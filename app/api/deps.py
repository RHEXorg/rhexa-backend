# app/api/deps.py
"""
FastAPI dependencies for RheXa API.

This module provides reusable dependencies for:
- Database session management
- Authentication (Phase 1.8)
- Storage backend access
- Request validation

Dependencies follow FastAPI best practices for:
- Resource cleanup (database connections)
- Dependency injection
- Type safety
"""

from typing import Generator, Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from pydantic import ValidationError

from app.db.session import SessionLocal
from app.core.storage import StorageBackend, get_storage
from app.core.config import settings
from app.core import security
from app.models.user import User
from app.schemas.auth import TokenPayload

# OAuth2 configuration
reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.ENV}/auth/login" if settings.ENV != "development" else "/api/auth/login"
)


def get_db() -> Generator[Session, None, None]:
    """Database session dependency."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_storage_backend() -> StorageBackend:
    """Storage backend dependency."""
    return get_storage()


def get_current_user(
    db: Session = Depends(get_db), 
    token: str = Depends(reusable_oauth2)
) -> User:
    """
    Get current authenticated user from JWT token.
    
    Validates token, extracts subject (user ID), and fetches user from DB.
    """
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        token_data = TokenPayload(**payload)
    except (JWTError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )
    
    user = db.query(User).filter(User.id == token_data.sub).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Verify user is active."""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


def require_organization_access(
    organization_id: int = None, 
    current_user: User = Depends(get_current_active_user)
) -> int:
    """
    Verify user has access to a specific organization.
    If no organization_id is provided, use the user's own organization.
    Enforces multi-tenant isolation.
    """
    if organization_id is None:
        return current_user.organization_id

    if current_user.is_superuser:
        return organization_id
        
    if current_user.organization_id != organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this organization's data"
        )
    return organization_id
