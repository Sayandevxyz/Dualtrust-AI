import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import relationship
from app.database import Base
from app.models.enums import DocumentType


class Document(Base):
    __tablename__ = "documents"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    application_id = Column(String, ForeignKey("applications.id", ondelete="CASCADE"), nullable=False)
    doc_type = Column(SAEnum(DocumentType), default=DocumentType.unknown, nullable=False)
    file_path = Column(String, nullable=False)
    file_hash = Column(String, index=True, nullable=False)
    phash = Column(String, nullable=True)
    original_filename = Column(String, nullable=True)
    uploaded_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    application = relationship("Application", back_populates="documents")
    extractions = relationship("Extraction", back_populates="document", cascade="all, delete-orphan")
    rule_checks = relationship("RuleCheck", back_populates="document", cascade="all, delete-orphan")
    tamper_signals = relationship("TamperSignal", back_populates="document", cascade="all, delete-orphan")
    consensus_results = relationship("ConsensusResult", back_populates="document", cascade="all, delete-orphan")
