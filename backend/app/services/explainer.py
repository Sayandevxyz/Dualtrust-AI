"""M7 — Explainability (natural language) + Hash-chained Audit Log"""
import hashlib
import json
import logging
from datetime import datetime
from sqlalchemy.orm import Session
from groq import Groq

from app.models import AuditLog, RiskScore, RuleCheck, CrossDocumentCheck, ConsensusResult
from app.config import settings

logger = logging.getLogger(__name__)

GENESIS_HASH = "DUALTRUST_GENESIS_HASH_0000000000000000000000000000000000000000000000"


# ──────────────────────────────────────────────────────────────────
# Explainability
# ──────────────────────────────────────────────────────────────────

def generate_explanation(
    application_id: str,
    risk_score: RiskScore,
    db: Session,
) -> str:
    """
    Generate a plain-English 'why flagged' explanation via Groq.
    Only called for REVIEW and HIGH_RISK_REVIEW cases.
    Falls back to templated text if Groq call fails.
    """
    if risk_score.status == "PASS":
        return "All document checks passed. Documents are consistent across both AI pipelines and all deterministic rules."

    # Gather evidence
    rule_failures = (
        db.query(RuleCheck)
        .join(RuleCheck.document)
        .filter(RuleCheck.passed == False)
        .all()
    )
    mismatches = (
        db.query(ConsensusResult)
        .filter(
            ConsensusResult.application_id == application_id,
            ConsensusResult.match_status.in_(["MISMATCH", "PARTIAL"]),
        )
        .all()
    )
    cross_issues = (
        db.query(CrossDocumentCheck)
        .filter(
            CrossDocumentCheck.application_id == application_id,
            CrossDocumentCheck.result == "DISCREPANCY",
        )
        .all()
    )

    evidence = {
        "overall_score": risk_score.overall_score,
        "status": risk_score.status,
        "rule_failures": [
            {"rule": r.rule_name, "detail": r.detail, "severity": str(r.severity)}
            for r in rule_failures
        ],
        "field_mismatches": [
            {"field": m.field_name, "groq": m.groq_value, "mistral": m.mistral_value}
            for m in mismatches[:5]
        ],
        "cross_doc_discrepancies": [
            {"check": c.check_type, "detail": c.detail, "gap_pct": c.discrepancy_pct}
            for c in cross_issues
        ],
    }

    if not settings.GROQ_API_KEY or settings.GROQ_API_KEY == "your_groq_api_key_here":
        return _template_explanation(risk_score, rule_failures, mismatches, cross_issues)

    try:
        client = Groq(api_key=settings.GROQ_API_KEY)
        response = client.chat.completions.create(
            model=settings.GROQ_MODEL,
            messages=[{
                "role": "system",
                "content": (
                    "You are an audit AI for a loan document verification system. "
                    "Generate a 2-3 sentence plain-English explanation of why this application "
                    "was flagged for human review. Be specific: mention field names, discrepancy "
                    "amounts, and rule failures. Do NOT recommend approve or reject. "
                    "Do NOT make assumptions beyond the evidence provided."
                ),
            }, {
                "role": "user",
                "content": f"Application evidence:\n{json.dumps(evidence, indent=2)}",
            }],
            max_tokens=200,
            temperature=0.3,
        )
        explanation = response.choices[0].message.content.strip()
        logger.info(f"Explanation generated for {application_id}")
        return explanation
    except Exception as e:
        logger.warning(f"Groq explanation failed, using template: {e}")
        return _template_explanation(risk_score, rule_failures, mismatches, cross_issues)


def _template_explanation(risk_score, rule_failures, mismatches, cross_issues) -> str:
    parts = [f"Application scored {risk_score.overall_score:.0f}/100 and was routed to {risk_score.status}."]
    if rule_failures:
        failed_names = ", ".join(r.rule_name for r in rule_failures[:3])
        parts.append(f"Deterministic rule failures: {failed_names}.")
    if mismatches:
        fields = ", ".join(m.field_name for m in mismatches[:3])
        parts.append(f"Field mismatches between AI pipelines: {fields}.")
    if cross_issues:
        parts.append(f"{len(cross_issues)} cross-document discrepancies detected.")
    return " ".join(parts)


# ──────────────────────────────────────────────────────────────────
# Hash-chained Audit Log
# ──────────────────────────────────────────────────────────────────

def append_audit_log(
    actor: str,
    action: str,
    entity_type: str,
    entity_id: str,
    metadata: dict,
    db: Session,
) -> AuditLog:
    """
    Append a new audit log entry with hash chaining.
    entry_hash = SHA-256(prev_hash + canonical_content)
    Editing any past entry breaks the chain — detectable via verify_audit_chain().
    """
    last = db.query(AuditLog).order_by(AuditLog.created_at.desc()).first()
    prev_hash = last.entry_hash if last else GENESIS_HASH

    content = json.dumps({
        "actor": actor,
        "action": action,
        "entity_type": entity_type,
        "entity_id": str(entity_id),
        "metadata": metadata,
        "created_at": datetime.utcnow().isoformat(),
    }, sort_keys=True)

    entry_hash = hashlib.sha256(f"{prev_hash}{content}".encode()).hexdigest()

    entry = AuditLog(
        actor=actor,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        metadata_json=metadata,
        prev_hash=prev_hash,
        entry_hash=entry_hash,
    )
    db.add(entry)
    db.commit()
    return entry


def verify_audit_chain(db: Session) -> tuple[bool, list[str]]:
    """
    Walk the entire audit log and verify hash chain integrity.
    Returns (chain_valid, list_of_broken_entry_ids).
    """
    entries = db.query(AuditLog).order_by(AuditLog.created_at.asc()).all()
    broken = []
    prev_hash = GENESIS_HASH

    for entry in entries:
        content = json.dumps({
            "actor": entry.actor,
            "action": entry.action,
            "entity_type": entry.entity_type,
            "entity_id": str(entry.entity_id),
            "metadata": entry.metadata_json,
            "created_at": entry.created_at.isoformat(),
        }, sort_keys=True)

        expected_hash = hashlib.sha256(f"{prev_hash}{content}".encode()).hexdigest()
        if expected_hash != entry.entry_hash:
            broken.append(f"Entry {entry.id} (action={entry.action}) — hash mismatch")
        prev_hash = entry.entry_hash

    chain_valid = len(broken) == 0
    if chain_valid:
        logger.info(f"Audit chain verified: {len(entries)} entries, all valid")
    else:
        logger.warning(f"Audit chain BROKEN: {len(broken)} invalid entries")
    return chain_valid, broken
