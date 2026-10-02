"""
M9 — Seed Data Generator
Creates 3 synthetic demo applications covering PASS / REVIEW / HIGH_RISK_REVIEW.
All data is obviously fake and labeled as SYNTHETIC.
"""
import os
import json
import hashlib
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session

from app.database import SessionLocal, Base, engine
from app.models import (
    Application, Document, Extraction, ConsensusResult, RuleCheck,
    CrossDocumentCheck, RiskScore, AuditLog, TamperSignal,
    ApplicationStatus, DocumentType, MatchStatus, RuleSeverity
)
from app.services.explainer import append_audit_log
from app.config import settings


def gen_fake_pdf_content(title: str, fields: dict) -> bytes:
    """Generate a minimal text-based PDF that human can open."""
    lines = [f"  {k}: {v}" for k, v in fields.items()]
    body = "\n".join(lines)
    # Minimal valid PDF
    content = f"""%PDF-1.4
1 0 obj<</Type /Catalog /Pages 2 0 R>>endobj
2 0 obj<</Type /Pages /Kids[3 0 R] /Count 1>>endobj
3 0 obj<</Type /Page /Parent 2 0 R /MediaBox[0 0 612 792]
/Contents 4 0 R /Resources<</Font<</F1 5 0 R>>>>>>endobj
4 0 obj<</Length {len(body) + 200}>>
stream
BT /F1 12 Tf 50 750 Td
(SYNTHETIC DATA - NOT A REAL DOCUMENT) Tj 0 -20 Td
({title}) Tj 0 -30 Td
{chr(10).join(f'({line}) Tj 0 -15 Td' for line in lines)}
ET
endstream endobj
5 0 obj<</Type /Font /Subtype /Type1 /BaseFont /Helvetica>>endobj
xref
0 6
0000000000 65535 f
trailer<</Size 6 /Root 1 0 R>>
startxref 9
%%EOF"""
    return content.encode()


def create_scenario_1_pass(db: Session, storage_base: str) -> Application:
    """Scenario 1 — Clean PASS. All fields match, all rules pass."""
    app = Application(
        id="seed-app-001",
        applicant_name="Priya Kapoor (SYNTHETIC)",
        loan_type="home",
        loan_amount=1500000.0,
        status=ApplicationStatus.pass_,
        is_synthetic=True,
    )
    db.add(app)
    db.flush()

    salary_fields = {
        "applicant_name": "Priya Kapoor",
        "employer_name": "TechBridge Solutions Pvt Ltd",
        "gross_salary": 75000.0,
        "net_salary": 60000.0,
        "salary_month": "2026-08",
        "employee_id": "EMP-SYN-4821",
        "document_date": "2026-08-31",
        "pan_number": "ABCPS1234P",   # synthetic — passes PAN format
        "account_number": "SYNTH00012345",
        "deductions_total": 15000.0,
    }
    bank_fields = {
        "account_holder_name": "Priya Kapoor",
        "account_number": "SYNTH00012345",
        "bank_name": "State Bank of India",
        "ifsc_code": "SBIN0001234",
        "statement_period_start": "2026-07-01",
        "statement_period_end": "2026-09-30",
        "opening_balance": 45000.0,
        "closing_balance": 52000.0,
        "total_credits": 180000.0,
        "total_debits": 173000.0,
        "average_monthly_credit": 60000.0,
    }

    _create_doc_with_extractions(db, app.id, "salary_slip", salary_fields, salary_fields, storage_base, "priya_salary_slip.pdf")
    _create_doc_with_extractions(db, app.id, "bank_statement", bank_fields, bank_fields, storage_base, "priya_bank_statement.pdf")

    _create_risk_score(db, app.id, 94.0, "PASS",
        "All document checks passed. Documents are consistent across both AI pipelines and all deterministic rules.",
        93.0, 95.0, 100.0, 95.0)

    _seed_audit(db, app.id, "Priya Kapoor")
    db.commit()
    print("[OK] Seeded Scenario 1 (PASS): Priya Kapoor")
    return app


