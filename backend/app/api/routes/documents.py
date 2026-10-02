"""Document upload routes."""
import hashlib
import os
import shutil
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Application, Document, DocumentType
from app.schemas.api_schemas import DocumentResponse
from app.services.classifier import classify_document
from app.services.explainer import append_audit_log
from app.config import settings

router = APIRouter()


def _compute_phash(file_path: str) -> str:
    """Compute perceptual hash for near-duplicate detection."""
    try:
        import imagehash
        from PIL import Image
        from pdf2image import convert_from_path

        if file_path.endswith(".pdf"):
            images = convert_from_path(file_path, first_page=1, last_page=1, dpi=72)
            if images:
                return str(imagehash.phash(images[0]))
        else:
            img = Image.open(file_path)
            return str(imagehash.phash(img))
    except Exception:
        return ""


@router.post("/{app_id}/documents", response_model=DocumentResponse, status_code=201)
async def upload_document(
    app_id: str,
    file: UploadFile = File(...),
    hint_type: str = Form(default=None),
    db: Session = Depends(get_db),
):
    app = db.query(Application).filter(Application.id == app_id).first()
    if not app:
        raise HTTPException(404, "Application not found")

    # Save file
    storage_dir = os.path.join(settings.DOCUMENT_STORAGE_PATH, app_id)
    os.makedirs(storage_dir, exist_ok=True)
    file_path = os.path.join(storage_dir, file.filename)

    contents = await file.read()
    with open(file_path, "wb") as f:
        f.write(contents)

    # Compute hashes
    file_hash = hashlib.sha256(contents).hexdigest()
    phash = _compute_phash(file_path)

    # Classify
    doc_type_str, confidence = await classify_document(file_path, file.filename, hint_type)

    # Map to enum
    try:
        doc_type = DocumentType(doc_type_str)
    except ValueError:
        doc_type = DocumentType.unknown

    doc = Document(
        application_id=app_id,
        doc_type=doc_type,
        file_path=file_path,
        file_hash=file_hash,
        phash=phash or None,
        original_filename=file.filename,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    append_audit_log("api", "document_uploaded", "document", doc.id,
                     {"doc_type": doc_type_str, "filename": file.filename,
                      "file_hash": file_hash[:16] + "...", "classifier_confidence": confidence}, db)

    return doc
