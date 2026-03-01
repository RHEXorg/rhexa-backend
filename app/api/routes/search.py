# app/api/routes/search.py
"""
Search API for RAG testing.
"""

from typing import List, Any
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.api.deps import require_organization_access
from app.services.rag_service import search_similar

router = APIRouter(prefix="/api/search", tags=["search"])

class SearchResult(BaseModel):
    content: str
    metadata: dict
    score: float

class SearchRequest(BaseModel):
    query: str
    limit: int = 5

@router.post("/query", response_model=List[SearchResult])
def search_documents(
    request: SearchRequest,
    current_org_id: int = Depends(require_organization_access)
):
    """
    Search for relevant document chunks using Vector Search.
    """
    results = search_similar(current_org_id, request.query, request.limit)
    
    # Format results
    # LangChain FAISS returns (Document, score)
    response = []
    for doc, score in results:
        response.append(SearchResult(
            content=doc.page_content,
            metadata=doc.metadata,
            score=float(score)
        ))
        
    return response
