# api/auth/models.py
"""
Pydantic models for authentication endpoints.
"""
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, ConfigDict


class Token(BaseModel):
    """JWT token response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenRefresh(BaseModel):
    """Request to refresh access token."""
    refresh_token: str


class LoginRequest(BaseModel):
    """Login credentials."""
    email: EmailStr
    password: str


class UserCreate(BaseModel):
    """Request to create a new user."""
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: str = Field(..., min_length=1, max_length=255)
    role: str = Field(default="VIEWER", pattern="^(ADMIN|AUDITOR|OWNER|VIEWER)$")


class UserUpdate(BaseModel):
    """Request to update user profile."""
    email: EmailStr | None = None
    full_name: str | None = Field(None, min_length=1, max_length=255)
    role: str | None = Field(None, pattern="^(ADMIN|AUDITOR|OWNER|VIEWER)$")
    is_active: bool | None = None


class PasswordChange(BaseModel):
    """Request to change password."""
    current_password: str
    new_password: str = Field(..., min_length=8)


class PasswordReset(BaseModel):
    """Admin password reset (no current password required)."""
    new_password: str = Field(..., min_length=8)


class UserResponse(BaseModel):
    """User data response."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    full_name: str
    role: str
    is_active: bool
    must_change_password: bool
    created_at: datetime
    last_login_at: datetime | None = None


class UserListResponse(BaseModel):
    """List of users response."""
    users: list[UserResponse]
    total: int
