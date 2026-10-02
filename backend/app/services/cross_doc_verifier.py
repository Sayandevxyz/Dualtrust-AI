"""
M6 — Cross-Document Verification
Reconcile income and identity fields across all uploaded documents for one application.
"""
import logging
from sqlalchemy.orm import Session

from app.models import CrossDocumentCheck, Document, Extraction, DocumentType
from app.config import settings

logger = logging.getLogger(__name__)


def _get_best_extraction(doc_id: str, db: Session) -> dict:
    """Get the best (highest confidence) structured extraction for a document."""
    extractions = (
        db.query(Extraction)
        .filter(Extraction.document_id == doc_id, Extraction.extraction_failed == False)
        .order_by(Extraction.overall_confidence.desc())
        .all()
    )
    if not extractions:
        return {}
    # Average of both engines if both available
    merged = {}
    for ext in extractions:
        fields = ext.structured_json or {}
        for k, v in fields.items():
            if v is not None and k not in merged:
                merged[k] = v
    return merged


def _save_check(db, application_id, check_type, doc_ids, result, discrepancy_amount, discrepancy_pct, detail):
    check = CrossDocumentCheck(
        application_id=application_id,
        check_type=check_type,
        documents_involved=doc_ids,
        result=result,
        discrepancy_amount=discrepancy_amount,
        discrepancy_pct=discrepancy_pct,
        detail=detail,
    )
    db.add(check)
    icon = "✅" if result == "OK" else "🔴"
    logger.info(f"  Cross-doc {check_type}: {icon} {detail}")
    return check


