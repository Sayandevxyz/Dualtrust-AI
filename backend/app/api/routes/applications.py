"""Application routes."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.models import Application, Document, RiskScore, ConsensusResult, RuleCheck, CrossDocumentCheck, TamperSignal, AuditLog
from app.schemas.api_schemas import (
    ApplicationCreate, ApplicationResponse, DashboardResponse,
    RiskScoreResponse, ConsensusResponse, FieldComparisonItem,
    RuleCheckResponse, CrossDocResponse, DocumentResponse
)
from app.services.explainer import append_audit_log

router = APIRouter()


@router.post("", response_model=ApplicationResponse, status_code=201)
def create_application(payload: ApplicationCreate, db: Session = Depends(get_db)):
    app = Application(
        applicant_name=payload.applicant_name,
        loan_type=payload.loan_type,
        loan_amount=payload.loan_amount,
    )
    db.add(app)
    db.commit()
    db.refresh(app)
    append_audit_log("api", "application_created", "application", app.id,
                     {"applicant": app.applicant_name, "loan_amount": app.loan_amount}, db)
    return app


@router.get("", response_model=list[ApplicationResponse])
def list_applications(
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    q = db.query(Application)
    if status:
        q = q.filter(Application.status == status)
    return q.order_by(Application.created_at.desc()).all()


@router.get("/{app_id}", response_model=ApplicationResponse)
def get_application(app_id: str, db: Session = Depends(get_db)):
    app = db.query(Application).filter(Application.id == app_id).first()
    if not app:
        raise HTTPException(404, "Application not found")
    return app


@router.get("/{app_id}/risk-score", response_model=RiskScoreResponse)
def get_risk_score(app_id: str, db: Session = Depends(get_db)):
    rs = (db.query(RiskScore)
          .filter(RiskScore.application_id == app_id)
          .order_by(RiskScore.created_at.desc())
          .first())
    if not rs:
        raise HTTPException(404, "Risk score not yet computed")
    return rs


@router.get("/{app_id}/consensus", response_model=ConsensusResponse)
def get_consensus(app_id: str, db: Session = Depends(get_db)):
    rows = (db.query(ConsensusResult)
            .filter(ConsensusResult.application_id == app_id)
            .all())
    fields = [
        FieldComparisonItem(
            field_name=r.field_name,
            groq_value=r.groq_value,
            mistral_value=r.mistral_value,
            match_status=r.match_status.value if hasattr(r.match_status, "value") else str(r.match_status),
            weight=r.weight,
            score_contribution=r.score_contribution,
        )
        for r in rows
    ]
    total_w = sum(f.weight for f in fields) or 1
    agreement = sum(f.score_contribution for f in fields) / total_w * 100
    return ConsensusResponse(application_id=app_id, fields=fields, agreement_score=agreement)


@router.get("/{app_id}/dashboard", response_model=DashboardResponse)
def get_dashboard(app_id: str, db: Session = Depends(get_db)):
    app = db.query(Application).filter(Application.id == app_id).first()
    if not app:
        raise HTTPException(404, "Application not found")

    docs = db.query(Document).filter(Document.application_id == app_id).all()
    doc_ids = [d.id for d in docs]

    risk = (db.query(RiskScore)
            .filter(RiskScore.application_id == app_id)
            .order_by(RiskScore.created_at.desc()).first())

    consensus = (db.query(ConsensusResult)
                 .filter(ConsensusResult.application_id == app_id).all())

    rules = (db.query(RuleCheck)
             .filter(RuleCheck.document_id.in_(doc_ids)).all()) if doc_ids else []

    cross = (db.query(CrossDocumentCheck)
             .filter(CrossDocumentCheck.application_id == app_id).all())

    tamper = (db.query(TamperSignal)
              .filter(TamperSignal.document_id.in_(doc_ids)).all()) if doc_ids else []

    audit_count = (db.query(AuditLog)
                   .filter(AuditLog.entity_id == app_id).count())

    return DashboardResponse(
        application=app,
        documents=[DocumentResponse.model_validate(d) for d in docs],
        risk_score=RiskScoreResponse.model_validate(risk) if risk else None,
        field_comparisons=[
            FieldComparisonItem(
                field_name=r.field_name,
                groq_value=r.groq_value,
                mistral_value=r.mistral_value,
                match_status=r.match_status.value if hasattr(r.match_status, "value") else str(r.match_status),
                weight=r.weight,
                score_contribution=r.score_contribution,
            ) for r in consensus
        ],
        rule_checks=[RuleCheckResponse.model_validate(r) for r in rules],
        cross_doc_checks=[CrossDocResponse.model_validate(c) for c in cross],
        tamper_signals=[{"document_id": t.document_id, "type": t.signal_type, "detail": t.description, "severity": str(t.severity)} for t in tamper],
        audit_log_count=audit_count,
    )
