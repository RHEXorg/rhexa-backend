# app/api/routes/github_auth.py
"""
GitHub OAuth routes for RheXa.

Handles:
- Redirect to GitHub login
- Callback from GitHub with auth code
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

router = APIRouter(prefix="/auth/github", tags=["auth"])

GITHUB_AUTH_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_USERINFO_URL = "https://api.github.com/user"
GITHUB_EMAILS_URL = "https://api.github.com/user/emails"


@router.get("/login")
def github_login():
    """
    Redirect user to GitHub OAuth consent screen.
    """
    if not settings.GITHUB_CLIENT_ID:
        raise HTTPException(status_code=500, detail="GitHub OAuth not configured")
    
    params = {
        "client_id": settings.GITHUB_CLIENT_ID,
        "redirect_uri": settings.GITHUB_REDIRECT_URI,
        "scope": "user:email",
    }
    
    auth_url = f"{GITHUB_AUTH_URL}?{urlencode(params)}"
    return RedirectResponse(url=auth_url)


@router.get("/callback")
async def github_callback(
    code: str = None,
    error: str = None,
    db: Session = Depends(deps.get_db)
) -> Any:
    """
    Handle OAuth callback from GitHub.
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
                GITHUB_TOKEN_URL,
                headers={"Accept": "application/json"},
                data={
                    "client_id": settings.GITHUB_CLIENT_ID,
                    "client_secret": settings.GITHUB_CLIENT_SECRET,
                    "code": code,
                    "redirect_uri": settings.GITHUB_REDIRECT_URI,
                },
            )
            
            if token_response.status_code != 200:
                return RedirectResponse(url=f"{settings.FRONTEND_URL}/login?error=token_error")
            
            tokens = token_response.json()
            access_token = tokens.get("access_token")
            
            if not access_token:
                 return RedirectResponse(url=f"{settings.FRONTEND_URL}/login?error=no_access_token")

            # Get user info from GitHub
            userinfo_response = await client.get(
                GITHUB_USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"}
            )
            
            if userinfo_response.status_code != 200:
                return RedirectResponse(url=f"{settings.FRONTEND_URL}/login?error=userinfo_error")
            
            github_user = userinfo_response.json()
            
            # Get primary email if not public in profile
            email = github_user.get("email")
            if not email:
                emails_response = await client.get(
                    GITHUB_EMAILS_URL,
                    headers={"Authorization": f"Bearer {access_token}"}
                )
                if emails_response.status_code == 200:
                    emails = emails_response.json()
                    for e in emails:
                        if e.get("primary") and e.get("verified"):
                            email = e.get("email")
                            break
        
        name_parts = (github_user.get("name") or github_user.get("login") or "").split()
        first_name = name_parts[0] if name_parts else ""
        last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""
        
        if not email:
            return RedirectResponse(url=f"{settings.FRONTEND_URL}/login?error=no_email")
        
        # Check if user exists
        user = db.query(User).filter(User.email == email).first()
        
        if not user:
            # Create new user
            new_org = Organization(name=f"{email.split('@')[0]}'s Organization")
            db.add(new_org)
            db.commit()
            db.refresh(new_org)
            
            user = User(
                email=email,
                hashed_password=security.get_password_hash("github-oauth-no-password"),
                first_name=first_name,
                last_name=last_name,
                organization_id=new_org.id,
                is_active=1,
                is_verified=1,
                auth_provider="github"  # Track provider
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        else:
            # User exists. Check provider mismatch.
            if user.auth_provider != "github":
                 # Strict isolation: if provider is local or google, block github login
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
        print(f"GitHub OAuth error: {e}")
        return RedirectResponse(url=f"{settings.FRONTEND_URL}/login?error=server_error")
