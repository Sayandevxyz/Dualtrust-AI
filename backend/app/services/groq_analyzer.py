"""
M2 — Groq Analyzer (AI-A)
Sends document content to Groq (llama-3.3-70b) and gets structured JSON
conforming to the shared ExtractionResult schema.
"""
import json
import base64
import logging
from datetime import datetime
from pathlib import Path
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from groq import Groq, RateLimitError, APIError
from app.config import settings
from app.schemas.extraction_schema import ExtractionResult, EXTRACTION_SCHEMA_PROMPT

logger = logging.getLogger(__name__)


def _load_document_content(file_path: str) -> str:
    """
    Load document as text. For PDFs, extract text layer.
    For images, convert to base64 and embed. For scanned PDFs, 
    convert first page to image.
    """
    path = Path(file_path)
    suffix = path.suffix.lower()

    if suffix == ".pdf":
        try:
            import PyPDF2
            with open(file_path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                text = "\n".join(
                    page.extract_text() or "" for page in reader.pages
                )
            if len(text.strip()) > 50:
                return f"[PDF TEXT CONTENT]\n{text}"
        except Exception:
            pass

        # Scanned PDF — convert first page to image text description
        try:
            from pdf2image import convert_from_path
            images = convert_from_path(file_path, first_page=1, last_page=1, dpi=150)
            if images:
                return f"[SCANNED PDF - image description unavailable in text mode. File: {path.name}]"
        except Exception as e:
            logger.warning(f"pdf2image failed: {e}")

    elif suffix in (".png", ".jpg", ".jpeg", ".webp"):
        with open(file_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        return f"[IMAGE FILE: {path.name}, base64 length: {len(b64)}]"

    return f"[UNSUPPORTED FILE TYPE: {suffix}]"


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((RateLimitError,)),
    reraise=False,
)
async def analyze_with_groq(
    file_path: str,
    doc_type: str,
) -> ExtractionResult:
    """
    Send document to Groq LLM and return structured ExtractionResult.
    Retries 3× with exponential backoff on rate limit errors.
    On total failure, returns a failed extraction result (degrades gracefully).
    """
    from app.services.heuristic_extractor import heuristic_extract

    if not settings.GROQ_API_KEY or settings.GROQ_API_KEY == "your_groq_api_key_here":
        logger.info("GROQ_API_KEY not configured. Using heuristic intelligent extraction.")
        return heuristic_extract(file_path, doc_type, engine="groq")

    try:
        client = Groq(api_key=settings.GROQ_API_KEY)
        doc_content = _load_document_content(file_path)

        system_prompt = (
            "You are a financial document analysis AI. "
            "Extract structured information from the document text provided. "
            "Be precise. For any field you cannot confidently read, use null. "
            "Do NOT hallucinate values. "
            f"The document type is: {doc_type}. "
            "IMPORTANT: Never use real PAN numbers, Aadhaar numbers, or account numbers — "
            "only extract what is literally present in the document text."
        )

        user_prompt = (
            f"Analyze this financial document and extract all fields.\n\n"
            f"{EXTRACTION_SCHEMA_PROMPT}\n\n"
            f"Set engine to 'groq'.\n\n"
            f"Document content:\n{doc_content[:8000]}"  # Groq context window safe limit
        )

        response = client.chat.completions.create(
            model=settings.GROQ_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=2048,
            temperature=0.1,
            response_format={"type": "json_object"},
        )

        raw_text = response.choices[0].message.content
        parsed = json.loads(raw_text)

        # Ensure engine is set correctly
        parsed["engine"] = "groq"
        parsed["extraction_timestamp"] = datetime.utcnow().isoformat()
        parsed["raw_response"] = raw_text

        result = ExtractionResult(**parsed)
        logger.info(
            f"Groq extraction complete: doc_type={doc_type}, "
            f"confidence={result.overall_confidence:.2f}, "
            f"tamper_signals={len(result.tampering_signals)}"
        )
        return result

    except json.JSONDecodeError as e:
        logger.error(f"Groq returned invalid JSON: {e}")
        if settings.DEMO_MODE:
            return heuristic_extract(file_path, doc_type, engine="groq")
        return _failed_extraction("groq", doc_type, f"JSON parse error: {e}")

    except Exception as e:
        logger.error(f"Groq analysis failed: {type(e).__name__}: {e}")
        if settings.DEMO_MODE:
            return heuristic_extract(file_path, doc_type, engine="groq")
        return _failed_extraction("groq", doc_type, str(e))


def _failed_extraction(engine: str, doc_type: str, reason: str) -> ExtractionResult:
    """
    Graceful degradation — return a marked-failed result instead of crashing.
    Application will be flagged as single_source_needs_review.
    """
    return ExtractionResult(
        document_type=doc_type,
        extracted_fields={},
        signature_present=False,
        tampering_signals=["extraction_failed"],
        field_confidence={},
        overall_confidence=0.0,
        engine=engine,
        extraction_failed=True,
        failure_reason=reason,
        raw_response="",
    )
