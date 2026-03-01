from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text
from sqlalchemy.sql import func
from app.db.session import Base

class Document(Base):
    """
    Document model for storing uploaded file metadata.
    
    Stores file information and metadata for multi-tenant document management.
    The actual file content is stored in the file system (or S3 in production).
    Extracted text is stored for AI processing and search.
    """
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False, index=True)
    file_path = Column(String, nullable=False)  # Storage path (local or S3 key)
    file_size = Column(Integer, nullable=False)  # Size in bytes
    file_type = Column(String, nullable=False)  # Extension: pdf, csv, xlsx, txt

    data_source_id = Column(Integer, ForeignKey("data_sources.id"), nullable=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