def run_cross_document_verification(application_id: str, db: Session) -> list[CrossDocumentCheck]:
    """
    Run all cross-document checks for an application.
    Collects all documents and their best extractions, then reconciles.
    """
    w = settings.get_consensus_weights()
    income_tol = w.get("cross_doc_income_tolerance_pct", 25.0)
    itr_tol = w.get("cross_doc_itr_tolerance_pct", 20.0)
    bank_itr_tol = w.get("cross_doc_bank_itr_tolerance_pct", 30.0)

    docs = db.query(Document).filter(Document.application_id == application_id).all()
    if len(docs) < 2:
        return []  # Need at least 2 documents for cross-checks

    # Build type → (doc_id, fields) map
    doc_map: dict[str, tuple[str, dict]] = {}
    for doc in docs:
        fields = _get_best_extraction(doc.id, db)
        if fields:
            doc_map[doc.doc_type.value if hasattr(doc.doc_type, "value") else str(doc.doc_type)] = (doc.id, fields)

    checks = []

    # ── Name reconciliation ─────────────────────────────────────────
    name_fields = {
        "salary_slip": "applicant_name",
        "bank_statement": "account_holder_name",
        "pan_card": "applicant_name",
        "aadhaar": "applicant_name",
        "itr": "applicant_name",
    }
    names = {}
    for dt, field in name_fields.items():
        if dt in doc_map:
            val = doc_map[dt][1].get(field)
            if val:
                names[dt] = (doc_map[dt][0], val)

    if len(names) >= 2:
        doc_types = list(names.keys())
        for i in range(len(doc_types)):
            for j in range(i + 1, len(doc_types)):
                dt_a, dt_b = doc_types[i], doc_types[j]
                id_a, name_a = names[dt_a]
                id_b, name_b = names[dt_b]
                import re
                norm = lambda s: re.sub(r"[^a-z]", "", s.lower())
                ok = norm(name_a) == norm(name_b)
                checks.append(_save_check(
                    db, application_id,
                    f"name_match_{dt_a}_vs_{dt_b}",
                    [id_a, id_b],
                    "OK" if ok else "DISCREPANCY",
                    None, None,
                    f"Name match OK: '{name_a}'" if ok
                    else f"Name mismatch: '{name_a}' ({dt_a}) vs '{name_b}' ({dt_b})",
                ))

    # ── PAN reconciliation ──────────────────────────────────────────
    pan_sources = {}
    for dt in ("salary_slip", "pan_card", "itr"):
        if dt in doc_map:
            pan = doc_map[dt][1].get("pan_number")
            if pan:
                pan_sources[dt] = (doc_map[dt][0], pan)

    if len(pan_sources) >= 2:
        pans = list(pan_sources.values())
        for i in range(len(pans)):
            for j in range(i + 1, len(pans)):
                id_a, pan_a = pans[i]
                id_b, pan_b = pans[j]
                ok = pan_a.strip().upper() == pan_b.strip().upper()
                checks.append(_save_check(
                    db, application_id, "pan_cross_match", [id_a, id_b],
                    "OK" if ok else "DISCREPANCY", None, None,
                    "PAN consistent across documents" if ok
                    else f"PAN MISMATCH: {pan_a} vs {pan_b}",
                ))

    # ── Account number: salary_slip vs bank_statement ──────────────
    if "salary_slip" in doc_map and "bank_statement" in doc_map:
        ss_id, ss_fields = doc_map["salary_slip"]
        bs_id, bs_fields = doc_map["bank_statement"]
        ss_acct = ss_fields.get("account_number")
        bs_acct = bs_fields.get("account_number")
        if ss_acct and bs_acct:
            ok = ss_acct.strip() == bs_acct.strip()
            checks.append(_save_check(
                db, application_id, "account_number_match", [ss_id, bs_id],
                "OK" if ok else "DISCREPANCY", None, None,
                "Account number consistent" if ok
                else f"Account mismatch: slip={ss_acct} vs bank={bs_acct}",
            ))

    # ── Income: salary_slip vs bank_statement ──────────────────────
    if "salary_slip" in doc_map and "bank_statement" in doc_map:
        ss_id, ss_fields = doc_map["salary_slip"]
        bs_id, bs_fields = doc_map["bank_statement"]
        net_salary = ss_fields.get("net_salary")
        avg_credit = bs_fields.get("average_monthly_credit")
        if net_salary and avg_credit:
            try:
                net_salary = float(net_salary)
                avg_credit = float(avg_credit)
                diff_pct = abs(net_salary - avg_credit) / max(net_salary, 1) * 100
                ok = diff_pct <= income_tol
                checks.append(_save_check(
                    db, application_id, "income_reconciliation_salary_vs_bank",
                    [ss_id, bs_id],
                    "OK" if ok else "DISCREPANCY",
                    abs(net_salary - avg_credit), diff_pct,
                    f"Salary/bank income aligned: ₹{net_salary:,.0f} vs ₹{avg_credit:,.0f} ({diff_pct:.1f}%)" if ok
                    else f"Income gap {diff_pct:.1f}%: salary ₹{net_salary:,.0f}/mo vs bank avg ₹{avg_credit:,.0f}/mo",
                ))
            except (ValueError, TypeError):
                pass

    # ── Income: salary_slip vs ITR ─────────────────────────────────
    if "salary_slip" in doc_map and "itr" in doc_map:
        ss_id, ss_fields = doc_map["salary_slip"]
        itr_id, itr_fields = doc_map["itr"]
        gross_monthly = ss_fields.get("gross_salary")
        itr_annual = itr_fields.get("gross_total_income")
        if gross_monthly and itr_annual:
            try:
                gross_annual = float(gross_monthly) * 12
                itr_annual = float(itr_annual)
                diff_pct = abs(gross_annual - itr_annual) / max(gross_annual, 1) * 100
                ok = diff_pct <= itr_tol
                checks.append(_save_check(
                    db, application_id, "income_reconciliation_salary_vs_itr",
                    [ss_id, itr_id],
                    "OK" if ok else "DISCREPANCY",
                    abs(gross_annual - itr_annual), diff_pct,
                    f"Salary/ITR income aligned: ₹{gross_annual:,.0f} vs ₹{itr_annual:,.0f} ({diff_pct:.1f}%)" if ok
                    else f"Income gap {diff_pct:.1f}%: salary implied ₹{gross_annual:,.0f}/yr vs ITR ₹{itr_annual:,.0f}/yr",
                ))
            except (ValueError, TypeError):
                pass

    # ── Bank vs ITR ────────────────────────────────────────────────
    if "bank_statement" in doc_map and "itr" in doc_map:
        bs_id, bs_fields = doc_map["bank_statement"]
        itr_id, itr_fields = doc_map["itr"]
        total_credits = bs_fields.get("total_credits")
        itr_income = itr_fields.get("gross_total_income")
        if total_credits and itr_income:
            try:
                tc = float(total_credits)
                ii = float(itr_income)
                diff_pct = abs(tc - ii) / max(tc, 1) * 100
                ok = diff_pct <= bank_itr_tol
                checks.append(_save_check(
                    db, application_id, "bank_vs_itr_income",
                    [bs_id, itr_id],
                    "OK" if ok else "DISCREPANCY",
                    abs(tc - ii), diff_pct,
                    f"Bank credits/ITR aligned: ₹{tc:,.0f} vs ₹{ii:,.0f} ({diff_pct:.1f}%)" if ok
                    else f"Bank credits ₹{tc:,.0f} vs ITR income ₹{ii:,.0f} — gap {diff_pct:.1f}%",
                ))
            except (ValueError, TypeError):
                pass

    db.commit()
    return checks
