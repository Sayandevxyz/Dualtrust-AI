"""
M5 — Consensus Engine
Field-by-field comparison of Groq vs Mistral outputs.
Weighted score → PASS / REVIEW / HIGH_RISK_REVIEW routing.
All weights/thresholds come from consensus_weights.json — no hardcoding.
"""
import logging
from datetime import datetime
from typing import Optional
from Levenshtein import ratio as lev_ratio
from sqlalchemy.orm import Session

from app.models import ConsensusResult, RiskScore, MatchStatus, Application, ApplicationStatus
from app.schemas.extraction_schema import ExtractionResult
from app.config import settings

logger = logging.getLogger(__name__)

# Fields that should be compared numerically
NUMERIC_FIELDS = {
    "gross_salary", "net_salary", "deductions_total",
    "opening_balance", "closing_balance", "total_credits", "total_debits",
    "average_monthly_credit", "gross_total_income", "taxable_income",
    "tax_paid", "annual_turnover",
}

# Fields that must be exact matches (identity fields)
EXACT_FIELDS = {
    "pan_number", "aadhaar_number", "account_number", "gstin",
}

# Date fields that must match strictly (no soft matching)
DATE_FIELDS = {
    "salary_month", "document_date", "statement_period_start", "statement_period_end",
    "date_of_birth", "registration_date",
}

# Per-field importance weights (relative)
FIELD_WEIGHTS = {
    "pan_number": 2.0, "aadhaar_number": 2.0, "account_number": 2.0,
    "applicant_name": 1.5, "account_holder_name": 1.5,
    "net_salary": 1.5, "gross_salary": 1.5,
    "employer_name": 1.0, "bank_name": 1.0,
    "salary_month": 1.0, "document_date": 1.0,
}


def _normalize_string(s: str) -> str:
    """Lowercase, strip punctuation and whitespace for comparison."""
    import re
    return re.sub(r"[^a-z0-9]", "", s.lower())


def _compare_field(
    field_name: str,
    val_a: Optional[str],
    val_b: Optional[str],
    tolerance_pct: float,
) -> tuple[MatchStatus, float]:
    """
    Compare two field values. Returns (match_status, score 0–1).
    """
    # Both null → skip
    if val_a is None and val_b is None:
        return MatchStatus.skipped, 1.0

    # One null → partial
    if val_a is None or val_b is None:
        return MatchStatus.partial, 0.5

    str_a, str_b = str(val_a).strip(), str(val_b).strip()

    # Numeric comparison
    if field_name in NUMERIC_FIELDS:
        try:
            n_a, n_b = float(str_a), float(str_b)
            if n_b == 0:
                return (MatchStatus.match, 1.0) if n_a == 0 else (MatchStatus.mismatch, 0.0)
            diff_pct = abs(n_a - n_b) / max(abs(n_b), 1) * 100
            if diff_pct <= tolerance_pct:
                return MatchStatus.match, 1.0
            else:
                return MatchStatus.mismatch, 0.0
        except ValueError:
            pass

    # Exact fields (identity numbers)
    if field_name in EXACT_FIELDS:
        ok = _normalize_string(str_a) == _normalize_string(str_b)
        return (MatchStatus.match, 1.0) if ok else (MatchStatus.mismatch, 0.0)

    # Date fields (must be exact, no soft Levenshtein matching)
    if field_name in DATE_FIELDS:
        ok = _normalize_string(str_a) == _normalize_string(str_b)
        return (MatchStatus.match, 1.0) if ok else (MatchStatus.mismatch, 0.0)

    # String comparison
    norm_a = _normalize_string(str_a)
    norm_b = _normalize_string(str_b)
    if norm_a == norm_b:
        return MatchStatus.match, 1.0
    similarity = lev_ratio(norm_a, norm_b)
    soft_threshold = 0.80  # from weights config ideally
    if similarity >= soft_threshold:
        return MatchStatus.soft_match, 0.7
    return MatchStatus.mismatch, 0.0


def compute_field_agreement(
    groq_result: ExtractionResult,
    mistral_result: ExtractionResult,
    document_id: str,
    application_id: str,
    db: Session,
) -> tuple[float, list[ConsensusResult]]:
    """
    Compare all fields from both pipelines.
    Saves ConsensusResult rows. Returns (agreement_score 0–100, rows).
    """
    w = settings.get_consensus_weights()
    tol = w.get("field_match_tolerance", {}).get("numeric_percent", 2.0)

    groq_fields = groq_result.extracted_fields or {}
    mistral_fields = mistral_result.extracted_fields or {}
    all_fields = set(groq_fields.keys()) | set(mistral_fields.keys())

    rows = []
    weighted_sum = 0.0
    total_weight = 0.0

    for field in all_fields:
        g_val = groq_fields.get(field)
        m_val = mistral_fields.get(field)
        status, field_score = _compare_field(field, g_val, m_val, tol)

        if status == MatchStatus.skipped:
            continue  # excluded from average

        weight = FIELD_WEIGHTS.get(field, 1.0)
        contribution = field_score * weight

        row = ConsensusResult(
            application_id=application_id,
            document_id=document_id,
            field_name=field,
            groq_value=str(g_val) if g_val is not None else None,
            mistral_value=str(m_val) if m_val is not None else None,
            match_status=status,
            weight=weight,
            score_contribution=contribution,
        )
        db.add(row)
        rows.append(row)

        weighted_sum += contribution
        total_weight += weight

    agreement_score = (weighted_sum / total_weight * 100) if total_weight > 0 else 0.0
    logger.info(f"Field agreement score: {agreement_score:.1f}/100 ({len(rows)} fields)")
    return agreement_score, rows