def create_scenario_2_review(db: Session, storage_base: str) -> Application:
    """Scenario 2 — REVIEW. Minor name mismatch + salary month off."""
    app = Application(
        id="seed-app-002",
        applicant_name="Arjun Mehta (SYNTHETIC)",
        loan_type="personal",
        loan_amount=800000.0,
        status=ApplicationStatus.review,
        is_synthetic=True,
    )
    db.add(app)
    db.flush()

    groq_fields = {
        "applicant_name": "Arjun Mehta",
        "employer_name": "Tech Solutions Pvt Ltd",   # note: different from Mistral
        "gross_salary": 55000.0,
        "net_salary": 44000.0,
        "salary_month": "2026-07",
        "pan_number": "BCDPA5678Q",
        "account_number": "SYNTH00056789",
        "deductions_total": 11000.0,
    }
    mistral_fields = {
        "applicant_name": "Arjun Mehta",
        "employer_name": "TECH SOLUTIONS PVT. LTD.",  # formatting diff → soft match
        "gross_salary": 55000.0,
        "net_salary": 44000.0,
        "salary_month": "2026-06",   # off by one month → mismatch
        "pan_number": "BCDPA5678Q",
        "account_number": "SYNTH00056789",
        "deductions_total": 11000.0,
    }
    bank_fields = {
        "account_holder_name": "Arjun Mehta",
        "account_number": "SYNTH00056789",
        "bank_name": "HDFC Bank",
        "ifsc_code": "HDFC0001234",
        "total_credits": 132000.0,
        "average_monthly_credit": 44000.0,
    }

    _create_doc_with_extractions(db, app.id, "salary_slip", groq_fields, mistral_fields, storage_base, "arjun_salary_slip.pdf")
    _create_doc_with_extractions(db, app.id, "bank_statement", bank_fields, bank_fields, storage_base, "arjun_bank_statement.pdf")

    _create_risk_score(db, app.id, 76.0, "REVIEW",
        "The employer name on the salary slip shows minor formatting inconsistency between AI pipelines "
        "('Tech Solutions Pvt Ltd' vs 'TECH SOLUTIONS PVT. LTD.'). Additionally, salary month differs "
        "by one month between extractions (2026-07 vs 2026-06). All rule checks passed; this appears "
        "to be an ambiguity requiring human confirmation rather than suspected fraud.",
        72.0, 80.0, 100.0, 82.0)

    _seed_audit(db, app.id, "Arjun Mehta")
    db.commit()
    print("[OK] Seeded Scenario 2 (REVIEW): Arjun Mehta")
    return app


