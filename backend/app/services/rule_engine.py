"""
M4 — Deterministic Rule Engine
Fraud checks that don't depend on ANY AI. The "third validator."
Even if both Groq and Mistral are fooled, these checks catch structural fraud.
"""
import re
import hashlib
import logging
from datetime import datetime, date, timedelta
from typing import Optional
from sqlalchemy.orm import Session

from app.models import RuleCheck, Document, RuleSeverity
from app.config import settings

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────
# Verhoeff Algorithm (Aadhaar checksum)
# ──────────────────────────────────────────────────────────────────
_VERHOEFF_D = [
    [0,1,2,3,4,5,6,7,8,9],[1,2,3,4,0,6,7,8,9,5],[2,3,4,0,1,7,8,9,5,6],
    [3,4,0,1,2,8,9,5,6,7],[4,0,1,2,3,9,5,6,7,8],[5,9,8,7,6,0,4,3,2,1],
    [6,5,9,8,7,1,0,4,3,2],[7,6,5,9,8,2,1,0,4,3],[8,7,6,5,9,3,2,1,0,4],
    [9,8,7,6,5,4,3,2,1,0],
]
_VERHOEFF_P = [
    [0,1,2,3,4,5,6,7,8,9],[1,5,7,6,2,8,3,0,9,4],[5,8,0,3,7,9,6,1,4,2],
    [8,9,1,6,0,4,3,5,2,7],[9,4,5,3,1,2,6,8,7,0],[4,2,8,6,5,7,3,9,0,1],
    [2,7,9,3,8,0,6,4,1,5],[7,0,4,6,9,1,3,2,5,8],
]
_VERHOEFF_INV = [0,4,3,2,1,9,8,7,6,5]

def _verhoeff_validate(number: str) -> bool:
    """Returns True if the Aadhaar number passes the Verhoeff checksum."""
    digits = [int(d) for d in reversed(number.replace(" ", ""))]
    c = 0
    for i, digit in enumerate(digits):
        c = _VERHOEFF_D[c][_VERHOEFF_P[i % 8][digit]]
    return c == 0


