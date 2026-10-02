import uuid
from datetime import datetime
from sqlalchemy import Column, String, Float, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import relationship
from app.database import Base
from app.models.enums import MatchStatus


class ConsensusResult(Base):
    __tablename__ = "consensus_results"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    application_id = Column(String, ForeignKey("applications.id", ondelete="CASCADE"), nullable=False)
    document_id = Column(String, ForeignKey("documents.id", ondelete="CASCADE"), nullable=True)
    field_name = Column(String, nullable=False)
    groq_value = Column(String, nullable=True)
    mistral_value = Column(String, nullable=True)
    match_status = Column(SAEnum(MatchStatus), nullable=False)
    weight = Column(Float, default=1.0)
    score_contribution = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    application = relationship("Application", back_populates="consensus_results")
    document = relationship("Document", back_populates="consensus_results")
