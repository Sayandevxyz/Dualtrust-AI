import uuid
from datetime import datetime
from sqlalchemy import Column, String, Float, Boolean, DateTime, Enum as SAEnum
from sqlalchemy.orm import relationship
from app.database import Base
from app.models.enums import ApplicationStatus


class Application(Base):
    __tablename__ = "applications"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    applicant_name = Column(String, nullable=False)
    loan_type = Column(String, nullable=False, default="personal")
    loan_amount = Column(Float, nullable=False, default=0.0)
    status = Column(SAEnum(ApplicationStatus), default=ApplicationStatus.pending, nullable=False)
    is_synthetic = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    documents = relationship("Document", back_populates="application", cascade="all, delete-orphan")
    risk_scores = relationship("RiskScore", back_populates="application", cascade="all, delete-orphan")
    consensus_results = relationship("ConsensusResult", back_populates="application", cascade="all, delete-orphan")
    cross_doc_checks = relationship("CrossDocumentCheck", back_populates="application", cascade="all, delete-orphan")
    reviews = relationship("Review", back_populates="application", cascade="all, delete-orphan")