# ──────────────────────────────────────────────────────────────────
# GSTIN check digit (mod 36)
# ──────────────────────────────────────────────────────────────────
def _gstin_validate(gstin: str) -> bool:
    """Validates GSTIN check digit using mod-36 algorithm."""
    gstin = gstin.strip().upper()
    if len(gstin) != 15:
        return False
    chars = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    total = 0
    for i, ch in enumerate(gstin[:-1]):
        if ch not in chars:
            return False
        val = chars.index(ch)
        factor = 2 if i % 2 else 1
        val *= factor
        total += (val // 36) + (val % 36)
    check = (36 - (total % 36)) % 36
    expected = chars[check]
    return gstin[-1] == expected


# ──────────────────────────────────────────────────────────────────
# PAN format validation
# ──────────────────────────────────────────────────────────────────
_PAN_PATTERN = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$")
_PAN_VALID_CATEGORIES = set("PCHABFTLJG")  # 4th letter category codes

def _pan_validate(pan: str) -> tuple[bool, str]:
    pan = pan.strip().upper()
    if not _PAN_PATTERN.match(pan):
        return False, f"PAN '{pan}' does not match format AAAAA9999A"
    category = pan[3]
    if category not in _PAN_VALID_CATEGORIES:
        return False, f"PAN category code '{category}' is not a valid category (P,C,H,A,B,F,T,L,J,G)"
    return True, "OK"


# ──────────────────────────────────────────────────────────────────
# IFSC format
# ──────────────────────────────────────────────────────────────────
_IFSC_PATTERN = re.compile(r"^[A-Z]{4}0[A-Z0-9]{6}$")

def _ifsc_validate(ifsc: str) -> bool:
    return bool(_IFSC_PATTERN.match(ifsc.strip().upper()))


# ──────────────────────────────────────────────────────────────────
# Main rule engine entry point
# ──────────────────────────────────────────────────────────────────

def run_rule_engine(
    document_id: str,
    doc_type: str,
    extracted_fields: dict,
    file_hash: str,
    application_id: str,
    application_date: datetime,
    db: Session,
) -> list[RuleCheck]:
    """
    Run all deterministic checks for a document.
    Saves results to rule_checks table and returns list of RuleCheck objects.
    """
    w = settings.get_consensus_weights()
    checks: list[RuleCheck] = []

    def _save(rule_name, passed, detail, severity=RuleSeverity.review):
        rc = RuleCheck(
            document_id=document_id,
            rule_name=rule_name,
            passed=passed,
            detail=detail,
            severity=severity,
        )
        db.add(rc)
        checks.append(rc)
        level = "✅" if passed else ("🔴" if severity == RuleSeverity.high_risk else "🟡")
        logger.info(f"  Rule {rule_name}: {level} {detail}")

    logger.info(f"Running rule engine: doc_type={doc_type}, doc_id={document_id}")

    # ── PAN format ─────────────────────────────────────────────────
    if doc_type in ("pan_card", "salary_slip", "itr"):
        pan = extracted_fields.get("pan_number")
        if pan:
            ok, msg = _pan_validate(pan)
            _save("PAN_FORMAT", ok, msg if not ok else f"PAN '{pan}' format valid", RuleSeverity.high_risk)

    # ── Aadhaar Verhoeff checksum ──────────────────────────────────
    if doc_type == "aadhaar":
        aadhaar = extracted_fields.get("aadhaar_number", "")
        digits_only = re.sub(r"\s", "", str(aadhaar))
        if len(digits_only) == 12 and digits_only.isdigit():
            ok = _verhoeff_validate(digits_only)
            _save("AADHAAR_CHECKSUM", ok,
                  "Verhoeff checksum valid" if ok else f"Aadhaar checksum FAILED for {digits_only[:4]}****{digits_only[8:]}",
                  RuleSeverity.high_risk)
        elif aadhaar:
            _save("AADHAAR_CHECKSUM", False, f"Aadhaar number has wrong length ({len(digits_only)} digits, expected 12)", RuleSeverity.high_risk)

    # ── GSTIN check digit ──────────────────────────────────────────
    if doc_type == "gst":
        gstin = extracted_fields.get("gstin", "")
        if gstin:
            ok = _gstin_validate(gstin)
            _save("GSTIN_CHECKSUM", ok,
                  "GSTIN check digit valid" if ok else f"GSTIN '{gstin}' check digit INVALID",
                  RuleSeverity.high_risk)

    # ── IFSC format ────────────────────────────────────────────────
    if doc_type in ("bank_statement", "salary_slip"):
        ifsc = extracted_fields.get("ifsc_code")
        if ifsc:
            ok = _ifsc_validate(ifsc)
            _save("IFSC_FORMAT", ok,
                  "IFSC format valid" if ok else f"IFSC '{ifsc}' does not match format AAAA0XXXXXX",
                  RuleSeverity.review)

    # ── Salary arithmetic: gross - deductions ≈ net ────────────────
    if doc_type == "salary_slip":
        gross = extracted_fields.get("gross_salary")
        net = extracted_fields.get("net_salary")
        deductions = extracted_fields.get("deductions_total")
        if gross and net and deductions:
            expected_net = gross - deductions
            tolerance_pct = w.get("field_match_tolerance", {}).get("numeric_percent", 2.0)
            diff_pct = abs(expected_net - net) / gross * 100
            ok = diff_pct <= tolerance_pct
            _save("SALARY_ARITHMETIC", ok,
                  f"Arithmetic OK: {gross} - {deductions} ≈ {net}" if ok
                  else f"Arithmetic FAIL: {gross} - {deductions} = {expected_net:.2f} ≠ {net} (diff {diff_pct:.1f}%)",
                  RuleSeverity.review)

    # ── Date: no future documents ──────────────────────────────────
    doc_date_str = extracted_fields.get("document_date") or extracted_fields.get("salary_month")
    if doc_date_str:
        try:
            if len(doc_date_str) == 7:  # YYYY-MM
                doc_date = datetime.strptime(doc_date_str + "-01", "%Y-%m-%d").date()
            else:
                doc_date = datetime.strptime(doc_date_str[:10], "%Y-%m-%d").date()
            today = date.today()
            ok = doc_date <= today
            _save("DATE_FUTURE", ok,
                  "Document date is valid (not in future)" if ok
                  else f"Document date {doc_date} is in the FUTURE (today: {today})",
                  RuleSeverity.high_risk)

            # ── Salary slip age ─────────────────────────────────────
            if doc_type == "salary_slip":
                max_age = w.get("salary_slip_max_age_days", 90)
                age_days = (today - doc_date).days
                ok_age = age_days <= max_age
                _save("SALARY_AGE", ok_age,
                      f"Salary slip is {age_days} days old (limit: {max_age})" if not ok_age
                      else f"Salary slip age OK: {age_days} days",
                      RuleSeverity.review)
        except ValueError:
            pass  # unparseable date — skip

    # ── Duplicate hash detection ───────────────────────────────────
    from app.models import Document as DocModel, Application as AppModel
    existing = (
        db.query(DocModel)
        .join(AppModel)
        .filter(
            DocModel.file_hash == file_hash,
            AppModel.id != application_id,
        )
        .first()
    )
    if existing:
        _save("DUPLICATE_HASH", False,
              f"IDENTICAL document (SHA-256 match) found in application {existing.application_id}",
              RuleSeverity.high_risk)
    else:
        _save("DUPLICATE_HASH", True, "No duplicate document found across applications")

    # ── Velocity: PAN appears in too many applications ─────────────
    pan_any = extracted_fields.get("pan_number")
    if pan_any:
        _check_pan_velocity(pan_any, application_id, w, db, _save)

    # ── Velocity: bank account ─────────────────────────────────────
    acct = extracted_fields.get("account_number")
    if acct:
        _check_account_velocity(acct, application_id, w, db, _save)

    db.commit()
    return checks


def _check_pan_velocity(pan, application_id, w, db, _save):
    """Flag if same PAN appears in too many applications in the window."""
    from app.models import Extraction as ExtractionModel, Document as DocModel
    max_apps = w.get("velocity_pan_max_applications", 2)
    window_days = w.get("velocity_pan_window_days", 30)
    cutoff = datetime.utcnow() - timedelta(days=window_days)

    bind = db.get_bind()
    is_postgres = bind and bind.dialect.name == "postgresql"
    if is_postgres:
        count_query = (
            db.query(ExtractionModel)
            .join(DocModel)
            .filter(
                ExtractionModel.structured_json.op("->>")("pan_number") == pan,
                ExtractionModel.created_at >= cutoff,
                DocModel.application_id != application_id,
            )
            .count()
        )
    else:
        extractions = (
            db.query(ExtractionModel)
            .join(DocModel)
            .filter(
                ExtractionModel.created_at >= cutoff,
                DocModel.application_id != application_id,
            )
            .all()
        )
        count_query = sum(
            1 for e in extractions
            if isinstance(e.structured_json, dict) and e.structured_json.get("pan_number") == pan
        )

    ok = count_query <= max_apps
    _save("VELOCITY_PAN", ok,
          f"PAN velocity OK: {count_query} prior apps in {window_days} days" if ok
          else f"PAN '{pan[:5]}****' seen in {count_query} applications in {window_days} days (limit: {max_apps})",
          RuleSeverity.high_risk)


def _check_account_velocity(acct, application_id, w, db, _save):
    from app.models import Extraction as ExtractionModel, Document as DocModel
    max_apps = w.get("velocity_account_max_applications", 2)
    window_days = w.get("velocity_account_window_days", 30)
    cutoff = datetime.utcnow() - timedelta(days=window_days)

    bind = db.get_bind()
    is_postgres = bind and bind.dialect.name == "postgresql"
    if is_postgres:
        count_query = (
            db.query(ExtractionModel)
            .join(DocModel)
            .filter(
                ExtractionModel.structured_json.op("->>")("account_number") == acct,
                ExtractionModel.created_at >= cutoff,
                DocModel.application_id != application_id,
            )
            .count()
        )
    else:
        extractions = (
            db.query(ExtractionModel)
            .join(DocModel)
            .filter(
                ExtractionModel.created_at >= cutoff,
                DocModel.application_id != application_id,
            )
            .all()
        )
        count_query = sum(
            1 for e in extractions
            if isinstance(e.structured_json, dict) and e.structured_json.get("account_number") == acct
        )

    ok = count_query <= max_apps
    _save("VELOCITY_ACCOUNT", ok,
          f"Account velocity OK" if ok
          else f"Account '****{acct[-4:]}' seen in {count_query} applications in {window_days} days (limit: {max_apps})",
          RuleSeverity.high_risk)
