"""
M3 — Mistral OCR Pipeline (AI-B)
Two-stage: Mistral OCR (text + bounding boxes) → structuring LLM pass → ExtractionResult
"""
import json
import base64
import logging
from datetime import datetime
from pathlib import Path
from tenacity import retry, stop_after_attempt, wait_exponential

from mistralai import Mistral
from app.config import settings
from app.schemas.extraction_schema import ExtractionResult, EXTRACTION_SCHEMA_PROMPT

logger = logging.getLogger(__name__)


def _encode_file_base64(file_path: str) -> tuple[str, str]:
    """Returns (base64_content, mime_type)."""
    suffix = Path(file_path).suffix.lower()
    mime_map = {
        ".pdf": "application/pdf",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
    }
    mime = mime_map.get(suffix, "application/octet-stream")
    with open(file_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    return b64, mime


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=False,
)
async def _run_mistral_ocr(file_path: str) -> dict:
    """
    Stage 1: Mistral OCR API — returns markdown text + (if available) bounding boxes.
    Stores raw output in extractions.raw_json for future visual tamper analysis.
    """
    client = Mistral(api_key=settings.MISTRAL_API_KEY)
    b64_content, mime_type = _encode_file_base64(file_path)

    # Mistral OCR API call
    ocr_response = client.ocr.process(
        model=settings.MISTRAL_OCR_MODEL,
        document={
            "type": "base64",
            "data": b64_content,
            "media_type": mime_type,
        },
    )

    # Extract markdown text from all pages
    pages = []
    if hasattr(ocr_response, "pages"):
        for page in ocr_response.pages:
            pages.append({
                "markdown": getattr(page, "markdown", ""),
                "index": getattr(page, "index", 0),
            })
    elif hasattr(ocr_response, "text"):
        pages.append({"markdown": ocr_response.text, "index": 0})

    return {
        "pages": pages,
        "raw_ocr": ocr_response.model_dump() if hasattr(ocr_response, "model_dump") else str(ocr_response),
    }


async def _structure_ocr_output(ocr_data: dict, doc_type: str) -> ExtractionResult:
    """
    Stage 2: Use Mistral LLM to map OCR markdown → shared JSON schema.
    """
    client = Mistral(api_key=settings.MISTRAL_API_KEY)

    # Combine all page markdowns
    combined_text = "\n\n".join(
        p.get("markdown", "") for p in ocr_data.get("pages", [])
    )

    schema_prompt = EXTRACTION_SCHEMA_PROMPT.replace('"engine": "groq"', '"engine": "mistral"')

    response = client.chat.complete(
        model=settings.MISTRAL_STRUCT_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a financial document structuring AI. "
                    "Convert OCR-extracted text into structured JSON. "
                    "Be precise. Use null for unreadable fields. Never hallucinate."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Document type: {doc_type}\n"
                    f"OCR extracted text:\n{combined_text[:6000]}\n\n"
                    f"{schema_prompt}\n\n"
                    "Set engine to 'mistral'."
                ),
            },
        ],
        response_format={"type": "json_object"},
        max_tokens=2048,
        temperature=0.1,
    )

    raw_text = response.choices[0].message.content
    parsed = json.loads(raw_text)
    parsed["engine"] = "mistral"
    parsed["extraction_timestamp"] = datetime.utcnow().isoformat()
    parsed["raw_response"] = raw_text
    return ExtractionResult(**parsed)


async def analyze_with_mistral(
    file_path: str,
    doc_type: str,
) -> tuple[ExtractionResult, dict]:
    """
    Full Mistral pipeline.
    Returns (ExtractionResult, raw_ocr_json) — raw is stored separately for bounding box use.
    """
    from app.services.heuristic_extractor import heuristic_extract

    if not settings.MISTRAL_API_KEY or settings.MISTRAL_API_KEY == "your_mistral_api_key_here":
        logger.info("MISTRAL_API_KEY not configured. Using heuristic intelligent extraction.")
        return heuristic_extract(file_path, doc_type, engine="mistral"), {"pages": [{"markdown": "[Heuristic OCR]"}]}

    try:
        # Stage 1 — OCR
        ocr_data = await _run_mistral_ocr(file_path)

        # Stage 2 — Structure
        result = await _structure_ocr_output(ocr_data, doc_type)

        logger.info(
            f"Mistral extraction complete: doc_type={doc_type}, "
            f"confidence={result.overall_confidence:.2f}"
        )
        return result, ocr_data

    except json.JSONDecodeError as e:
        logger.error(f"Mistral returned invalid JSON: {e}")
        if settings.DEMO_MODE:
            return heuristic_extract(file_path, doc_type, engine="mistral"), {"pages": []}
        return _failed_extraction("mistral", doc_type, f"JSON parse error: {e}"), {}

    except Exception as e:
        logger.error(f"Mistral analysis failed: {type(e).__name__}: {e}")
        if settings.DEMO_MODE:
            return heuristic_extract(file_path, doc_type, engine="mistral"), {"pages": []}
        return _failed_extraction("mistral", doc_type, str(e)), {}


def _failed_extraction(engine: str, doc_type: str, reason: str) -> ExtractionResult:
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
