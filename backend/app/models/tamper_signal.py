import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import relationship
from app.database import Base
from app.models.enums import RuleSeverity


class TamperSignal(Base):
    __tablename__ = "tamper_signals"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    signal_type = Column(String, nullable=False)
    description = Column(String, nullable=False)
    severity = Column(SAEnum(RuleSeverity), default=RuleSeverity.review, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    document = relationship("Document", back_populates="tamper_signals")