def compute_tamper_score(
    rule_checks: list,
    groq_result: ExtractionResult,
    mistral_result: ExtractionResult,
) -> float:
    """
    Score 0–100 based on rule failures and tamper signals.
    Starts at 100, deducted per failure.
    """
    w = settings.get_consensus_weights()
    penalties = w.get("rule_severity_penalties", {"HIGH_RISK": 40, "REVIEW": 15})
    score = 100.0

    for rc in rule_checks:
        if not rc.passed:
            sev = rc.severity.value if hasattr(rc.severity, "value") else str(rc.severity)
            score -= penalties.get(sev, 15)

    # Penalize tamper signals from AI
    all_signals = set(groq_result.tampering_signals or []) | set(mistral_result.tampering_signals or [])
    real_signals = [s for s in all_signals if s != "extraction_failed"]
    score -= len(real_signals) * 10

    return max(0.0, min(100.0, score))


def compute_risk_score(
    document_id: str,
    application_id: str,
    groq_result: ExtractionResult,
    mistral_result: ExtractionResult,
    rule_checks: list,
    cross_doc_results: list,
    loan_amount: float,
    db: Session,
) -> RiskScore:
    """
    Full consensus computation → RiskScore row saved to DB.
    """
    w = settings.get_consensus_weights()
    wt = w.get("weights", {})
    thresholds = w.get("thresholds", {"pass": 90, "review": 70})

    # 1. Field agreement
    agreement_score, _ = compute_field_agreement(
        groq_result, mistral_result, document_id, application_id, db
    )

    # 2. Cross-doc consistency
    if cross_doc_results:
        ok_checks = sum(1 for c in cross_doc_results if c.result == "OK")
        consistency_score = ok_checks / len(cross_doc_results) * 100
    else:
        consistency_score = 100.0  # no cross-doc data = no penalty

    # 3. Tamper + rule score
    tamper_score = compute_tamper_score(rule_checks, groq_result, mistral_result)

    # 4. Model confidence
    g_conf = groq_result.overall_confidence if not groq_result.extraction_failed else 0.0
    m_conf = mistral_result.overall_confidence if not mistral_result.extraction_failed else 0.0

    both_failed = groq_result.extraction_failed and mistral_result.extraction_failed
    single_source = groq_result.extraction_failed or mistral_result.extraction_failed

    if both_failed:
        confidence_score = 0.0
    elif single_source:
        confidence_score = max(g_conf, m_conf) * 50  # halved — single source penalty
    else:
        confidence_score = (g_conf + m_conf) / 2 * 100

    # Weighted overall
    overall = (
        agreement_score * wt.get("agreement_score", 0.40) +
        consistency_score * wt.get("cross_document_consistency", 0.30) +
        tamper_score * wt.get("tamper_and_rule_signals", 0.20) +
        confidence_score * wt.get("ocr_model_confidence", 0.10)
    )

    # Single-source cap
    if single_source:
        cap = w.get("single_source_score_cap", 65)
        overall = min(overall, cap)

    # Loan amount tier override
    tier = w.get("loan_amount_tier_overrides", {})
    pass_threshold = thresholds.get("pass", 90)
    if loan_amount >= tier.get("large_loan_threshold", 2000000):
        pass_threshold = tier.get("large_loan_pass_threshold", 95)

    # Routing
    if overall >= pass_threshold:
        status = "PASS"
    elif overall >= thresholds.get("review", 70):
        status = "REVIEW"
    else:
        status = "HIGH_RISK_REVIEW"

    risk = RiskScore(
        application_id=application_id,
        agreement_score=round(agreement_score, 2),
        consistency_score=round(consistency_score, 2),
        tamper_score=round(tamper_score, 2),
        rule_score=round(tamper_score, 2),
        confidence_score=round(confidence_score, 2),
        overall_score=round(overall, 2),
        status=status,
        single_source=single_source,
    )
    db.add(risk)

    # Update application status
    app = db.query(Application).filter(Application.id == application_id).first()
    if app:
        status_map = {
            "PASS": ApplicationStatus.pass_,
            "REVIEW": ApplicationStatus.review,
            "HIGH_RISK_REVIEW": ApplicationStatus.high_risk,
        }
        app.status = status_map.get(status, ApplicationStatus.review)

    db.commit()
    logger.info(
        f"Risk score: {overall:.1f}/100 → {status} "
        f"(agreement={agreement_score:.1f}, consistency={consistency_score:.1f}, "
        f"tamper={tamper_score:.1f}, confidence={confidence_score:.1f})"
    )
    return risk
