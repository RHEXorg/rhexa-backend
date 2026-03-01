# app/schemas/chat.py
"""
Pydantic models for Key Chat API.
"""

from typing import List, Optional, Any, Dict
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class Citation(BaseModel):
    """Source document reference"""
    document_id: int
    filename: str
    page: Optional[int] = None
    text_snippet: str
    score: float


class ChatRequest(BaseModel):
    """User question structure"""
    message: str = Field(..., min_length=1)
    session_id: Optional[int] = None  # None = New Session
    document_ids: Optional[List[int]] = None
    database_ids: Optional[List[int]] = None


class ChatResponse(BaseModel):
    """AI answer structure"""
    answer: str
    session_id: int
    citations: List[Citation] = []
    created_at: datetime


class ChatSessionList(BaseModel):
    """List of sessions for sidebar"""
    id: int
    title: Optional[str] = None
    updated_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ChatMessageHistory(BaseModel):
    """History of a session"""
    role: str
    content: str
    created_at: datetime
    citations: Optional[List[Citation]] = None

    model_config = ConfigDict(from_attributes=True)