def create_scenario_3_high_risk(db: Session, storage_base: str) -> Application:
    """Scenario 3 — HIGH_RISK_REVIEW. Cross-doc fraud + Aadhaar checksum fail + future date."""
    app = Application(
        id="seed-app-003",
        applicant_name="Rohit Verma (SYNTHETIC)",
        loan_type="business",
        loan_amount=5000000.0,
        status=ApplicationStatus.high_risk,
        is_synthetic=True,
    )
    db.add(app)
    db.flush()

    salary_fields = {
        "applicant_name": "Rohit Verma",
        "employer_name": "Apex Enterprises",
        "gross_salary": 120000.0,
        "net_salary": 95000.0,
        "salary_month": "2027-03",   # FUTURE DATE → triggers DATE_FUTURE rule fail
        "pan_number": "CDEQR9012R",
        "account_number": "SYNTH00099123",
        "deductions_total": 25000.0,
    }
    bank_fields = {
        "account_holder_name": "Rohit Verma",
        "account_number": "SYNTH00099123",
        "bank_name": "Axis Bank",
        "ifsc_code": "UTIB0001234",
        "total_credits": 624000.0,    # implied ₹52,000/month — 57% gap vs salary
        "average_monthly_credit": 52000.0,
    }
    itr_fields = {
        "applicant_name": "Rohit Verma",
        "pan_number": "CDEQR9012R",
        "assessment_year": "2026-27",
        "gross_total_income": 680000.0,   # ₹6.8L vs salary slip implied ₹14.4L — huge gap
        "taxable_income": 580000.0,
    }
    aadhaar_fields = {
        "aadhaar_number": "123456789013",   # Deliberately INVALID Verhoeff checksum
        "applicant_name": "Rohit Verma",
        "date_of_birth": "1985-05-15",
        "gender": "Male",
        "address": "123 Synthetic Road, Demo City - 110001",
    }

    doc_salary = _create_doc_with_extractions(db, app.id, "salary_slip", salary_fields, salary_fields, storage_base, "rohit_salary_slip.pdf")
    doc_bank = _create_doc_with_extractions(db, app.id, "bank_statement", bank_fields, bank_fields, storage_base, "rohit_bank_statement.pdf")
    doc_itr = _create_doc_with_extractions(db, app.id, "itr", itr_fields, itr_fields, storage_base, "rohit_itr.pdf")
    doc_aadhaar = _create_doc_with_extractions(db, app.id, "aadhaar", aadhaar_fields, aadhaar_fields, storage_base, "rohit_aadhaar.pdf")

    # Seed rule failures
    _add_rule_check(db, doc_salary.id, "DATE_FUTURE", False, "Document date 2027-03 is in the FUTURE (today: 2026-09-27)", RuleSeverity.high_risk)
    _add_rule_check(db, doc_aadhaar.id, "AADHAAR_CHECKSUM", False, "Checksum digit 3 does not match computed value 7 for 1234****9013", RuleSeverity.high_risk)
    _add_rule_check(db, doc_salary.id, "DUPLICATE_HASH", True, "No duplicate document found")
    _add_rule_check(db, doc_salary.id, "SALARY_ARITHMETIC", False, "120000 - 25000 = 95000 ≈ 95000 (OK actually — keep for demo completeness)", RuleSeverity.review)

    # Seed cross-doc discrepancies
    db.add(CrossDocumentCheck(
        application_id=app.id,
        check_type="income_reconciliation_salary_vs_bank",
        documents_involved=[doc_salary.id, doc_bank.id],
        result="DISCREPANCY",
        discrepancy_amount=43000.0,
        discrepancy_pct=45.3,
        detail="Income gap 45.3%: salary ₹95,000/mo vs bank avg ₹52,000/mo",
    ))
    db.add(CrossDocumentCheck(
        application_id=app.id,
        check_type="income_reconciliation_salary_vs_itr",
        documents_involved=[doc_salary.id, doc_itr.id],
        result="DISCREPANCY",
        discrepancy_amount=740000.0,
        discrepancy_pct=52.0,
        detail="Income gap 52%: salary implied ₹14,40,000/yr vs ITR ₹6,80,000/yr",
    ))

    # Tamper signal
    db.add(TamperSignal(
        document_id=doc_salary.id,
        signal_type="ai_detected",
        description="Unusual font inconsistency detected in salary figures",
        severity=RuleSeverity.review,
    ))

    _create_risk_score(db, app.id, 38.0, "HIGH_RISK_REVIEW",
        "This application has multiple critical fraud signals: (1) Salary slip is dated March 2027, "
        "which is in the future. (2) Aadhaar number fails Verhoeff checksum validation. "
        "(3) Declared salary (₹95,000/month) is 45% higher than average bank credits (₹52,000/month). "
        "(4) ITR gross income (₹6,80,000/year) is 52% below salary slip implied income (₹14,40,000/year). "
        "Requires immediate human review before any further processing.",
        35.0, 20.0, 20.0, 78.0)

    _seed_audit(db, app.id, "Rohit Verma")
    db.commit()
    print("[OK] Seeded Scenario 3 (HIGH_RISK): Rohit Verma")
    return app


# ─── Helpers ───────────────────────────────────────────────────────

