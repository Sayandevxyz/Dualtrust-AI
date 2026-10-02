"""
M1 — Document Classifier
Priority: filename keywords → PDF text layer → Groq fallback (for scanned docs)
"""
import re
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

CLASSIFIER_RULES: dict[str, list[str]] = {
    "pan_card": [
        r"permanent account number", r"income.?tax.?dep(t|artment)",
        r"\bpan\b.*card", r"govt\. of india.*pan",
    ],
    "aadhaar": [
        r"unique identification", r"\baadhaar\b", r"\buidai\b",
        r"enrolment no", r"your aadhaar",
    ],
    "salary_slip": [
        r"salary.?slip", r"pay.?slip", r"net.?pay", r"gross.?salary",
        r"payroll", r"employee.?pay", r"monthly.?salary",
    ],
    "bank_statement": [
        r"bank.?statement", r"account.?statement", r"closing.?balance",
        r"opening.?balance", r"transaction.?history", r"statement.?of.?account",
    ],
    "itr": [
        r"income.?tax.?return", r"\bitr.?\d\b", r"assessment.?year",
        r"return.?of.?income", r"central.?board.?of.?direct.?taxes",
    ],
    "gst": [
        r"goods.?and.?services.?tax", r"\bgstin\b", r"\bgstr\b",
        r"gst.?registration", r"tax.?invoice",
    ],
    "address_proof": [
        r"electricity.?bill", r"utility.?bill", r"registered.?address",
        r"water.?bill", r"telephone.?bill",
    ],
}

FILENAME_KEYWORDS: dict[str, list[str]] = {
    "pan_card":       ["pan", "pan_card", "pancard"],
    "aadhaar":        ["aadhaar", "aadhar", "uid"],
    "salary_slip":    ["salary", "payslip", "pay_slip", "salaryslip"],
    "bank_statement": ["bank", "statement", "bankstatement"],
    "itr":            ["itr", "income_tax_return", "incometax"],
    "gst":            ["gst", "gstin"],
    "address_proof":  ["address", "electricity", "utility"],
}


def classify_by_filename(filename: str) -> Optional[str]:
    """Fast O(1) classification from filename."""
    stem = Path(filename).stem.lower().replace("-", "_").replace(" ", "_")
    for doc_type, keywords in FILENAME_KEYWORDS.items():
        if any(kw in stem for kw in keywords):
            return doc_type
    return None


def classify_by_text(text: str) -> Optional[str]:
    """Regex classification on document text content."""
    text_lower = text.lower()
    scores: dict[str, int] = {}
    for doc_type, patterns in CLASSIFIER_RULES.items():
        matches = sum(1 for p in patterns if re.search(p, text_lower))
        if matches > 0:
            scores[doc_type] = matches
    if not scores:
        return None
    return max(scores, key=scores.get)


def extract_pdf_text(file_path: str) -> str:
    """Extract text from PDF (text layer only — fast, no OCR)."""
    try:
        import PyPDF2
        with open(file_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            text = " ".join(
                page.extract_text() or "" for page in reader.pages[:2]
            )
        return text
    except Exception as e:
        logger.warning(f"PDF text extraction failed: {e}")
        return ""


async def classify_document(
    file_path: str,
    original_filename: str,
    hint_type: Optional[str] = None,
) -> tuple[str, float]:
    """
    Classify a document. Returns (doc_type, confidence).
    Confidence: 1.0 = certain, 0.7 = text regex, 0.5 = filename only.
    """
    # 0. Use explicit hint if provided
    if hint_type and hint_type in CLASSIFIER_RULES:
        return hint_type, 1.0

    # 1. Filename keywords (fast)
    by_filename = classify_by_filename(original_filename)

    # 2. PDF text layer
    text = ""
    if file_path.endswith(".pdf"):
        text = extract_pdf_text(file_path)

    by_text = classify_by_text(text) if text else None

    # Decision logic
    if by_text:
        confidence = 0.90 if by_text == by_filename else 0.75
        return by_text, confidence
    if by_filename:
        return by_filename, 0.55

    # 3. Groq fallback (for scanned images with no text layer)
    try:
        groq_type = await classify_with_groq(file_path)
        if groq_type:
            return groq_type, 0.65
    except Exception as e:
        logger.warning(f"Groq classification fallback failed: {e}")

    return "unknown", 0.0


async def classify_with_groq(file_path: str) -> Optional[str]:
    """Use Groq (text-only) to classify if we have extracted text."""
    from app.config import settings
    from groq import Groq

    # For scanned images, try to get text with pdf2image + basic OCR hint
    text_hint = extract_pdf_text(file_path)
    if not text_hint:
        return None

    client = Groq(api_key=settings.GROQ_API_KEY)
    response = client.chat.completions.create(
        model=settings.GROQ_MODEL,
        messages=[{
            "role": "user",
            "content": (
                f"Classify this financial document text into ONE of these categories: "
                f"pan_card, aadhaar, salary_slip, bank_statement, itr, gst, address_proof, unknown.\n"
                f"Reply with ONLY the category name, nothing else.\n\n"
                f"Document text (first 500 chars):\n{text_hint[:500]}"
            )
        }],
        max_tokens=20,
        temperature=0,
    )
    result = response.choices[0].message.content.strip().lower()
    valid = list(CLASSIFIER_RULES.keys()) + ["unknown"]
    return result if result in valid else "unknown"
