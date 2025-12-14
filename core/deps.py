# core/deps.py
"""
FastAPI dependencies for authentication and authorization.
"""
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_session
from db_models.user import User, UserRole
from core.security import decode_token

# OAuth2 scheme for token extraction from Authorization header
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


class AuthenticationError(HTTPException):
    """Raised when authentication fails."""
    def __init__(self, detail: str = "Could not validate credentials"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


class AuthorizationError(HTTPException):
    """Raised when user lacks required permissions."""
    def __init__(self, detail: str = "Not enough permissions"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
        )


async def get_current_user(
    token: Annotated[str | None, Depends(oauth2_scheme)],
    db: AsyncSession = Depends(get_session),
) -> User:
    """
    Dependency to get the current authenticated user from JWT token.

    Raises:
        AuthenticationError: If token is missing, invalid, or user not found
    """
    if token is None:
        raise AuthenticationError("Not authenticated")

    payload = decode_token(token)
    if payload is None:
        raise AuthenticationError("Invalid or expired token")

    # Check token type
    if payload.get("type") != "access":
        raise AuthenticationError("Invalid token type")

    user_id = payload.get("sub")
    if user_id is None:
        raise AuthenticationError("Invalid token payload")

    # Get user from database
    try:
        user_id = int(user_id)
    except (ValueError, TypeError):
        raise AuthenticationError("Invalid user ID in token")

    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None:
        raise AuthenticationError("User not found")

    if not user.is_active:
        raise AuthenticationError("User account is disabled")

    return user


async def get_current_user_optional(
    token: Annotated[str | None, Depends(oauth2_scheme)],
    db: AsyncSession = Depends(get_session),
) -> User | None:
    """
    Dependency to optionally get current user. Returns None if not authenticated.
    Useful for endpoints that work with or without authentication.
    """
    if token is None:
        return None

    payload = decode_token(token)
    if payload is None:
        return None

    if payload.get("type") != "access":
        return None

    user_id = payload.get("sub")
    if user_id is None:
        return None

    try:
        user_id = int(user_id)
    except (ValueError, TypeError):
        return None

    stmt = select(User).where(User.id == user_id, User.is_active == True)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Dependency to ensure user is active."""
    if not current_user.is_active:
        raise AuthorizationError("Inactive user")
    return current_user


# Role-based access dependencies

async def require_admin(
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> User:
    """Dependency that requires ADMIN role."""
    if not current_user.is_admin():
        raise AuthorizationError("Admin access required")
    return current_user


async def require_auditor_or_admin(
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> User:
    """Dependency that requires AUDITOR or ADMIN role."""
    if current_user.role not in (UserRole.ADMIN.value, UserRole.AUDITOR.value):
        raise AuthorizationError("Auditor or admin access required")
    return current_user


async def require_can_verify(
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> User:
    """Dependency that requires ability to verify assets (ADMIN, AUDITOR, or OWNER)."""
    if current_user.role not in (UserRole.ADMIN.value, UserRole.AUDITOR.value, UserRole.OWNER.value):
        raise AuthorizationError("Verification access required")
    return current_user


# Type aliases for cleaner endpoint signatures
CurrentUser = Annotated[User, Depends(get_current_active_user)]
CurrentUserOptional = Annotated[User | None, Depends(get_current_user_optional)]
AdminUser = Annotated[User, Depends(require_admin)]
AuditorOrAdmin = Annotated[User, Depends(require_auditor_or_admin)]
CanVerify = Annotated[User, Depends(require_can_verify)]
