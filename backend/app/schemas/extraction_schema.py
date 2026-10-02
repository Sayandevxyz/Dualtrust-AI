"""
Pydantic v2 schemas — shared extraction contract enforced on BOTH AI pipelines.
Both Groq and Mistral must return data conforming to ExtractionResult.
"""
from __future__ import annotations
from datetime import date, datetime
from typing import Any, Literal, Optional
from pydantic import BaseModel, Field, model_validator


# ─────────────────────────────────────────
# Per-document field schemas
# ─────────────────────────────────────────

class SalarySlipFields(BaseModel):
    applicant_name: str
    employer_name: str
    gross_salary: float
    net_salary: float
    salary_month: str = Field(description="YYYY-MM format")
    employee_id: Optional[str] = None
    document_date: Optional[str] = None   # YYYY-MM-DD
    pan_number: Optional[str] = None
    account_number: Optional[str] = None
    deductions_total: Optional[float] = None
    bank_name: Optional[str] = None


class BankStatementFields(BaseModel):
    account_holder_name: str
    account_number: str
    bank_name: str
    ifsc_code: Optional[str] = None
    statement_period_start: Optional[str] = None
    statement_period_end: Optional[str] = None
    opening_balance: Optional[float] = None
    closing_balance: Optional[float] = None
    total_credits: Optional[float] = None
    total_debits: Optional[float] = None
    average_monthly_credit: Optional[float] = None


class PANFields(BaseModel):
    pan_number: str
    applicant_name: str
    father_name: Optional[str] = None
    date_of_birth: Optional[str] = None
    pan_category: Optional[str] = None   # P=Individual, C=Company, etc.


class AadhaarFields(BaseModel):
    aadhaar_number: str
    applicant_name: str
    date_of_birth: Optional[str] = None
    gender: Optional[str] = None
    address: Optional[str] = None


class ITRFields(BaseModel):
    applicant_name: str
    pan_number: Optional[str] = None
    assessment_year: Optional[str] = None
    gross_total_income: Optional[float] = None
    taxable_income: Optional[float] = None
    tax_paid: Optional[float] = None
    itr_type: Optional[str] = None


class GSTFields(BaseModel):
    gstin: str
    business_name: str
    address: Optional[str] = None
    registration_date: Optional[str] = None
    annual_turnover: Optional[float] = None


class AddressProofFields(BaseModel):
    applicant_name: str
    address: str
    document_issuer: Optional[str] = None
    document_date: Optional[str] = None


FIELD_SCHEMA_MAP = {
    "salary_slip": SalarySlipFields,
    "bank_statement": BankStatementFields,
    "pan_card": PANFields,
    "aadhaar": AadhaarFields,
    "itr": ITRFields,
    "gst": GSTFields,
    "address_proof": AddressProofFields,
}


# ─────────────────────────────────────────
# Shared extraction contract
# ─────────────────────────────────────────

class ExtractionResult(BaseModel):
    """
    THE shared JSON contract — both Groq and Mistral pipelines must return this.
    Direct field-by-field comparison is only possible if both outputs conform.
    """
    document_type: str
    extracted_fields: dict[str, Any]
    signature_present: bool = False
    tampering_signals: list[str] = Field(default_factory=list)
    field_confidence: dict[str, float] = Field(default_factory=dict)
    overall_confidence: float = Field(ge=0.0, le=1.0)
    engine: Literal["groq", "mistral"]
    extraction_timestamp: datetime = Field(default_factory=datetime.utcnow)
    raw_response: str = ""
    extraction_failed: bool = False
    failure_reason: Optional[str] = None


# ─────────────────────────────────────────
# JSON schema string for LLM prompting
# ─────────────────────────────────────────

EXTRACTION_SCHEMA_PROMPT = """
Return ONLY valid JSON matching this schema exactly. No markdown, no explanation.

{
  "document_type": "<one of: salary_slip | bank_statement | pan_card | aadhaar | itr | gst | address_proof>",
  "extracted_fields": { ... all fields specific to the document type ... },
  "signature_present": true | false,
  "tampering_signals": ["list of strings describing any suspicious features, empty if none"],
  "field_confidence": { "field_name": 0.0-1.0, ... },
  "overall_confidence": 0.0-1.0,
  "engine": "groq"
}

For salary_slip, extracted_fields must include:
  applicant_name, employer_name, gross_salary (number), net_salary (number),
  salary_month (YYYY-MM), employee_id, document_date (YYYY-MM-DD),
  pan_number, account_number, deductions_total (number)

For bank_statement, extracted_fields must include:
  account_holder_name, account_number, bank_name, ifsc_code,
  statement_period_start (YYYY-MM-DD), statement_period_end (YYYY-MM-DD),
  opening_balance, closing_balance, total_credits, total_debits, average_monthly_credit

For pan_card, extracted_fields must include:
  pan_number, applicant_name, father_name, date_of_birth, pan_category

For aadhaar, extracted_fields must include:
  aadhaar_number, applicant_name, date_of_birth, gender, address

For itr, extracted_fields must include:
  applicant_name, pan_number, assessment_year, gross_total_income,
  taxable_income, tax_paid, itr_type

For gst, extracted_fields must include:
  gstin, business_name, address, registration_date, annual_turnover

Use null for any field that cannot be read from the document.
"""
