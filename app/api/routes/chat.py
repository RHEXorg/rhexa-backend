# app/api/routes/chat.py
"""
Chat API.
Handles RAG interactions and history management.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.api.deps import get_db, require_organization_access, get_current_user, get_current_active_user
from app.models.user import User
from app.models.chat_session import ChatSession, ChatMessage
from app.models.document import Document
from app.models.database_connection import DatabaseConnection
from app.schemas.chat import ChatRequest, ChatResponse, ChatSessionList, ChatMessageHistory
from app.services.rag_service import generate_answer
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post(
    "/",
    response_model=ChatResponse,
    summary="Send message",
    description="Send a message to the AI and get a RAG-powered response."
)
def send_message(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_org_id: int = Depends(require_organization_access),
    current_user: User = Depends(get_current_user)
):
    """
    RAG Chat Flow:
    1. Get/Create Session
    2. Save User Message
    3. Generate AI Answer (RAG)
    4. Save AI Message
    5. Return Response
    """
    try:
        # 1. Session Management
        if request.session_id:
            # Verify ownership
            session = db.query(ChatSession).filter(
                ChatSession.id == request.session_id,
                ChatSession.organization_id == current_org_id,
                ChatSession.user_id == current_user.id
            ).first()
            if not session:
                raise HTTPException(status_code=404, detail="Session not found")
        else:
            # Check session limit (200 sessions max)
            existing_sessions = db.query(ChatSession).filter(
                ChatSession.user_id == current_user.id
            ).order_by(ChatSession.updated_at.desc()).all()
            
            if len(existing_sessions) >= 200:
                # Delete oldest sessions beyond 199 to make room for 200th
                to_delete = existing_sessions[199:]
                for old_sess in to_delete:
                    db.delete(old_sess)
                db.commit()

            # Create new session
            title = request.message[:50] + "..." if len(request.message) > 50 else request.message
            session = ChatSession(
                user_id=current_user.id,
                organization_id=current_org_id,
                title=title
            )
            db.add(session)
            db.commit()
            db.refresh(session)
            
        # 2. Save User Message
        user_msg = ChatMessage(
            session_id=session.id,
            role="user",
            content=request.message,
            citations=None
        )
        db.add(user_msg)
        db.commit()
        
        # 3. Build conversation history from this session
        history_messages = db.query(ChatMessage).filter(
            ChatMessage.session_id == session.id
        ).order_by(ChatMessage.created_at).all()
        
        # Take the last 20 messages to keep context manageable
        conversation_history = [
            {"role": msg.role, "content": msg.content}
            for msg in history_messages[-20:]
        ]
        
        # 4. Check for data sources before generating answer
        docs_count = db.query(Document).filter(Document.organization_id == current_org_id).count()
        db_count = db.query(DatabaseConnection).filter(DatabaseConnection.organization_id == current_org_id).count()

        if docs_count == 0 and db_count == 0:
            rag_response = {
                "answer": "No file or database connected. Please upload documents or connect a database first.",
                "citations": []
            }
        else:
            # Prepare IDs - ensure they are passed as None if empty
            doc_ids = request.document_ids if request.document_ids and len(request.document_ids) > 0 else None
            db_ids = request.database_ids if request.database_ids and len(request.database_ids) > 0 else None
            
            logger.info(f"Generating RAG answer for org {current_org_id}")
            logger.info(f"Selected Documents: {doc_ids}, Selected Databases: {db_ids}")
            
            rag_response = generate_answer(
                organization_id=current_org_id,
                query=request.message,
                conversation_history=conversation_history,
                document_ids=doc_ids,
                database_ids=db_ids
            )
            
            logger.info(f"Answer generated with {len(rag_response.get('citations', []))} citations")
        
        # 4. Save Assistant Message
        ai_msg = ChatMessage(
            session_id=session.id,
            role="assistant",
            content=rag_response["answer"],
            citations=[c.dict() if hasattr(c, 'dict') else c for c in rag_response["citations"]]
        )
        db.add(ai_msg)
        
        # Update session timestamp
        session.updated_at = ai_msg.created_at
        db.commit()
        
        return ChatResponse(
            answer=rag_response["answer"],
            session_id=session.id,
            citations=rag_response["citations"],
            created_at=ai_msg.created_at
        )

    except Exception as e:
        logger.exception(f"Chat error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while generating the response: {str(e)}"
        )


@router.get(
    "/sessions",
    response_model=list[ChatSessionList],
    summary="List sessions"
)
def list_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """List all chat sessions for the current user."""
    sessions = db.query(ChatSession).filter(
        ChatSession.user_id == current_user.id
    ).order_by(
        # Handle NULL values - use created_at as fallback if updated_at is NULL
        func.coalesce(ChatSession.updated_at, ChatSession.created_at).desc(),
        ChatSession.created_at.desc()
    ).all()
    
    return sessions


@router.get(
    "/sessions/{session_id}/messages",
    response_model=list[ChatMessageHistory],
    summary="Get session history"
)
def get_session_history(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get all messages for a specific session belonging to the user."""
    session = db.query(ChatSession).filter(
        ChatSession.id == session_id,
        ChatSession.user_id == current_user.id
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    messages = db.query(ChatMessage).filter(
        ChatMessage.session_id == session_id
    ).order_by(ChatMessage.created_at).all()
    
    return messages


@router.delete(
    "/sessions/{session_id}",
    summary="Delete session"
)
def delete_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete a chat session and its history if it belongs to the user."""
    session = db.query(ChatSession).filter(
        ChatSession.id == session_id,
        ChatSession.user_id == current_user.id
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    db.delete(session)
    db.commit()
    return {"status": "success", "message": "Session deleted"}
