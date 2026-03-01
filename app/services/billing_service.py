# app/services/billing_service.py
from datetime import datetime, timezone, timedelta
from app.models.organization import Organization
from app.models.widget_config import WidgetConfig
from app.models.document import Document
from app.models.database_connection import DatabaseConnection
from sqlalchemy.orm import Session
from fastapi import HTTPException

# Define limits
PLAN_LIMITS = {
    "free_trial": {
        "widgets": 1,
        "files": 1,
        "databases": 0,
        "trial_days": 2
    },
    "pro": {
        "widgets": 6,
        "files": 10,
        "databases": 2,
    },
    "enterprise": {
        "widgets": float('inf'),
        "files": float('inf'),
        "databases": float('inf'),
    }
}

def get_org_usage(db: Session, org_id: int):
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
        
    widgets_count = db.query(WidgetConfig).filter(WidgetConfig.organization_id == org_id).count()
    files_count = db.query(Document).filter(Document.organization_id == org_id).count()
    dbs_count = db.query(DatabaseConnection).filter(DatabaseConnection.organization_id == org_id).count()
    
    tier = org.subscription_tier or "free_trial"
    limits = PLAN_LIMITS.get(tier, PLAN_LIMITS["free_trial"])
    
    # Check trial expiry if on free trial
    is_expired = False
    if tier == "free_trial":
        if org.trial_ends_at and datetime.now(timezone.utc) > org.trial_ends_at:
            is_expired = True
            
    return {
        "tier": tier,
        "limits": limits,
        "usage": {
            "widgets": widgets_count,
            "files": files_count,
            "databases": dbs_count
        },
        "is_expired": is_expired,
        "trial_ends_at": org.trial_ends_at.isoformat() if org.trial_ends_at else None
    }

def check_limit(db: Session, org_id: int, resource_type: str):
    usage_info = get_org_usage(db, org_id)
    if usage_info["is_expired"]:
        raise HTTPException(status_code=403, detail="Your free trial has expired. Please upgrade to continue.")
        
    current = usage_info["usage"].get(resource_type, 0)
    limit = usage_info["limits"].get(resource_type, 0)
    
    if current >= limit:
        raise HTTPException(status_code=403, detail=f"Upgrade required: Plan limit reached for {resource_type} ({limit} max).")
