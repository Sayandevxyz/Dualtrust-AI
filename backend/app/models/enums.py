from enum import Enum


class ApplicationStatus(str, Enum):
    pending = "PENDING"
    analyzing = "ANALYZING"
    pass_ = "PASS"
    review = "REVIEW"
    high_risk = "HIGH_RISK_REVIEW"
    decided = "DECIDED"


class DocumentType(str, Enum):
    salary_slip = "salary_slip"
    bank_statement = "bank_statement"
    pan_card = "pan_card"
    aadhaar = "aadhaar"
    itr = "itr"
    gst = "gst"
    address_proof = "address_proof"
    unknown = "unknown"


class MatchStatus(str, Enum):
    match = "MATCH"
    soft_match = "SOFT_MATCH"
    mismatch = "MISMATCH"
    partial = "PARTIAL"
    skipped = "SKIPPED"


class RuleSeverity(str, Enum):
    high_risk = "HIGH_RISK"
    review = "REVIEW"
    info = "INFO"
