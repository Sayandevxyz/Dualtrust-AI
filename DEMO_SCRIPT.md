# DualTrust AI — 3-Minute Demo Script

## Setup (do before demo)
```bash
make dev && make seed
```
Open http://localhost:3000 — login with `demo@dualtrust.ai` / `demo1234`

---

## Minute 1: The Dashboard (30 sec) + Scenario 1 PASS (30 sec)

**Say:** "DualTrust AI runs every document through two completely independent AI pipelines — Groq and Mistral — then reconciles them field by field."

1. Show dashboard → 3 applications, 3 different status badges
2. Click **Priya Kapoor** (PASS, score 94)
3. Point to explainability card: "No issues found"
4. Click **Field Comparison** tab → all green checkmarks
5. Click **Rule Engine** tab → all pass

**Key line:** "Clean documents score above 90 — routed straight to underwriting. No human time wasted."

---

## Minute 2: Scenario 2 REVIEW (1 min)

1. Go back → click **Arjun Mehta** (REVIEW, score 76)
2. Show explainability: "Employer name formatting inconsistency + salary month off by one"
3. Field Comparison → show SOFT_MATCH on employer_name (Groq: "Tech Solutions Pvt Ltd", Mistral: "TECH SOLUTIONS PVT. LTD.")
4. Rule Engine → all pass (no fraud signals)

**Key line:** "This isn't fraud — it's ambiguity. The system flags it for a human to confirm, not reject it automatically. Disagreement is a signal, not a verdict."

---

## Minute 3: Scenario 3 HIGH RISK + Audit Chain (1 min)

1. Go back → click **Rohit Verma** (HIGH RISK, score 38, pulsing red)
2. Explainability: read the 4 fraud signals
3. Rule Engine tab → 🔴 AADHAAR_CHECKSUM FAIL, 🔴 DATE_FUTURE FAIL
4. Cross-Document tab → 45% income gap salary vs bank, 52% salary vs ITR

**Key line:** "Even if both AIs were fooled by a photoshopped salary slip, the Aadhaar checksum check is pure math — it doesn't care what the AI thinks."

5. Audit Log tab → click **Verify Hash Chain** → ✓ Chain Valid
6. "Every action is hash-chained. Editing a past log entry breaks the chain instantly — provable tamper-evidence for compliance audits."

---

## Decision Panel (close out)
- Show sticky footer: "Approve / Request More / Reject"
- Point to disclaimer: "The system never decides — it routes. Human reviewers decide."

---

## If Asked: "What if both AIs make the same mistake?"
> "That's exactly why we built the deterministic rule engine. It runs independently of any AI — Verhoeff checksum, PAN format validation, arithmetic checks. A forged Aadhaar that fools both vision models still fails its checksum instantly. The rule engine is the third validator that doesn't learn, doesn't hallucinate, and doesn't have an API quota."
