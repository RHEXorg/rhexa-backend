# app/api/routes/auth.py
"""
Authentication routes for RheXa.

Handles:
- User signup
- Login (getting access token)
- User profile retrieval
"""

import random
import string
from datetime import timedelta
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status, Body, UploadFile, File
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.api import deps
from app.core import security
from app.core.config import settings
from app.core.email import send_verification_email, send_password_reset_email
from app.models.user import User
from app.models.organization import Organization
from app.schemas.auth import Token, PasswordResetRequest, PasswordResetVerify, PasswordResetSet, PasswordChange
from app.schemas.user import UserCreate, UserResponse, UserUpdate

router = APIRouter(prefix="/auth", tags=["auth"])


def generate_verification_code(length=6):
    return ''.join(random.choices(string.digits, k=length))


@router.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def signup(
    *,
    db: Session = Depends(deps.get_db),
    user_in: UserCreate
) -> Any:
    """
    Create a new user and potentially a new organization.
    """
    user = db.query(User).filter(User.email == user_in.email).first()
    if user:
        raise HTTPException(
            status_code=400,
            detail="Account already exists. Please sign in to continue.",
        )
    
    # If no organization_id is provided, create a new organization
    # This is a simple logic for Phase 1.8
    org_id = user_in.organization_id
    if not org_id:
        new_org = Organization(name=f"{user_in.email.split('@')[0]}'s Organization")
        db.add(new_org)
        db.commit()
        db.refresh(new_org)
        org_id = new_org.id
    else:
        # Verify organization exists
        org = db.query(Organization).filter(Organization.id == org_id).first()
        if not org:
            raise HTTPException(status_code=404, detail="Organization not found")

    verification_code = generate_verification_code()
    
    # Send verification email (Real or Simulated based on config)
    send_verification_email(user_in.email, verification_code)

    new_user = User(
        email=user_in.email,
        hashed_password=security.get_password_hash(user_in.password),
        first_name=user_in.first_name,
        last_name=user_in.last_name,
        organization_id=org_id,
        is_active=1,
        is_verified=0, # User must verify email
        verification_code=verification_code
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@router.post("/verify-email")
def verify_email(
    email: str = Body(..., embed=True),
    code: str = Body(..., embed=True),
    db: Session = Depends(deps.get_db)
) -> Any:
    """
    Verify email with the code sent.
    """
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.is_verified == 1:
        return {"msg": "Email already verified"}

    if not user.verification_code or user.verification_code != code:
        raise HTTPException(status_code=400, detail="Invalid verification code")
    
    user.is_verified = 1
    user.verification_code = None
    db.add(user)
    db.commit()
    
    return {"msg": "Email verified successfully"}


@router.post("/login", response_model=Token)
def login_access_token(
    db: Session = Depends(deps.get_db), 
    form_data: OAuth2PasswordRequestForm = Depends()
) -> Any:
    """
    OAuth2 compatible token login, get an access token for future requests.
    """
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not security.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    elif not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    elif not user.is_verified:
        raise HTTPException(status_code=400, detail="Email not verified. Please check your inbox for the code.")
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return {
        "access_token": security.create_access_token(
            user.id, expires_delta=access_token_expires
        ),
        "token_type": "bearer",
    }


@router.get("/me", response_model=UserResponse)
def read_user_me(
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get current user details.
    """
    return current_user


@router.put("/me", response_model=UserResponse)
def update_user_me(
    *,
    db: Session = Depends(deps.get_db),
    user_in: UserUpdate,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Update own user profile.
    """
    if user_in.email:
        existing_user = db.query(User).filter(User.email == user_in.email).first()
        if existing_user and existing_user.id != current_user.id:
            raise HTTPException(status_code=400, detail="Email already registered")
        current_user.email = user_in.email
    
    if user_in.first_name:
        current_user.first_name = user_in.first_name
    if user_in.last_name:
        current_user.last_name = user_in.last_name
    if user_in.avatar_url is not None:
        current_user.avatar_url = user_in.avatar_url
    if user_in.password:
        current_user.hashed_password = security.get_password_hash(user_in.password)
        
    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    return current_user


@router.post("/me/avatar", response_model=UserResponse)
def upload_avatar(
    *,
    db: Session = Depends(deps.get_db),
    file: UploadFile = File(...),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Upload a profile avatar image. Max 500KB, image files only.
    """
    # Validate file type
    allowed_types = ["image/jpeg", "image/png", "image/webp", "image/gif"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail="Only JPEG, PNG, WebP, and GIF images are allowed."
        )
    
    # Read file content
    contents = file.file.read()
    
    # Validate file size (500KB max)
    if len(contents) > 500 * 1024:
        raise HTTPException(
            status_code=400,
            detail="Image must be under 500KB. Please compress it before uploading."
        )
    
    # Create avatars directory
    import os
    import uuid
    avatars_dir = os.path.join(os.getcwd(), "uploads", "avatars")
    os.makedirs(avatars_dir, exist_ok=True)
    
    # Delete old avatar file if exists
    if current_user.avatar_url:
        old_path = os.path.join(os.getcwd(), current_user.avatar_url.lstrip("/"))
        if os.path.exists(old_path):
            try:
                os.remove(old_path)
            except Exception:
                pass
    
    # Generate unique filename
    ext = file.filename.split(".")[-1] if "." in file.filename else "jpg"
    filename = f"{current_user.id}_{uuid.uuid4().hex[:8]}.{ext}"
    filepath = os.path.join(avatars_dir, filename)
    
    # Save file
    with open(filepath, "wb") as f:
        f.write(contents)
    
    # Update user avatar URL
    avatar_url = f"/uploads/avatars/{filename}"
    current_user.avatar_url = avatar_url
    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    
    return current_user


@router.post("/forgot-password")
def forgot_password(
    *,
    db: Session = Depends(deps.get_db),
    email_in: PasswordResetRequest
) -> Any:
    """
    Initiate password reset process.
    """
    user = db.query(User).filter(User.email == email_in.email).first()
    if not user:
        # Don't reveal if user exists for security, but we'll show helpful message for UX
        raise HTTPException(status_code=404, detail="Email not found")
    
    if user.auth_provider != "local":
        raise HTTPException(
            status_code=400, 
            detail=f"This account is linked with {user.auth_provider}. Please sign in using {user.auth_provider}."
        )

    reset_code = generate_verification_code()
    user.verification_code = reset_code
    db.add(user)
    db.commit()
    
    send_password_reset_email(user.email, reset_code)
    
    return {"msg": "Password reset code sent to your email"}


@router.post("/verify-reset-code")
def verify_reset_code(
    *,
    db: Session = Depends(deps.get_db),
    verify_in: PasswordResetVerify
) -> Any:
    """
    Verify the reset code.
    """
    user = db.query(User).filter(User.email == verify_in.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if not user.verification_code or user.verification_code != verify_in.code:
        raise HTTPException(status_code=400, detail="Invalid or expired reset code")
    
    return {"msg": "Code verified successfully"}


@router.post("/reset-password")
def reset_password(
    *,
    db: Session = Depends(deps.get_db),
    reset_in: PasswordResetSet
) -> Any:
    """
    Reset password using the code.
    """
    user = db.query(User).filter(User.email == reset_in.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if not user.verification_code or user.verification_code != reset_in.code:
        raise HTTPException(status_code=400, detail="Invalid or expired reset code")
    
    # Update password and clear code
    user.hashed_password = security.get_password_hash(reset_in.new_password)
    user.verification_code = None
    db.add(user)
    db.commit()
    
    return {"msg": "Password reset successful. You can now login with your new password."}


@router.post("/change-password")
def change_password(
    *,
    db: Session = Depends(deps.get_db),
    pass_in: PasswordChange,
    current_user: User = Depends(deps.get_current_active_user)
) -> Any:
    """
    Change password for a logged in user.
    """
    if current_user.auth_provider != "local":
        raise HTTPException(
            status_code=400, 
            detail=f"This account is linked with {current_user.auth_provider}. Password management is handled by {current_user.auth_provider}."
        )

    if not security.verify_password(pass_in.old_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect old password")
    
    current_user.hashed_password = security.get_password_hash(pass_in.new_password)
    db.add(current_user)
    db.commit()
    
    return {"msg": "Password changed successfully"}
