import uuid
from datetime import datetime
from sqlalchemy import Column, String, Float, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.database import Base


class Extraction(Base):
    __tablename__ = "extractions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    engine = Column(String, nullable=False)  # "groq" | "mistral"
    raw_json = Column(JSON, nullable=True)
    structured_json = Column(JSON, nullable=True)
    overall_confidence = Column(Float, default=0.0)
    extraction_failed = Column(Boolean, default=False)
    failure_reason = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    document = relationship("Document", back_populates="extractions")
