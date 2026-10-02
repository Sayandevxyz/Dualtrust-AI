"""API request/response Pydantic schemas."""
from __future__ import annotations
from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, Field


# ─── Applications ───────────────────────

class ApplicationCreate(BaseModel):
    applicant_name: str
    loan_type: str
    loan_amount: float

class ApplicationResponse(BaseModel):
    id: str
    applicant_name: str
    loan_type: str
    loan_amount: float
    status: str
    is_synthetic: bool
    created_at: datetime
    class Config:
        from_attributes = True


# ─── Documents ──────────────────────────

class DocumentResponse(BaseModel):
    id: str
    application_id: str
    doc_type: str
    file_hash: str
    original_filename: Optional[str]
    uploaded_at: datetime
    class Config:
        from_attributes = True


# ─── Consensus ──────────────────────────

class FieldComparisonItem(BaseModel):
    field_name: str
    groq_value: Optional[str]
    mistral_value: Optional[str]
    match_status: str
    weight: float
    score_contribution: float

class ConsensusResponse(BaseModel):
    application_id: str
    fields: list[FieldComparisonItem]
    agreement_score: float


# ─── Risk Score ─────────────────────────

class RiskScoreResponse(BaseModel):
    application_id: str
    agreement_score: float
    consistency_score: float
    tamper_score: float
    rule_score: float
    confidence_score: float
    overall_score: float
    status: str
    explanation_text: Optional[str]
    single_source: bool
    created_at: datetime
    class Config:
        from_attributes = True


# ─── Rule Check ─────────────────────────

class RuleCheckResponse(BaseModel):
    id: str
    document_id: str
    rule_name: str
    passed: bool
    detail: Optional[str]
    severity: str
    class Config:
        from_attributes = True


# ─── Cross-doc ──────────────────────────

class CrossDocResponse(BaseModel):
    id: str
    check_type: str
    documents_involved: list[str]
    result: str
    discrepancy_amount: Optional[float]
    discrepancy_pct: Optional[float]
    detail: Optional[str]
    class Config:
        from_attributes = True


# ─── Dashboard (all-in-one) ─────────────

class DashboardResponse(BaseModel):
    application: ApplicationResponse
    documents: list[DocumentResponse]
    risk_score: Optional[RiskScoreResponse]
    field_comparisons: list[FieldComparisonItem]
    rule_checks: list[RuleCheckResponse]
    cross_doc_checks: list[CrossDocResponse]
    tamper_signals: list[dict]
    audit_log_count: int


# ─── Review ─────────────────────────────

class ReviewCreate(BaseModel):
    decision: str
    notes: Optional[str] = None

class ReviewResponse(BaseModel):
    id: str
    application_id: str
    reviewer_id: Optional[str]
    decision: str
    notes: Optional[str]
    created_at: datetime
    class Config:
        from_attributes = True


# ─── Audit Log ──────────────────────────

class AuditLogResponse(BaseModel):
    id: str
    actor: str
    action: str
    entity_type: Optional[str]
    entity_id: Optional[str]
    metadata_json: Optional[dict]
    prev_hash: str
    entry_hash: str
    created_at: datetime
    class Config:
        from_attributes = True

class AuditChainVerifyResponse(BaseModel):
    chain_valid: bool
    total_entries: int
    broken_entries: list[str]


# ─── Auth ───────────────────────────────

class LoginRequest(BaseModel):
    email: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_name: str
    role: str


# ─── B2B API ────────────────────────────

class VerifyRequest(BaseModel):
    document_base64: str
    document_type: Optional[str] = None
    applicant_name: Optional[str] = None

class VerifyResponse(BaseModel):
    verification_id: str
    status: str
    overall_score: float
    explanation: str
    rule_failures: list[str]
    single_source: bool