def _create_doc_with_extractions(db, app_id, doc_type_str, groq_fields, mistral_fields, storage_base, filename):
    os.makedirs(os.path.join(storage_base, app_id), exist_ok=True)
    file_path = os.path.join(storage_base, app_id, filename)
    content = gen_fake_pdf_content(filename.replace("_", " ").title(), groq_fields)
    with open(file_path, "wb") as f:
        f.write(content)
    file_hash = hashlib.sha256(content).hexdigest()

    try:
        doc_type = DocumentType(doc_type_str)
    except ValueError:
        doc_type = DocumentType.unknown

    doc = Document(
        application_id=app_id,
        doc_type=doc_type,
        file_path=file_path,
        file_hash=file_hash,
        original_filename=filename,
    )
    db.add(doc)
    db.flush()

    db.add(Extraction(document_id=doc.id, engine="groq",
                      raw_json={}, structured_json=groq_fields, overall_confidence=0.92))
    db.add(Extraction(document_id=doc.id, engine="mistral",
                      raw_json={}, structured_json=mistral_fields, overall_confidence=0.88))

    # Generate consensus comparison rows
    from app.services.consensus_engine import _compare_field, FIELD_WEIGHTS
    all_fields = set(groq_fields.keys()) | set(mistral_fields.keys())
    for f in all_fields:
        g_val = groq_fields.get(f)
        m_val = mistral_fields.get(f)
        st, score = _compare_field(f, g_val, m_val, 2.0)
        w = FIELD_WEIGHTS.get(f, 1.0)
        db.add(ConsensusResult(
            application_id=app_id,
            document_id=doc.id,
            field_name=f,
            groq_value=str(g_val) if g_val is not None else None,
            mistral_value=str(m_val) if m_val is not None else None,
            match_status=st,
            weight=w,
            score_contribution=score * w,
        ))

    # Seed common rule checks
    if doc_type_str == "salary_slip":
        pan = groq_fields.get("pan_number")
        if pan:
            db.add(RuleCheck(document_id=doc.id, rule_name="PAN_FORMAT", passed=True,
                             detail=f"PAN '{pan}' format valid", severity=RuleSeverity.high_risk))
        date_val = groq_fields.get("salary_month") or groq_fields.get("document_date")
        is_future = date_val and date_val.startswith("2027")
        if not is_future:
            db.add(RuleCheck(document_id=doc.id, rule_name="DATE_FUTURE", passed=True,
                             detail="Document date valid (not in future)", severity=RuleSeverity.high_risk))
            db.add(RuleCheck(document_id=doc.id, rule_name="SALARY_ARITHMETIC", passed=True,
                             detail="Arithmetic OK: Gross - Deductions ≈ Net", severity=RuleSeverity.review))
            db.add(RuleCheck(document_id=doc.id, rule_name="DUPLICATE_HASH", passed=True,
                             detail="No duplicate document found", severity=RuleSeverity.high_risk))
    elif doc_type_str == "bank_statement":
        db.add(RuleCheck(document_id=doc.id, rule_name="IFSC_FORMAT", passed=True,
                         detail="IFSC format valid", severity=RuleSeverity.review))
        db.add(RuleCheck(document_id=doc.id, rule_name="DUPLICATE_HASH", passed=True,
                         detail="No duplicate document found", severity=RuleSeverity.high_risk))

    return doc


def _add_rule_check(db, doc_id, rule_name, passed, detail, severity=RuleSeverity.review):
    db.add(RuleCheck(document_id=doc_id, rule_name=rule_name, passed=passed, detail=detail, severity=severity))


def _create_risk_score(db, app_id, overall, status, explanation, agreement, consistency, tamper, confidence):
    db.add(RiskScore(
        application_id=app_id,
        agreement_score=agreement,
        consistency_score=consistency,
        tamper_score=tamper,
        rule_score=tamper,
        confidence_score=confidence,
        overall_score=overall,
        status=status,
        explanation_text=explanation,
        single_source=False,
    ))


def _seed_audit(db, app_id, name):
    from app.services.explainer import append_audit_log
    append_audit_log("system", "application_created", "application", app_id, {"applicant": name}, db)
    append_audit_log("system", "analysis_complete", "application", app_id, {"seeded": True}, db)


def run_seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    storage_base = settings.DOCUMENT_STORAGE_PATH
    os.makedirs(storage_base, exist_ok=True)

    # Clear existing seed data
    for app_id in ["seed-app-001", "seed-app-002", "seed-app-003"]:
        existing = db.query(Application).filter(Application.id == app_id).first()
        if existing:
            db.query(CrossDocumentCheck).filter(CrossDocumentCheck.application_id == app_id).delete()
            db.query(ConsensusResult).filter(ConsensusResult.application_id == app_id).delete()
            db.query(RiskScore).filter(RiskScore.application_id == app_id).delete()
            # Get doc IDs first
            docs = db.query(Document).filter(Document.application_id == app_id).all()
            for doc in docs:
                db.query(Extraction).filter(Extraction.document_id == doc.id).delete()
                db.query(RuleCheck).filter(RuleCheck.document_id == doc.id).delete()
                db.query(TamperSignal).filter(TamperSignal.document_id == doc.id).delete()
            db.query(Document).filter(Document.application_id == app_id).delete()
            db.delete(existing)
    db.commit()

    create_scenario_1_pass(db, storage_base)
    create_scenario_2_review(db, storage_base)
    create_scenario_3_high_risk(db, storage_base)
    db.close()
    print("\n[OK] Seed complete. 3 synthetic applications created.")
    print("   Login: demo@dualtrust.ai / demo1234")


if __name__ == "__main__":
    run_seed()
