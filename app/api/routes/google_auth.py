# app/api/routes/google_auth.py
"""
Google OAuth routes for RheXa.

Handles:
- Redirect to Google login
- Callback from Google with auth code
- Auto-create or login user
"""

from datetime import timedelta
from typing import Any
import httpx
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.api import deps
from app.core import security
from app.core.config import settings
from app.models.user import User
from app.models.organization import Organization

router = APIRouter(prefix="/auth/google", tags=["auth"])

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"


@router.get("/login")
def google_login():
    """
    Redirect user to Google OAuth consent screen.
    """
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=500, detail="Google OAuth not configured")
    
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "consent",
    }
    
    auth_url = f"{GOOGLE_AUTH_URL}?{urlencode(params)}"
    return RedirectResponse(url=auth_url)


@router.get("/callback")
async def google_callback(
    code: str = None,
    error: str = None,
    db: Session = Depends(deps.get_db)
) -> Any:
    """
    Handle OAuth callback from Google.
    Exchange code for tokens, get user info, create/login user.
    """
    if error:
        return RedirectResponse(url=f"{settings.FRONTEND_URL}/login?error={error}")
    
    if not code:
        return RedirectResponse(url=f"{settings.FRONTEND_URL}/login?error=no_code")
    
    try:
        # Exchange code for tokens
        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": settings.GOOGLE_REDIRECT_URI,
                },
            )
            
            if token_response.status_code != 200:
                print(f"Token error: {token_response.text}")
                return RedirectResponse(url=f"{settings.FRONTEND_URL}/login?error=token_error")
            
            tokens = token_response.json()
            access_token = tokens.get("access_token")
            
            # Get user info from Google
            userinfo_response = await client.get(
                GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"}
            )
            
            if userinfo_response.status_code != 200:
                return RedirectResponse(url=f"{settings.FRONTEND_URL}/login?error=userinfo_error")
            
            google_user = userinfo_response.json()
        
        email = google_user.get("email")
        first_name = google_user.get("given_name", "")
        last_name = google_user.get("family_name", "")
        
        if not email:
            return RedirectResponse(url=f"{settings.FRONTEND_URL}/login?error=no_email")
        
        # Check if user exists
        user = db.query(User).filter(User.email == email).first()
        
        if not user:
            # Create new user (auto-verified since it's from Google)
            new_org = Organization(name=f"{email.split('@')[0]}'s Organization")
            db.add(new_org)
            db.commit()
            db.refresh(new_org)
            
            user = User(
                email=email,
                hashed_password=security.get_password_hash("google-oauth-no-password"),
                first_name=first_name,
                last_name=last_name,
                organization_id=new_org.id,
                is_active=1,
                is_verified=1,
                auth_provider="google"  # Track provider
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        else:
            # User exists. Check provider mismatch.
            if user.auth_provider != "google":
                # Strict isolation: if provider is local or github, block google login
                error_code = "account_exists_locally" if user.auth_provider == "local" else "account_exists_other_provider"
                return RedirectResponse(
                    url=f"{settings.FRONTEND_URL}/login?error={error_code}"
                )
            
            if not user.is_verified:
                user.is_verified = 1
                db.commit()
        
        # Create JWT token
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        jwt_token = security.create_access_token(
            user.id, expires_delta=access_token_expires
        )
        
        # Redirect to frontend with token
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/auth/callback?token={jwt_token}"
        )
        
    except Exception as e:
        print(f"Google OAuth error: {e}")
        return RedirectResponse(url=f"{settings.FRONTEND_URL}/login?error=server_error")
