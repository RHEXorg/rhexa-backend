# app/schemas/auth.py
"""
Authentication schemas for RheXa.
"""

from pydantic import BaseModel


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    sub: str | None = None


class PasswordResetRequest(BaseModel):
    email: str


class PasswordResetVerify(BaseModel):
    email: str
    code: str


class PasswordResetSet(BaseModel):
    email: str
    code: str
    new_password: str


class PasswordChange(BaseModel):
    old_password: str
    new_password: str
