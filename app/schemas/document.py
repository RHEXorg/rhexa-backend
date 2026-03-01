# app/schemas/document.py
"""
Pydantic schemas for document-related API operations.

These schemas provide:
- Request validation
- Response serialization
- API documentation (OpenAPI/Swagger)
- Type safety
"""

from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional


class DocumentBase(BaseModel):
    """Base document schema with common fields."""
    filename: str = Field(..., description="Original filename of the uploaded document")
    

class DocumentCreate(BaseModel):
    """
    Schema for document creation (internal use).
    
    This is used internally after file upload.
    The actual upload endpoint uses multipart/form-data.
    """
    filename: str
    file_path: str
    file_size: int
    file_type: str
    organization_id: int
    data_source_id: Optional[int] = None
    extracted_text: Optional[str] = None


class DocumentResponse(BaseModel):
    """
    Schema for document response.
    
    Returned when:
    - Document is uploaded
    - Document details are requested
    - Document is updated
    """
    id: int
    filename: str
    file_size: int = Field(..., description="File size in bytes")
    file_type: str = Field(..., description="File extension (e.g., 'pdf', 'csv')")
    organization_id: int
    data_source_id: Optional[int] = None
    created_at: datetime
    
    # Pydantic v2 configuration
    model_config = ConfigDict(from_attributes=True)


class DocumentList(BaseModel):
    """
    Schema for paginated document list response.
    """
    total: int = Field(..., description="Total number of documents")
    documents: list[DocumentResponse] = Field(..., description="List of documents")
    page: int = Field(1, description="Current page number")
    page_size: int = Field(50, description="Number of documents per page")


class DocumentUploadResponse(BaseModel):
    """
    Schema for successful file upload response.
    
    Provides immediate feedback to client with:
    - Document ID for future reference
    - Processing status
    - File metadata
    """
    success: bool = True
    message: str = "File uploaded successfully"
    document_id: int
    filename: str
    file_size: int
    file_type: str
    extracted_text_length: int = Field(..., description="Length of extracted text in characters")
    processing_time_ms: int = Field(..., description="Processing time in milliseconds")


class ErrorResponse(BaseModel):
    """
    Standard error response schema.
    
    Provides consistent error format across all endpoints.
    """
    success: bool = False
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Detailed error information")
    error_code: Optional[str] = Field(None, description="Machine-readable error code")
