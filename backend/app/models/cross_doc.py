import uuid
from datetime import datetime
from sqlalchemy import Column, String, Float, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.database import Base


class CrossDocumentCheck(Base):
    __tablename__ = "cross_document_checks"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    application_id = Column(String, ForeignKey("applications.id", ondelete="CASCADE"), nullable=False)
    check_type = Column(String, nullable=False)
    documents_involved = Column(JSON, default=list)
    result = Column(String, nullable=False)  # "OK" | "DISCREPANCY"
    discrepancy_amount = Column(Float, nullable=True)
    discrepancy_pct = Column(Float, nullable=True)
    detail = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    application = relationship("Application", back_populates="cross_doc_checks")
