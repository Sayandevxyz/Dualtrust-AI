"""Analysis trigger routes + B2B /verify endpoint."""
import base64
import tempfile
import os
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Document, Application, RiskScore
from app.schemas.api_schemas import VerifyRequest, VerifyResponse
from app.config import settings

router = APIRouter()


@router.post("/documents/{doc_id}/analyze")
async def trigger_analysis(
    doc_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(404, "Document not found")

    from app.tasks.analysis_task import run_full_analysis, run_full_analysis_sync
    from app.services.explainer import append_audit_log

    append_audit_log("api", "analysis_triggered", "document", doc_id,
                     {"application_id": doc.application_id}, db)

    if settings.ASYNC_ANALYSIS:
        try:
            import redis
            from rq import Queue
            r = redis.from_url(settings.REDIS_URL)
            q = Queue(connection=r)
            q.enqueue(run_full_analysis_sync, doc_id, doc.application_id)
            return {"status": "queued", "document_id": doc_id, "application_id": doc.application_id}
        except Exception:
            pass  # Fall through to sync

    # Synchronous (dev mode or RQ unavailable)
    background_tasks.add_task(run_full_analysis_sync, doc_id, doc.application_id)
    return {"status": "processing", "document_id": doc_id, "application_id": doc.application_id}


@router.post("/verify", response_model=VerifyResponse)
async def verify_document(payload: VerifyRequest, db: Session = Depends(get_db)):
    """B2B API — single-call document verification endpoint."""
    # Decode and temporarily save
    file_bytes = base64.b64decode(payload.document_base64)
    suffix = ".pdf" if file_bytes[:4] == b"%PDF" else ".png"

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name

    try:
        from app.services.classifier import classify_document
        from app.services.groq_analyzer import analyze_with_groq
        from app.services.rule_engine import (
            _pan_validate, _verhoeff_validate, _ifsc_validate
        )
        import uuid
        verification_id = str(uuid.uuid4())

        doc_type, _ = await classify_document(tmp_path, f"upload{suffix}", payload.document_type)
        groq_result = await analyze_with_groq(tmp_path, doc_type)

        fields = groq_result.extracted_fields or {}
        rule_failures = []

        # Run key rule checks
        pan = fields.get("pan_number")
        if pan:
            ok, msg = _pan_validate(pan)
            if not ok:
                rule_failures.append(f"PAN_FORMAT: {msg}")

        aadhaar = fields.get("aadhaar_number", "")
        import re
        digits = re.sub(r"\s", "", str(aadhaar))
        if len(digits) == 12 and digits.isdigit():
            if not _verhoeff_validate(digits):
                rule_failures.append("AADHAAR_CHECKSUM: Invalid checksum digit")

        score = groq_result.overall_confidence * 100
        if rule_failures:
            score = min(score, 40.0)
            status = "HIGH_RISK_REVIEW"
        elif score >= 80:
            status = "PASS"
        elif score >= 60:
            status = "REVIEW"
        else:
            status = "HIGH_RISK_REVIEW"

        return VerifyResponse(
            verification_id=verification_id,
            status=status,
            overall_score=round(score, 1),
            explanation=f"Document type: {doc_type}. Confidence: {score:.0f}%. Rule failures: {len(rule_failures)}.",
            rule_failures=rule_failures,
            single_source=True,
        )
    finally:
        os.unlink(tmp_path)
