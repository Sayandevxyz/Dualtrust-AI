"""Review routes — human reviewer decisions."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Review, Application, ApplicationStatus
from app.schemas.api_schemas import ReviewCreate, ReviewResponse
from app.services.explainer import append_audit_log

router = APIRouter()


@router.post("/{app_id}/review", response_model=ReviewResponse, status_code=201)
def submit_review(app_id: str, payload: ReviewCreate, db: Session = Depends(get_db)):
    app = db.query(Application).filter(Application.id == app_id).first()
    if not app:
        raise HTTPException(404, "Application not found")

    review = Review(
        application_id=app_id,
        reviewer_id="demo-user",
        decision=payload.decision,
        notes=payload.notes,
    )
    db.add(review)
    app.status = ApplicationStatus.decided
    db.commit()
    db.refresh(review)

    append_audit_log("reviewer", "review_submitted", "application", app_id,
                     {"decision": payload.decision, "has_notes": bool(payload.notes)}, db)

    return review


@router.get("/{app_id}/reviews", response_model=list[ReviewResponse])
def get_reviews(app_id: str, db: Session = Depends(get_db)):
    return db.query(Review).filter(Review.application_id == app_id).all()
