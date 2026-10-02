import uuid
from datetime import datetime
from sqlalchemy import Column, String, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database import Base


class RiskScore(Base):
    __tablename__ = "risk_scores"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    application_id = Column(String, ForeignKey("applications.id", ondelete="CASCADE"), nullable=False)
    agreement_score = Column(Float, default=0.0)
    consistency_score = Column(Float, default=0.0)
    tamper_score = Column(Float, default=0.0)
    rule_score = Column(Float, default=0.0)
    confidence_score = Column(Float, default=0.0)
    overall_score = Column(Float, default=0.0)
    status = Column(String, nullable=False)  # "PASS", "REVIEW", "HIGH_RISK_REVIEW"
    explanation_text = Column(Text, nullable=True)
    single_source = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    application = relationship("Application", back_populates="risk_scores")
