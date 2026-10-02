"""
Async analysis pipeline — orchestrates M1→M2→M3→M4→M5→M6→M7 in sequence.
Can run as RQ background task or synchronously (ASYNC_ANALYSIS=false).
"""
import hashlib
import logging
import os
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Document, Extraction, Application, ApplicationStatus, TamperSignal, RuleSeverity
from app.services.groq_analyzer import analyze_with_groq
from app.services.mistral_analyzer import analyze_with_mistral
from app.services.rule_engine import run_rule_engine
from app.services.cross_doc_verifier import run_cross_document_verification
from app.services.consensus_engine import compute_risk_score
from app.services.explainer import generate_explanation, append_audit_log

logger = logging.getLogger(__name__)


async def run_full_analysis(document_id: str, application_id: str):
    """
    Full analysis pipeline for one document.
    Gracefully degrades if one AI provider fails.
    """
    db: Session = SessionLocal()
    try:
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            logger.error(f"Document {document_id} not found")
            return

        app = db.query(Application).filter(Application.id == application_id).first()
        app.status = ApplicationStatus.analyzing
        db.commit()

        append_audit_log("system", "analysis_started", "document", document_id,
                         {"doc_type": str(doc.doc_type)}, db)

        doc_type = doc.doc_type.value if hasattr(doc.doc_type, "value") else str(doc.doc_type)
        file_path = doc.file_path

        # ── M2: Groq ────────────────────────────────────────────────
        logger.info(f"[{document_id}] Running Groq analysis...")
        groq_result = await analyze_with_groq(file_path, doc_type)
        groq_ext = Extraction(
            document_id=document_id,
            engine="groq",
            raw_json=groq_result.raw_response,
            structured_json=groq_result.extracted_fields,
            overall_confidence=groq_result.overall_confidence,
            extraction_failed=groq_result.extraction_failed,
        )
        db.add(groq_ext)

        # ── M3: Mistral ─────────────────────────────────────────────
        logger.info(f"[{document_id}] Running Mistral analysis...")
        mistral_result, raw_ocr = await analyze_with_mistral(file_path, doc_type)
        mistral_ext = Extraction(
            document_id=document_id,
            engine="mistral",
            raw_json=raw_ocr,
            structured_json=mistral_result.extracted_fields,
            overall_confidence=mistral_result.overall_confidence,
            extraction_failed=mistral_result.extraction_failed,
        )
        db.add(mistral_ext)
        db.commit()

        # Store tamper signals
        all_signals = set(groq_result.tampering_signals or []) | set(mistral_result.tampering_signals or [])
        for sig in all_signals:
            if sig and sig != "extraction_failed":
                ts = TamperSignal(
                    document_id=document_id,
                    signal_type="ai_detected",
                    description=sig,
                    severity=RuleSeverity.review,
                )
                db.add(ts)
        db.commit()

        # ── M4: Rule Engine ─────────────────────────────────────────
        logger.info(f"[{document_id}] Running rule engine...")
        best_fields = groq_result.extracted_fields or mistral_result.extracted_fields or {}
        rule_checks = run_rule_engine(
            document_id=document_id,
            doc_type=doc_type,
            extracted_fields=best_fields,
            file_hash=doc.file_hash,
            application_id=application_id,
            application_date=app.created_at,
            db=db,
        )

        # ── M6: Cross-document verification ─────────────────────────
        logger.info(f"[{application_id}] Running cross-document verification...")
        cross_results = run_cross_document_verification(application_id, db)

        # ── M5: Consensus → Risk Score ──────────────────────────────
        logger.info(f"[{application_id}] Computing consensus score...")
        risk = compute_risk_score(
            document_id=document_id,
            application_id=application_id,
            groq_result=groq_result,
            mistral_result=mistral_result,
            rule_checks=rule_checks,
            cross_doc_results=cross_results,
            loan_amount=app.loan_amount,
            db=db,
        )

        # ── M7: Explainability ──────────────────────────────────────
        if risk.status in ("REVIEW", "HIGH_RISK_REVIEW"):
            logger.info(f"[{application_id}] Generating explanation...")
            explanation = generate_explanation(application_id, risk, db)
            risk.explanation_text = explanation
            db.commit()

        append_audit_log("system", "analysis_complete", "application", application_id,
                         {"status": risk.status, "score": risk.overall_score}, db)

        logger.info(f"✅ Analysis complete: {application_id} → {risk.status} ({risk.overall_score:.1f})")

    except Exception as e:
        logger.error(f"Analysis pipeline failed for {document_id}: {e}", exc_info=True)
        if app:
            app.status = ApplicationStatus.pending
            db.commit()
    finally:
        db.close()


def run_full_analysis_sync(document_id: str, application_id: str):
    """Synchronous wrapper for RQ task queue."""
    import asyncio
    asyncio.run(run_full_analysis(document_id, application_id))
