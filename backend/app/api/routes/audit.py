"""Audit log routes."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.models import AuditLog
from app.schemas.api_schemas import AuditLogResponse, AuditChainVerifyResponse
from app.services.explainer import verify_audit_chain

router = APIRouter()


@router.get("", response_model=list[AuditLogResponse])
def get_audit_logs(
    application_id: Optional[str] = None,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    q = db.query(AuditLog)
    if application_id:
        q = q.filter(AuditLog.entity_id == application_id)
    return q.order_by(AuditLog.created_at.desc()).limit(limit).all()


@router.get("/verify", response_model=AuditChainVerifyResponse)
def verify_chain(db: Session = Depends(get_db)):
    """Verify the entire audit log hash chain. Breaks if any entry was tampered."""
    total = db.query(AuditLog).count()
    chain_valid, broken = verify_audit_chain(db)
    return AuditChainVerifyResponse(
        chain_valid=chain_valid,
        total_entries=total,
        broken_entries=broken,
    )
