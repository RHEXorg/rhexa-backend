from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api import deps
from app.models.organization import Organization
from app.models.user import User
from app.schemas.organization import OrganizationResponse, OrganizationUpdate
from app.schemas.user import UserResponse

router = APIRouter(prefix="/api/organization", tags=["organization"])

@router.get("/settings", response_model=OrganizationResponse)
def get_organization_settings(
    db: Session = Depends(deps.get_db),
    current_org_id: int = Depends(deps.require_organization_access)
) -> Any:
    """
    Get organization details.
    """
    org = db.query(Organization).filter(Organization.id == current_org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    return org

@router.put("/settings", response_model=OrganizationResponse)
def update_organization_settings(
    *,
    db: Session = Depends(deps.get_db),
    org_in: OrganizationUpdate,
    current_org_id: int = Depends(deps.require_organization_access)
) -> Any:
    """
    Update organization name.
    """
    org = db.query(Organization).filter(Organization.id == current_org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    if org_in.name:
        org.name = org_in.name
        
    db.add(org)
    db.commit()
    db.refresh(org)
    return org

@router.get("/members", response_model=List[UserResponse])
def list_organization_members(
    db: Session = Depends(deps.get_db),
    current_org_id: int = Depends(deps.require_organization_access)
) -> Any:
    """
    List all users belonging to this organization.
    """
    members = db.query(User).filter(User.organization_id == current_org_id).all()
    return members
