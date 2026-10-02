# DualTrust AI — Detailed Implementation Plan

> **Project:** DualTrust AI — Dual-pipeline AI loan document verification system  
> **Build Target:** Hackathon MVP (demoable, not production-hardened)  
> **Est. Total Effort:** ~8–12 focused dev-hours with Antigravity

---

## Pre-Build Checklist (Do Before Running Antigravity)

| Item | Status | Notes |
|------|--------|-------|
| Gemini API Key | ⬜ | From [aistudio.google.com](https://aistudio.google.com) |
| Mistral API Key (OCR access) | ⬜ | From [console.mistral.ai](https://console.mistral.ai) |
| Docker Desktop installed | ⬜ | For Postgres + Redis containers |
| GitHub repo (empty) | ⬜ | Optional — for version control |
| Branding decision | ⬜ | Color palette, logo preference |
| Auth decision | ⬜ | Demo login OK vs. real auth? |
| Audience confirmed | ⬜ | SIH judges / investors / bank pilot |

---

## Repository Structure (Target)

```
dualtrust-ai/
├── docker-compose.yml
├── .env.example
├── README.md
├── DEMO_SCRIPT.md
├── consensus_weights.json          ← tunable, no code change needed
│
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── alembic/                    ← DB migrations
│   ├── app/
│   │   ├── main.py                 ← FastAPI entry point
│   │   ├── config.py               ← env var loading, fail-fast
│   │   ├── models/                 ← SQLAlchemy ORM models
│   │   │   ├── application.py
│   │   │   ├── document.py
│   │   │   ├── extraction.py
│   │   │   ├── consensus.py
│   │   │   ├── rule_check.py
│   │   │   ├── cross_doc.py
│   │   │   ├── risk_score.py
│   │   │   ├── review.py
│   │   │   ├── audit_log.py
│   │   │   └── user.py
│   │   ├── schemas/                ← Pydantic v2 schemas
│   │   │   ├── extraction_schema.py    ← THE shared JSON contract
│   │   │   ├── document_schemas.py     ← per-doc-type field sets
│   │   │   └── api_schemas.py
│   │   ├── services/
│   │   │   ├── classifier.py       ← M1
│   │   │   ├── gemini_analyzer.py  ← M2
│   │   │   ├── mistral_analyzer.py ← M3
│   │   │   ├── rule_engine.py      ← M4
│   │   │   ├── consensus_engine.py ← M5
│   │   │   ├── cross_doc_verifier.py ← M6
│   │   │   ├── explainer.py        ← M7
│   │   │   └── audit_logger.py     ← M7 hash-chain
│   │   ├── api/
│   │   │   └── routes/
│   │   │       ├── applications.py
│   │   │       ├── documents.py
│   │   │       ├── analysis.py
│   │   │       ├── reviews.py
│   │   │       └── audit.py
│   │   ├── tasks/                  ← RQ/Celery async workers
│   │   │   └── analysis_task.py
│   │   └── utils/
│   │       ├── crypto.py           ← hashing, audit chain
│   │       └── synthetic_data.py   ← M9 seed generator
│   └── tests/
│       ├── test_rule_engine.py
│       ├── test_consensus.py
│       └── test_cross_doc.py
│
└── frontend/
    ├── Dockerfile
    ├── vite.config.ts
    ├── package.json
    ├── src/
    │   ├── main.tsx
    │   ├── App.tsx
    │   ├── components/
    │   │   ├── ApplicationList.tsx
    │   │   ├── StatusBadge.tsx
    │   │   ├── FieldComparisonTable.tsx
    │   │   ├── RiskScoreCard.tsx
    │   │   ├── RuleEnginePanel.tsx
    │   │   ├── ExplainabilityCard.tsx
    │   │   ├── ReviewDecisionPanel.tsx
    │   │   ├── AuditLogViewer.tsx
    │   │   └── DocumentUploader.tsx
    │   ├── pages/
    │   │   ├── Dashboard.tsx
    │   │   ├── ApplicationDetail.tsx
    │   │   └── Pricing.tsx         ← mockup only
    │   └── api/
    │       └── client.ts
    └── tests/
        └── smoke.spec.ts           ← Playwright
```

---

## Milestone-by-Milestone Plan

---

### M0 — Scaffolding *(~1 hour)*

**Goal:** One-command `docker-compose up` starts everything.

**Deliverables:**
- `docker-compose.yml` with 4 services: `postgres`, `redis`, `backend`, `frontend`
- `.env.example` with all variables (see table below)
- Makefile shortcuts: `make dev`, `make migrate`, `make seed`, `make test`
- Empty `README.md` skeleton with headings

**Environment Variables (`.env.example`):**

```dotenv
# === AI Providers ===
GEMINI_API_KEY=your_key_here
MISTRAL_API_KEY=your_key_here

# === Database ===
POSTGRES_USER=dualtrust
POSTGRES_PASSWORD=dualtrust_dev
POSTGRES_DB=dualtrust
DATABASE_URL=postgresql://dualtrust:dualtrust_dev@postgres:5432/dualtrust

# === Redis ===
REDIS_URL=redis://redis:6379/0

# === Storage ===
DOCUMENT_STORAGE_PATH=/app/storage/documents
STORAGE_ENCRYPTION_KEY=generate_with_openssl_rand

# === Feature Flags ===
EXTERNAL_VERIFICATION_ENABLED=false    # PAN/Aadhaar/GST API stubs
ASYNC_ANALYSIS=true                     # use RQ workers vs. sync

# === App Config ===
JWT_SECRET=change_this_in_production
DEMO_MODE=true                          # shows SYNTHETIC banners in UI
LOG_LEVEL=INFO
```

**Acceptance test:** `docker-compose up` → `GET /health` returns 200 from backend.

---

### M1 — Document Classifier *(~1.5 hours)*

**Goal:** Upload a file → system knows what type of document it is.

**Implementation:**

```python
# Classifier priority order:
# 1. Filename keyword match (fast, free)
# 2. First-page text regex (PDF text layer)
# 3. Lightweight Gemini call (fallback for scanned docs)

CLASSIFIER_RULES = {
    "pan_card":       [r"permanent account number", r"income tax dept"],
    "aadhaar":        [r"unique identification", r"aadhaar", r"uidai"],
    "salary_slip":    [r"salary slip", r"payslip", r"net pay", r"gross salary"],
    "bank_statement": [r"bank statement", r"account statement", r"closing balance"],
    "itr":            [r"income tax return", r"itr-", r"assessment year"],
    "gst":            [r"goods and services tax", r"gstin", r"gstr"],
    "address_proof":  [r"electricity bill", r"utility bill", r"registered address"],
}
```

**API:**
```
POST /api/applications/{id}/documents
  Body: multipart/form-data { file, hint_type? }
  Response: { document_id, detected_type, confidence, file_hash }
```

**Stored on upload:**
- SHA-256 file hash (duplicate detection)
- pHash (perceptual hash for near-duplicate scanned images)
- File path on encrypted local volume

**Acceptance test:** Upload a salary slip PDF → `detected_type == "salary_slip"`.

---

### M2 — AI-A: Gemini Analyzer *(~2 hours)*

**Goal:** Send any classified document to Gemini, get back structured JSON that matches the shared contract.

**Model selection:** At build time, check `ai.google.dev` for current recommended model. Expected: `gemini-2.0-flash` or `gemini-1.5-pro` with multimodal + structured output (JSON schema mode).

**Shared extraction contract (Pydantic v2 schema — enforced on BOTH pipelines):**

```python
class ExtractionResult(BaseModel):
    document_type: DocumentType
    extracted_fields: dict[str, Any]   # typed per-doc subclass
    signature_present: bool
    tampering_signals: list[str]
    field_confidence: dict[str, float]  # 0.0–1.0 per field
    overall_confidence: float
    engine: Literal["gemini", "mistral"]
    extraction_timestamp: datetime
    raw_response: str                   # stored for audit

# Per-document field schemas (examples):

class SalarySlipFields(BaseModel):
    applicant_name: str
    employer_name: str
    gross_salary: float
    net_salary: float
    salary_month: str          # YYYY-MM
    employee_id: str | None
    document_date: date
    pan_number: str | None
    account_number: str | None
    deductions_total: float | None

class BankStatementFields(BaseModel):
    account_holder_name: str
    account_number: str
    bank_name: str
    ifsc_code: str | None
    statement_period_start: date
    statement_period_end: date
    opening_balance: float
    closing_balance: float
    total_credits: float
    total_debits: float
    average_monthly_credit: float | None

# ... PANFields, AadhaarFields, ITRFields, GSTFields defined similarly
```

**Gemini call pattern:**
```python
async def analyze_with_gemini(doc_path: str, doc_type: str) -> ExtractionResult:
    # 1. Load document (PDF→images or image direct)
    # 2. Build system prompt with JSON schema constraint
    # 3. Call Gemini with response_mime_type="application/json"
    # 4. Validate response against Pydantic schema
    # 5. Retry up to 3 times with exponential backoff
    # 6. On total failure: return ExtractionResult with engine="gemini",
    #    overall_confidence=0.0, tampering_signals=["extraction_failed"]
    #    AND flag application as "single_source_needs_review"
```

**Acceptance test:** PDF salary slip → parsed JSON with all salary fields populated, `engine == "gemini"`.

---

### M3 — AI-B: Mistral OCR Pipeline *(~2 hours)*

**Goal:** Mistral OCR extracts text + bounding boxes → structuring pass maps to shared JSON contract.

**Model selection:** At build time, check `docs.mistral.ai` for current OCR endpoint. Expected: Mistral OCR API with `mistral-ocr-latest` or equivalent.

**Two-stage approach:**

```
Stage 1: Mistral OCR
  Input: Document image/PDF
  Output: {
    pages: [{
      markdown: "...",
      images: [...],
      dimensions: { width, height }
    }]
  }
  (preserves word-level confidence + bounding boxes)

Stage 2: Structuring LLM pass (Mistral Le Chat or Mistral-7B)
  Input: OCR markdown + target JSON schema
  Output: ExtractionResult (same Pydantic schema as Gemini)
```

**Why two stages?** Keeps OCR bounding boxes available for the tamper-signal layer (unusual character spacing, inconsistent font metrics).

**Bounding box storage:** Raw OCR JSON stored in `extractions.raw_json` — not parsed further in MVP but available for future visual tamper analysis.

**Acceptance test:** Same salary slip → Mistral pipeline returns `ExtractionResult` with same fields, `engine == "mistral"`.

---

### M4 — Deterministic Rule Engine *(~2 hours)*

**Goal:** Fraud checks that don't depend on any AI. *The strongest technical differentiator.*

**Rules table:**

| Rule ID | Check | Fail Action |
|---------|-------|-------------|
| `PAN_FORMAT` | 5 letters + 4 digits + 1 letter; letter[3] ∈ {P,C,H,F,A,T,B,L,J,G} | `HIGH_RISK` |
| `AADHAAR_CHECKSUM` | Verhoeff algorithm on 12 digits | `HIGH_RISK` |
| `GSTIN_CHECKSUM` | GSTIN mod-36 check digit | `HIGH_RISK` |
| `IFSC_FORMAT` | 11 chars, first 4 alpha (bank code) + 0 + 6 alphanumeric | `REVIEW` |
| `SALARY_ARITHMETIC` | `gross - sum(deductions) ≈ net` within ±2% | `REVIEW` |
| `ITR_MONTHLY_MATCH` | `ITR_annual / 12` within ±25% of avg bank monthly credit | `REVIEW` |
| `DATE_FUTURE` | No document date > today | `HIGH_RISK` |
| `SALARY_AGE` | Salary slip date within 90 days of application | `REVIEW` |
| `DUPLICATE_HASH` | SHA-256 of file seen in another application | `HIGH_RISK` |
| `NEAR_DUPLICATE` | pHash distance < 10 from doc in another application | `REVIEW` |
| `VELOCITY_PAN` | Same PAN in >2 applications in 30 days | `HIGH_RISK` |
| `VELOCITY_ACCOUNT` | Same bank account in >2 applications in 30 days | `HIGH_RISK` |

**Implementation note:** Verhoeff checksum for Aadhaar is a well-known algorithm — implement it from scratch (no external library needed, ~20 lines of Python).

**Config:** Thresholds (90-day window, ±25% tolerance) in `consensus_weights.json`, not hardcoded.

**Output per check → `rule_checks` table:**
```json
{
  "document_id": "uuid",
  "rule_name": "AADHAAR_CHECKSUM",
  "passed": false,
  "detail": "Checksum digit 7 does not match computed value 3",
  "severity": "HIGH_RISK",
  "created_at": "ISO8601"
}
```

**Acceptance tests (M9):**
- Valid synthetic PAN → passes `PAN_FORMAT`
- Crafted invalid PAN → fails `PAN_FORMAT`
- Gross=50000, deductions=8000, net=45000 → fails `SALARY_ARITHMETIC`
- Future-dated salary slip → fails `DATE_FUTURE`

---

### M5 — Consensus Engine *(~1.5 hours)*

**Goal:** Field-by-field comparison of Gemini vs. Mistral output → weighted score → routing verdict.

**Config file (`consensus_weights.json`):**
```json
{
  "weights": {
    "agreement_score": 0.40,
    "cross_document_consistency": 0.30,
    "tamper_and_rule_signals": 0.20,
    "ocr_model_confidence": 0.10
  },
  "thresholds": {
    "pass": 90,
    "review": 70
  },
  "field_match_tolerance": {
    "numeric_percent": 2.0,
    "date_days": 0
  },
  "loan_amount_tier_overrides": {
    "large_loan_threshold": 2000000,
    "large_loan_pass_threshold": 95
  }
}
```

**Scoring logic:**

```python
def compute_consensus_score(
    gemini: ExtractionResult,
    mistral: ExtractionResult,
    rule_results: list[RuleCheck],
    cross_doc_results: list[CrossDocCheck],
    weights: ConsensusWeights,
) -> RiskScore:

    # 1. Field agreement (per-field match/mismatch/missing)
    agreement_score = compute_field_agreement(gemini, mistral)
    
    # 2. Cross-doc consistency (M6 output fed in)
    consistency_score = compute_cross_doc_consistency(cross_doc_results)
    
    # 3. Tamper + rule signals
    #    - Each HIGH_RISK rule fail → heavy penalty
    #    - Each REVIEW rule fail → moderate penalty
    #    - tamper_signals from either AI → deduction
    tamper_score = compute_tamper_score(rule_results, gemini, mistral)
    
    # 4. Model confidence (average of both engines' overall_confidence)
    confidence_score = (gemini.overall_confidence + mistral.overall_confidence) / 2 * 100
    
    # Weighted sum
    overall = (
        agreement_score * weights.agreement_score +
        consistency_score * weights.cross_document_consistency +
        tamper_score * weights.tamper_and_rule_signals +
        confidence_score * weights.ocr_model_confidence
    )
    
    # Routing
    if overall >= weights.thresholds.pass:
        status = "PASS"
    elif overall >= weights.thresholds.review:
        status = "REVIEW"
    else:
        status = "HIGH_RISK_REVIEW"
    
    return RiskScore(overall_score=overall, status=status, ...)
```

**Field match rules:**
- String fields: exact match after normalization (lowercase, strip punctuation) = MATCH; within 80% Levenshtein = SOFT_MATCH (scores as 0.7); else MISMATCH
- Numeric fields: within ±`numeric_percent`% = MATCH; else MISMATCH  
- Date fields: within ±`date_days` days = MATCH
- Null from one engine but value from other = PARTIAL (scores as 0.5)
- Null from both = SKIPPED (excluded from agreement calculation)

**Acceptance test:** Identical inputs → score 100. Completely mismatched fields → score < 50.

---

### M6 — Cross-Document Verification *(~1.5 hours)*

**Goal:** Reconcile identity and income fields across all uploaded documents for one application.

**Checks to implement:**

```
Identity Reconciliation:
  - applicant_name: salary_slip ↔ bank_statement ↔ PAN ↔ Aadhaar (all should match)
  - pan_number: salary_slip ↔ ITR ↔ PAN card (exact match required)
  - account_number: salary_slip ↔ bank_statement (exact match)

Income Reconciliation:
  - salary_slip.net_salary × 12  vs  bank_statement.total_credits (annual)
    → flag if discrepancy > 25% 
  - salary_slip.gross_salary × 12 vs ITR.gross_total_income
    → flag if discrepancy > 20%
  - bank_statement.average_monthly_credit vs ITR_annual / 12
    → flag if discrepancy > 30%

Date Coherence:
  - salary_slip.salary_month must be within bank_statement period
  - ITR.assessment_year must be consistent with salary slip dates

Employer Verification:
  - salary_slip.employer_name  vs  bank_statement credit description (if parseable)
```

**Discrepancy amount stored:** Absolute and percentage difference recorded in `cross_document_checks.discrepancy_amount` — powers the "evidence" view in the dashboard.

**Output → `cross_document_checks` table:**
```json
{
  "application_id": "uuid",
  "check_type": "income_reconciliation_salary_vs_itr",
  "documents_involved": ["doc_id_1", "doc_id_2"],
  "result": "DISCREPANCY",
  "discrepancy_amount": 180000,
  "discrepancy_pct": 36.0,
  "detail": "Salary slip annual income ₹6,00,000 vs ITR gross income ₹4,20,000 (36% gap)"
}
```

---

### M7 — Explainability + Audit Trail *(~1 hour)*

**Goal:** Human-readable "why flagged" + tamper-proof audit log.

**Explainability (for REVIEW/HIGH-RISK cases):**

```python
# One Gemini call with a structured template prompt:
EXPLAIN_PROMPT = """
You are an audit AI. Summarize in 2–3 plain-English sentences why this 
loan document application was flagged for human review. 
Be specific: mention field names, discrepancy amounts, and rule failures.
Do NOT recommend approve/reject — only describe the evidence.

Evidence:
- Consensus score: {score}/100 (threshold: {threshold})
- Field mismatches: {mismatches}
- Rule engine failures: {rule_failures}
- Cross-document discrepancies: {cross_doc_issues}
- Tamper signals: {tamper_signals}
"""
```

**Hash-chained audit log:**

```python
def append_audit_log(
    actor: str,
    action: str,
    entity_type: str,
    entity_id: str,
    metadata: dict,
    db: Session,
) -> AuditLog:
    # Get the hash of the last entry (or genesis hash if first)
    last_entry = db.query(AuditLog).order_by(AuditLog.created_at.desc()).first()
    prev_hash = last_entry.entry_hash if last_entry else "GENESIS_HASH_0000"
    
    # Canonical content string (deterministic serialization)
    content = json.dumps({
        "actor": actor,
        "action": action,
        "entity_type": entity_type,
        "entity_id": str(entity_id),
        "metadata": metadata,
        "created_at": datetime.utcnow().isoformat(),
    }, sort_keys=True)
    
    # Hash = SHA-256(prev_hash + content)
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

def verify_audit_chain(db: Session) -> list[str]:
    """Returns list of broken chain entries (should be empty if untampered)."""
    entries = db.query(AuditLog).order_by(AuditLog.created_at.asc()).all()
    broken = []
    prev_hash = "GENESIS_HASH_0000"
    for entry in entries:
        expected = hashlib.sha256(
            f"{prev_hash}{entry.canonical_content}".encode()
        ).hexdigest()
        if expected != entry.entry_hash:
            broken.append(f"Entry {entry.id} broken (prev: {entry.prev_hash})")
        prev_hash = entry.entry_hash
    return broken
```

**Actions logged:** document upload, analysis started, analysis complete, consensus computed, cross-doc check, risk score assigned, reviewer decision, audit chain verification.

---

### M8 — Reviewer Dashboard (React) *(~2.5 hours)*

**Goal:** A reviewer can see all applications, drill into any one, understand exactly why it was flagged, and record a decision.

**Pages & components:**

#### Dashboard (`/`)
- Application list table: Applicant Name | Loan Type | Amount | Status badge | Submitted date | Action
- Status badge colors: `PASS` = green, `REVIEW` = amber, `HIGH_RISK_REVIEW` = red (pulsing)
- Filter by status, search by name
- Summary cards: Total | Pending Review | High Risk Today

#### Application Detail (`/applications/:id`)

```
┌─────────────────────────────────────────────────────────┐
│  SYNTHETIC — NOT A REAL APPLICANT                       │  ← banner in DEMO_MODE
│  Rahul Sharma — ₹15,00,000 Home Loan                    │
│  Status: ⚠ REVIEW REQUIRED                             │
│  Risk Score: 74/100                                     │
└─────────────────────────────────────────────────────────┘

[Tabs: Overview | Field Comparison | Rule Engine | Cross-Doc | Audit Log]

── OVERVIEW TAB ──
  Explainability card:
  "The income declared on the salary slip (₹72,000/month) does not align
   with bank statement credits for the same period (₹51,000 avg). 
   Additionally, the employer name 'Acme Corp Ltd' on the salary slip 
   differs from 'ACME CORP LIMITED' in the bank statement — possible 
   formatting inconsistency but requires human confirmation."

  Score breakdown chart (Recharts radar/bar):
    Agreement: 85 | Consistency: 62 | Tamper: 90 | Confidence: 78

── FIELD COMPARISON TAB ──
  Table: Field | Gemini | Mistral | Match | Weight
  Color-coded: green (match), yellow (soft match), red (mismatch), gray (missing)

── RULE ENGINE TAB ──
  Table: Rule | Status | Detail
  Green checkmark / red X / amber warning icons

── CROSS-DOC TAB ──
  Per-check cards showing which documents conflict and by how much

── AUDIT LOG TAB ──
  Chronological log with actor, action, timestamp
  "Verify Chain" button → calls backend verify endpoint → shows pass/fail

── DECISION PANEL (sticky footer) ──
  [ Approve for Underwriting ]  [ Request More Documents ]  [ Reject ]
  Notes textarea
  Disclaimer: "This records your human review decision. The system does
               not make automated approve/reject decisions."
```

**Design system:** Tailwind CSS, dark mode by default, Inter font, Recharts for score visualizations. Status colors use CSS variables so they can be rebranded easily.

**After building:** Use browser tool to click through all 3 seeded scenarios and screenshot each state for pitch deck.

---

### M9 — Seed Data, Tests, Docs *(~1.5 hours)*

**Goal:** Three demo applications that reliably hit all three verdict states.

#### Scenario 1 — Clean Pass (Score ≥ 90)
- **Applicant:** Priya Kapoor (SYNTHETIC)
- **Documents:** Salary slip + Bank statement + ITR
- **Setup:** All fields match perfectly across documents. Income consistent. PAN format valid. All rule checks pass.
- **Expected:** Score 93, status `PASS`

#### Scenario 2 — Minor Mismatch → REVIEW (Score 70–89)
- **Applicant:** Arjun Mehta (SYNTHETIC)  
- **Documents:** Salary slip + Bank statement
- **Setup:** Employer name "Tech Solutions Pvt Ltd" vs "TECH SOLUTIONS PVT. LTD." (casing/punctuation). Salary month off by one. Net salary ±3% of bank credits (within tolerance individually, but combined with name mismatch pushes to REVIEW).
- **Expected:** Score 76, status `REVIEW`
- **Rule check:** All pass (no fraud signals, just ambiguity)

#### Scenario 3 — Cross-Document Fraud → HIGH-RISK REVIEW (Score < 70)
- **Applicant:** Rohit Verma (SYNTHETIC)
- **Documents:** Salary slip + Bank statement + ITR
- **Setup:** 
  - Salary slip shows gross ₹1,20,000/month
  - Bank statement shows avg monthly credits of ₹52,000 (57% gap)
  - ITR shows annual income of ₹6,80,000 (vs salary slip implied ₹14,40,000)
  - Aadhaar checksum deliberately made invalid
  - Document date on salary slip is 6 months in the future
- **Expected:** Score 38, status `HIGH_RISK_REVIEW`

**Synthetic document generation:**  
Ask Antigravity to generate these as minimal HTML-rendered-to-PDF files with "SYNTHETIC DATA — NOT A REAL DOCUMENT" watermarks. No real personal data anywhere.

---

## Test Coverage Plan

### Backend Tests (`pytest`)

```
tests/test_rule_engine.py:
  ✓ valid_pan_passes_format_check
  ✓ invalid_pan_fails_format_check  
  ✓ valid_aadhaar_passes_verhoeff
  ✓ invalid_aadhaar_fails_verhoeff
  ✓ salary_arithmetic_within_tolerance_passes
  ✓ salary_arithmetic_outside_tolerance_fails
  ✓ future_dated_document_fails
  ✓ duplicate_hash_detected_across_applications
  ✓ velocity_check_same_pan_multiple_applications

tests/test_consensus.py:
  ✓ identical_outputs_score_100
  ✓ completely_different_outputs_score_below_50
  ✓ missing_field_from_one_engine_partial_score
  ✓ both_engines_return_null_field_excluded
  ✓ numeric_within_tolerance_match
  ✓ numeric_outside_tolerance_mismatch
  ✓ soft_string_match_scores_07
  ✓ loan_amount_tier_override_raises_pass_threshold

tests/test_cross_doc.py:
  ✓ matching_income_across_docs_passes
  ✓ large_income_gap_salary_vs_itr_flagged
  ✓ mismatched_pan_across_docs_flagged
  ✓ name_mismatch_flagged
  ✓ salary_slip_outside_bank_statement_period_flagged
```

### Frontend Tests (`Playwright`)
- Upload document → classifier returns type
- Dashboard loads, shows 3 seeded applications
- Application detail renders all tabs
- Review decision panel submits and updates status badge

---

## API Contract (OpenAPI summary)

```yaml
paths:
  /api/applications:
    post:
      summary: Create a new loan application
  /api/applications/{id}/documents:
    post:
      summary: Upload a document to an application
  /api/documents/{id}/analyze:
    post:
      summary: Trigger async analysis (Gemini + Mistral + rules)
  /api/applications/{id}/consensus:
    get:
      summary: Field-by-field comparison of both AI outputs
  /api/applications/{id}/risk-score:
    get:
      summary: Aggregate score and routing status
  /api/applications/{id}/dashboard:
    get:
      summary: All data needed by the reviewer UI in one call
  /api/applications/{id}/review:
    post:
      summary: Record human reviewer decision
  /api/audit-logs:
    get:
      summary: Paginated audit trail (filterable by application_id)
  /api/audit-logs/verify:
    get:
      summary: Verify hash chain integrity
  /api/verify:
    post:
      summary: B2B API — single-call document verification
  /health:
    get:
      summary: Health check
```

Full OpenAPI 3.1 spec auto-generated by FastAPI at `/docs`.

---

## Key Technical Differentiators (for the pitch)

| Differentiator | What Makes It Strong | Where in Demo |
|----------------|---------------------|---------------|
| Deterministic rule engine (M4) | Catches fraud even if both AIs are fooled | Scenario 3: Aadhaar checksum fail |
| Hash-chained audit log (M7) | Tamper-evident, verifiable claim | Audit Log tab → "Verify Chain" button |
| Disagreement-as-signal (M5) | Not just pass/fail; partial matches are evidence | Field Comparison tab |
| Cross-doc income reconciliation (M6) | Catches the most common fraud pattern | Scenario 3: salary vs bank vs ITR gap |
| Natural-language explainability (M7) | Reviewer understands *why*, not just *what* | Overview tab explainability card |
| Config-driven weights (M5) | "Tunable" is a real feature, not marketing | `consensus_weights.json` in repo |

---

## Regulatory / Compliance Anchors (for pitch slides)

- **RBI Digital Lending Framework (2022):** Human-in-the-loop requirement → our routing model (never auto approve/reject) directly maps to this
- **DPDP Act 2023 (Digital Personal Data Protection):** No real PII stored; synthetic demo data labeled; `DEMO_MODE` flag; document storage encrypted at rest
- **Audit trail:** Hash-chained log addresses audit requirements for regulated financial institutions

---

## Roadmap Slide (built features → future)

```
Now (Hackathon MVP)                    → Next (Production Pilot)
────────────────────────────────────────────────────────────────
Dual AI pipeline                       → Add 3rd AI provider
Config-driven weights                  → ML-based weight calibration
                                         from reviewer decision data
Hash-chained audit log                 → Write to immutable ledger / WORM
Synthetic demo data                    → Real document ingestion
Mock external verification             → Live PAN/Aadhaar/GST API
Docker Compose                         → Kubernetes on GKE
Demo login                             → RBAC (RM / Senior RM / Auditor roles)
Per-application risk scoring           → Portfolio-level fraud ring detection
```

---

## Build Order for Antigravity (Recommended)

```
Day 1 (Foundation):  M0 → M1 → M2 → M3
Day 2 (Intelligence): M4 → M5 → M6
Day 3 (Polish + Demo): M7 → M8 → M9
```

> [!IMPORTANT]
> Tell Antigravity to **pause after each milestone** and show you the result before proceeding. The M4 rule engine and M5 consensus engine are the highest-risk code — test these early.

> [!TIP]
> Run `make seed` after M9 to populate the three demo scenarios. Then use Antigravity's browser tool to walk through the reviewer dashboard and screenshot all three states — these screenshots are your pitch deck slides.

> [!WARNING]
> Never paste real API keys into the prompt. Set them in `.env` after Antigravity generates the scaffold. The system is built to fail loudly at startup if keys are missing.
