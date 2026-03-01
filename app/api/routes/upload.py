# app/api/routes/upload.py
"""
Professional file upload API for RheXa.

This module provides enterprise-grade file upload functionality with:
- JWT Authentication & Multi-tenant isolation
- File validation and security
- Transaction safety
"""

import time
import logging
from pathlib import Path
from fastapi import BackgroundTasks
from app.services.rag_service import index_document
from app.services.billing_service import check_limit

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_storage_backend, require_organization_access, get_current_active_user
from app.core.storage import StorageBackend
from app.models.document import Document
from app.models.user import User
from app.schemas.document import (
    DocumentResponse,
    DocumentList,
    DocumentUploadResponse,
    ErrorResponse
)
from app.ingestion import load_file

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/documents", tags=["documents"])

# Configuration
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_EXTENSIONS = {'.pdf', '.txt', '.csv', '.xlsx', '.xls'}


def validate_file(file: UploadFile) -> tuple[bool, str]:
    """Validate uploaded file for security and compliance."""
    if not file.filename:
        return False, "No file provided"
    
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        return False, f"File type '{ext}' not supported. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"
    
    if len(file.filename) > 255:
        return False, "Filename too long"
    
    return True, ""

@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a document",
)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="File to upload"),
    data_source_id: int = Query(None, description="Optional data source ID"),
    db: Session = Depends(get_db),
    storage: StorageBackend = Depends(get_storage_backend),
    current_org_id: int = Depends(require_organization_access)
):
    """
    Upload and index a document.
    
    Processing:
    1. Validation & Storage (Synchronous)
    2. Text Extraction (Synchronous for now)
    3. RAG Indexing (Background Task)
    """
    start_time = time.time()
    
    try:
        # Check Billing limits
        check_limit(db, current_org_id, "files")

        # Step 1: Validate file
        logger.info(f"Validating upload: {file.filename} for org {current_org_id}")
        is_valid, error_msg = validate_file(file)
        if not is_valid:
            raise HTTPException(status_code=400, detail=error_msg)
        
        # Step 2: Check file size
        file.file.seek(0, 2)
        file_size = file.file.tell()
        file.file.seek(0)
        
        if file_size > MAX_FILE_SIZE:
             raise HTTPException(
                status_code=413,
                detail=f"File exceeds {MAX_FILE_SIZE/(1024*1024)}MB limit"
            )
        
        # Step 3: Save file to storage
        try:
            file_path = storage.save(file.file, file.filename, current_org_id)
        except Exception as e:
            logger.error(f"Storage error: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to save file")
        
        # Step 4: Extract text
        try:
            full_path = storage.get_full_path(file_path)
            extracted_text = load_file(full_path, organization_id=current_org_id)
            text_length = len(extracted_text)
        except Exception as e:
            logger.error(f"Extraction failed: {str(e)}")
            storage.delete(file_path)
            raise HTTPException(status_code=500, detail="Failed to extract text")
        
        # Step 5: Create DB record
        try:
            document = Document(
                filename=file.filename,
                file_path=file_path,
                file_size=file_size,
                file_type=Path(file.filename).suffix.lower().replace('.', ''),
                organization_id=current_org_id,
                data_source_id=data_source_id
            )
            db.add(document)
            db.commit()
            db.refresh(document)
        except Exception as e:
            logger.error(f"DB error: {str(e)}")
            db.rollback()
            storage.delete(file_path)
            raise HTTPException(status_code=500, detail="Failed to save metadata")
            
        # Step 6: Trigger Indexing (Background)
        # We pass the extracted text directly to avoid re-reading
        background_tasks.add_task(
            index_document, 
            db=db, 
            document=document, 
            extracted_text=extracted_text
        )
        
        return DocumentUploadResponse(
            document_id=document.id,
            filename=document.filename,
            file_size=document.file_size,
            file_type=document.file_type,
            extracted_text_length=text_length,
            processing_time_ms=int((time.time() - start_time) * 1000)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred")


@router.get(
    "/",
    response_model=DocumentList,
    summary="List documents",
)
def list_documents(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_org_id: int = Depends(require_organization_access)
):
    """List documents for authenticated organization."""
    total = db.query(Document).filter(Document.organization_id == current_org_id).count()
    documents = db.query(Document).filter(
        Document.organization_id == current_org_id
    ).order_by(Document.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    
    return DocumentList(total=total, documents=documents, page=page, page_size=page_size)


@router.get(
    "/{document_id}",
    response_model=DocumentResponse,
    summary="Get document details",
)
def get_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_org_id: int = Depends(require_organization_access)
):
    """Get document details with auth check."""
    document = db.query(Document).filter(
        Document.id == document_id, 
        Document.organization_id == current_org_id
    ).first()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return document


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete document",
)
def delete_document(
    document_id: int,
    db: Session = Depends(get_db),
    storage: StorageBackend = Depends(get_storage_backend),
    current_org_id: int = Depends(require_organization_access)
):
    """Securely delete document and file."""
    document = db.query(Document).filter(
        Document.id == document_id, 
        Document.organization_id == current_org_id
    ).first()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    try:
        storage.delete(document.file_path)
        # Also delete from vector store
        from app.rag.vector_store import vector_store_manager
        vector_store_manager.delete_document(current_org_id, document_id)
    except Exception as e:
        logger.error(f"Error during physical deletion of document {document_id}: {e}")
        
    db.delete(document)
    db.commit()


@router.get("/upload/info", summary="Get upload limits")
def get_upload_info(current_user: User = Depends(get_current_active_user)):
    """Get limits for authenticated users."""
    return {
        "max_file_size_mb": MAX_FILE_SIZE / (1024 * 1024),
        "allowed_extensions": list(ALLOWED_EXTENSIONS)
    }
