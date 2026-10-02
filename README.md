# DualTrust AI 🛡

> **AI-assisted loan document verification with dual independent pipelines, consensus scoring, and explainable human-review routing.**
>
> ⚠️ This system routes applications to human reviewers. It never issues automated approve/reject decisions.

---

## Quick Start

```bash
# 1. Clone & setup
git clone <repo>
cd dualtrust-ai
make setup           # copies .env.example → .env

# 2. Add API keys in .env
#    GROQ_API_KEY=...
#    MISTRAL_API_KEY=...

# 3. Start everything
make dev             # docker-compose up --build

# 4. Seed demo data
make seed            # creates 3 synthetic test applications

# 5. Open browser
#    Frontend: http://localhost:3000
#    API docs: http://localhost:8000/docs
#    Login: demo@dualtrust.ai / demo1234
```

---

## Architecture

```
Document Upload
      │
      ▼
Document Classifier (PAN / Aadhaar / Salary Slip / Bank Statement / ITR / GST)
      │
      ├──────────────┬──────────────────────────────┐
      ▼              ▼                              ▼
  AI-A: Groq    AI-B: Mistral OCR         Deterministic Rule Engine
  (structured    + structuring layer       (checksums, arithmetic,
   JSON output)    → same JSON schema)      date logic, duplicates)
      │              │                              │
      └──────┬───────┘                              │
             ▼                                      │
      Consensus Engine  ◄───────────────────────────┘
   (field match + weighted score from consensus_weights.json)
             │
             ▼
   Cross-Document Verification
   (income/date/identity reconciliation across docs)
             │
             ▼
      Risk & Confidence Score
             │
    ┌────────┼────────┐
    ▼        ▼        ▼
  PASS    REVIEW  HIGH-RISK
    └────────┴────┬───┘
                  ▼
         Human Reviewer Dashboard
         (evidence view, explainability)
                  │
                  ▼
         Hash-Chained Audit Log
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18 + Vite + TypeScript + Recharts |
| Backend | Python 3.11 + FastAPI + Pydantic v2 |
| Database | PostgreSQL 15 (SQLAlchemy + Alembic) |
| Cache/Queue | Redis + RQ |
| AI-A | Groq API (`llama-3.3-70b-versatile`) |
| AI-B | Mistral OCR API + Mistral LLM |
| Containers | Docker Compose |

## Demo Scenarios (seeded)

| # | Applicant | Status | What to Show |
|---|-----------|--------|-------------|
| 1 | Priya Kapoor | ✅ PASS (94/100) | All fields match, all rules pass |
| 2 | Arjun Mehta | ⚠️ REVIEW (76/100) | Minor name/date formatting differences |
| 3 | Rohit Verma | 🔴 HIGH RISK (38/100) | Aadhaar checksum fail + future date + income cross-doc gap |

## Rule Engine (Deterministic — AI-independent)

| Rule | What It Checks |
|------|---------------|
| PAN_FORMAT | 5 letters + 4 digits + 1 letter; valid category code |
| AADHAAR_CHECKSUM | Verhoeff algorithm on 12 digits |
| GSTIN_CHECKSUM | Mod-36 check digit |
| IFSC_FORMAT | 11-char format AAAA0XXXXXX |
| SALARY_ARITHMETIC | gross − deductions ≈ net (±2%) |
| DATE_FUTURE | No document dated in future |
| SALARY_AGE | Salary slip within 90 days of application |
| DUPLICATE_HASH | SHA-256 match across all applications |
| VELOCITY_PAN | Same PAN in >2 apps in 30 days |
| VELOCITY_ACCOUNT | Same account in >2 apps in 30 days |

## Consensus Weights

Edit [`consensus_weights.json`](./consensus_weights.json) — no code change needed:

```json
{
  "weights": {
    "agreement_score": 0.40,
    "cross_document_consistency": 0.30,
    "tamper_and_rule_signals": 0.20,
    "ocr_model_confidence": 0.10
  },
  "thresholds": { "pass": 90, "review": 70 }
}
```

## Regulatory Anchors

- **RBI Digital Lending Framework (2022):** Human-in-the-loop required — this system only routes, never decides.
- **DPDP Act 2023:** No real PII stored; demo data synthetic; document storage encrypted; DEMO_MODE banner shown.
- **Audit trail:** Hash-chained log — editing any past entry breaks the chain, detectable via `/api/audit-logs/verify`.

## Non-Goals (MVP Scope)

- ❌ No real PAN/Aadhaar/GST API verification (`EXTERNAL_VERIFICATION_ENABLED=false`)
- ❌ No production billing
- ❌ No real user PII — all seed data is synthetic and labeled

## Run Tests

```bash
make test        # via Docker
make test-local  # local pytest
```
