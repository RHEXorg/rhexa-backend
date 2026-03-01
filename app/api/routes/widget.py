# app/api/routes/widget.py
from fastapi import APIRouter, Depends, HTTPException, Header, status
from sqlalchemy.orm import Session
from typing import Optional, List
from app.api.deps import get_current_active_user, get_db
from app.models.widget_config import WidgetConfig
from app.models.user import User
from app.services.rag_service import generate_answer
from app.services.billing_service import check_limit
from pydantic import BaseModel, field_validator
import uuid
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/widget", tags=["Widget"])

# --- Schemas ---

class PublicChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    document_ids: Optional[List[int]] = None
    database_ids: Optional[List[int]] = None

class WidgetConfigCreate(BaseModel):
    name: str = "New Widget"

class WidgetConfigUpdate(BaseModel):
    name: Optional[str] = None
    is_enabled: Optional[bool] = None
    theme_color: Optional[str] = None
    bubble_icon: Optional[str] = None
    welcome_message: Optional[str] = None
    bot_name: Optional[str] = None
    position: Optional[str] = None
    show_branding: Optional[bool] = None
    default_theme: Optional[str] = None
    logo_url: Optional[str] = None
    allowed_domains: Optional[List[str]] = None
    selected_sources: Optional[dict] = None

class WidgetConfigResponse(BaseModel):
    id: int
    name: Optional[str] = "Default Widget"
    widget_key: str
    is_enabled: Optional[bool] = True
    theme_color: Optional[str] = "#991b1b"
    bubble_icon: Optional[str] = "MessageSquare"
    welcome_message: Optional[str] = "Hi! How can I help you today?"
    bot_name: Optional[str] = "RheXa AI"
    position: Optional[str] = "bottom-right"
    show_branding: Optional[bool] = True
    default_theme: Optional[str] = "light"
    logo_url: Optional[str] = None
    selected_sources: Optional[dict] = {"documents": [], "databases": []}
    
    @field_validator('name', 'theme_color', 'welcome_message', 'bot_name', 'position', mode='before')
    @classmethod
    def prevent_nulls(cls, v, info):
        if v is None:
            defaults = {
                'name': "Default Widget",
                'theme_color': "#991b1b",
                'welcome_message': "Hi! How can I help you today?",
                'bot_name': "RheXa AI",
                'position': "bottom-right"
            }
            return defaults.get(info.field_name, v)
        return v

    @field_validator('is_enabled', 'show_branding', mode='before')
    @classmethod
    def prevent_null_bools(cls, v):
        if v is None:
            return True
        return v
    
    class Config:
        from_attributes = True

# --- Public Endpoints ---

@router.get("/config/{widget_key}", response_model=WidgetConfigResponse)
def get_public_widget_config(widget_key: str, db: Session = Depends(get_db)):
    config = db.query(WidgetConfig).filter(WidgetConfig.widget_key == widget_key).first()
    if not config:
        raise HTTPException(status_code=404, detail="Invalid widget key")
    if not config.is_enabled:
        raise HTTPException(status_code=403, detail="Widget is disabled")
    return config

@router.post("/chat")
def public_widget_chat(
    request: PublicChatRequest,
    x_widget_key: str = Header(...),
    db: Session = Depends(get_db)
):
    config = db.query(WidgetConfig).filter(WidgetConfig.widget_key == x_widget_key).first()
    if not config or not config.is_enabled:
        raise HTTPException(status_code=401, detail="Invalid or disabled widget key")
    
    try:
        session_uuid = request.session_id or str(uuid.uuid4())
        
        # Enforce widget config selected sources if they exist
        allowed_docs = None
        allowed_dbs = None
        if config.selected_sources:
            allowed_docs = config.selected_sources.get("documents", [])
            allowed_dbs = config.selected_sources.get("databases", [])
            
            # If the user's request is even more restrictive, intersect them
            if request.document_ids is not None:
                allowed_docs = list(set(allowed_docs) & set(request.document_ids)) if allowed_docs else request.document_ids
            if request.database_ids is not None:
                allowed_dbs = list(set(allowed_dbs) & set(request.database_ids)) if allowed_dbs else request.database_ids
        else:
            allowed_docs = request.document_ids
            allowed_dbs = request.database_ids

        rag_response = generate_answer(
            organization_id=config.organization_id,
            query=request.message,
            document_ids=allowed_docs,
            database_ids=allowed_dbs
        )
        return {
            "answer": rag_response["answer"],
            "session_id": session_uuid,
            "citations": rag_response["citations"]
        }
    except Exception as e:
        logger.exception(f"Public chat error: {e}")
        return {
            "answer": "I am sorry, but I encountered an error while processing your request. Please try again later.",
            "session_id": request.session_id or str(uuid.uuid4()),
            "citations": []
        }

# --- Management Endpoints ---

@router.get("/list", response_model=List[WidgetConfigResponse])
def list_widgets(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    return db.query(WidgetConfig).filter(WidgetConfig.organization_id == current_user.organization_id).all()

@router.post("/create", response_model=WidgetConfigResponse)
def create_widget(
    obj_in: WidgetConfigCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    check_limit(db, current_user.organization_id, "widgets")
    
    config = WidgetConfig(
        organization_id=current_user.organization_id,
        name=obj_in.name
    )
    db.add(config)
    db.commit()
    db.refresh(config)
    return config

@router.patch("/{widget_id}", response_model=WidgetConfigResponse)
def update_widget(
    widget_id: int,
    obj_in: WidgetConfigUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    config = db.query(WidgetConfig).filter(
        WidgetConfig.id == widget_id, 
        WidgetConfig.organization_id == current_user.organization_id
    ).first()
    if not config:
        raise HTTPException(status_code=404, detail="Widget not found")
    
    update_data = obj_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(config, field, value)
        
    db.commit()
    db.refresh(config)
    return config

@router.delete("/{widget_id}")
def delete_widget(
    widget_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    config = db.query(WidgetConfig).filter(
        WidgetConfig.id == widget_id, 
        WidgetConfig.organization_id == current_user.organization_id
    ).first()
    if not config:
        raise HTTPException(status_code=404, detail="Widget not found")
    
    db.delete(config)
    db.commit()
    return {"status": "success"}

@router.post("/{widget_id}/rotate-key", response_model=WidgetConfigResponse)
def rotate_widget_key(
    widget_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    config = db.query(WidgetConfig).filter(
        WidgetConfig.id == widget_id, 
        WidgetConfig.organization_id == current_user.organization_id
    ).first()
    if not config:
        raise HTTPException(status_code=404, detail="Widget not found")
        
    config.widget_key = str(uuid.uuid4())
    db.commit()
    db.refresh(config)
    return config
