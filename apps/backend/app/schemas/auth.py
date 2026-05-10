"""Authentication request/response schemas."""

from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field

from app.models.user import UserRole


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class UserPublic(BaseModel):
    id: str
    email: EmailStr
    full_name: str | None = None
    role: UserRole
    is_active: bool


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = None
    role: UserRole = UserRole.VIEWER


class UserProfileUpdate(BaseModel):
    """User-self profile patch. Email and role are immutable from this endpoint."""

    full_name: str | None = Field(default=None, max_length=255)


class PasswordChangeRequest(BaseModel):
    current_password: str = Field(min_length=8, max_length=128, repr=False)
    new_password: str = Field(min_length=8, max_length=128, repr=False)
