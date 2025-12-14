# api/auth/views.py
"""
Authentication and user management endpoints.
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_session
from db_models.user import User, UserRole
from core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    verify_token_type,
)
from core.deps import (
    CurrentUser,
    AdminUser,
    get_current_user_optional,
)
from .models import (
    Token,
    TokenRefresh,
    LoginRequest,
    UserCreate,
    UserUpdate,
    PasswordChange,
    PasswordReset,
    UserResponse,
    UserListResponse,
)


router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/login", response_model=Token, summary="Login and get tokens")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_session),
) -> Token:
    """
    OAuth2 compatible login endpoint.
    Returns access and refresh tokens.
    """
    # Find user by email (username field contains email)
    stmt = select(User).where(User.email == form_data.username)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is disabled",
        )

    # Update last login timestamp
    user.last_login_at = datetime.now(timezone.utc)
    await db.commit()

    # Create tokens
    token_data = {"sub": str(user.id), "role": user.role}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post("/login/json", response_model=Token, summary="Login with JSON body")
async def login_json(
    credentials: LoginRequest,
    db: AsyncSession = Depends(get_session),
) -> Token:
    """
    Alternative login endpoint accepting JSON body.
    Useful for SPAs and mobile apps.
    """
    stmt = select(User).where(User.email == credentials.email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is disabled",
        )

    # Update last login timestamp
    user.last_login_at = datetime.now(timezone.utc)
    await db.commit()

    # Create tokens
    token_data = {"sub": str(user.id), "role": user.role}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post("/refresh", response_model=Token, summary="Refresh access token")
async def refresh_token(
    request: TokenRefresh,
    db: AsyncSession = Depends(get_session),
) -> Token:
    """
    Get a new access token using a refresh token.
    """
    payload = verify_token_type(request.refresh_token, "refresh")
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    # Verify user still exists and is active
    stmt = select(User).where(User.id == int(user_id), User.is_active == True)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    # Create new tokens
    token_data = {"sub": str(user.id), "role": user.role}
    access_token = create_access_token(token_data)
    new_refresh_token = create_refresh_token(token_data)

    return Token(
        access_token=access_token,
        refresh_token=new_refresh_token,
    )


@router.get("/me", response_model=UserResponse, summary="Get current user")
async def get_me(current_user: CurrentUser) -> UserResponse:
    """Get the current authenticated user's profile."""
    return UserResponse.model_validate(current_user)


@router.put("/me", response_model=UserResponse, summary="Update current user profile")
async def update_me(
    updates: UserUpdate,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_session),
) -> UserResponse:
    """
    Update current user's own profile.
    Non-admin users cannot change their own role or active status.
    """
    # Non-admins can only update email and full_name
    if not current_user.is_admin():
        if updates.role is not None or updates.is_active is not None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot change role or active status",
            )

    if updates.email is not None:
        # Check email uniqueness
        stmt = select(User).where(User.email == updates.email, User.id != current_user.id)
        result = await db.execute(stmt)
        if result.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already in use",
            )
        current_user.email = updates.email

    if updates.full_name is not None:
        current_user.full_name = updates.full_name

    if updates.role is not None and current_user.is_admin():
        current_user.role = updates.role

    if updates.is_active is not None and current_user.is_admin():
        current_user.is_active = updates.is_active

    await db.commit()
    await db.refresh(current_user)

    return UserResponse.model_validate(current_user)


@router.post("/me/password", summary="Change password")
async def change_password(
    request: PasswordChange,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_session),
) -> dict:
    """Change the current user's password."""
    if not verify_password(request.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    current_user.hashed_password = get_password_hash(request.new_password)
    current_user.must_change_password = False
    await db.commit()

    return {"message": "Password changed successfully"}


# --- Admin endpoints for user management ---

@router.get("/users", response_model=UserListResponse, summary="List all users (admin)")
async def list_users(
    admin: AdminUser,
    db: AsyncSession = Depends(get_session),
    skip: int = 0,
    limit: int = 100,
) -> UserListResponse:
    """List all users. Admin only."""
    # Get total count
    count_stmt = select(func.count(User.id))
    count_result = await db.execute(count_stmt)
    total = count_result.scalar() or 0

    # Get users
    stmt = select(User).order_by(User.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(stmt)
    users = list(result.scalars().all())

    return UserListResponse(
        users=[UserResponse.model_validate(u) for u in users],
        total=total,
    )


@router.post(
    "/users",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create user (admin)",
)
async def create_user(
    user_data: UserCreate,
    admin: AdminUser,
    db: AsyncSession = Depends(get_session),
) -> UserResponse:
    """Create a new user. Admin only."""
    # Check email uniqueness
    stmt = select(User).where(User.email == user_data.email)
    result = await db.execute(stmt)
    if result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    # Validate role
    if user_data.role not in [r.value for r in UserRole]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role. Must be one of: {[r.value for r in UserRole]}",
        )

    user = User(
        email=user_data.email,
        hashed_password=get_password_hash(user_data.password),
        full_name=user_data.full_name,
        role=user_data.role,
        is_active=True,
        must_change_password=False,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    return UserResponse.model_validate(user)


@router.get("/users/{user_id}", response_model=UserResponse, summary="Get user by ID (admin)")
async def get_user(
    user_id: int,
    admin: AdminUser,
    db: AsyncSession = Depends(get_session),
) -> UserResponse:
    """Get a specific user by ID. Admin only."""
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return UserResponse.model_validate(user)


@router.put("/users/{user_id}", response_model=UserResponse, summary="Update user (admin)")
async def update_user(
    user_id: int,
    updates: UserUpdate,
    admin: AdminUser,
    db: AsyncSession = Depends(get_session),
) -> UserResponse:
    """Update a user. Admin only."""
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if updates.email is not None:
        # Check email uniqueness
        stmt = select(User).where(User.email == updates.email, User.id != user_id)
        result = await db.execute(stmt)
        if result.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already in use",
            )
        user.email = updates.email

    if updates.full_name is not None:
        user.full_name = updates.full_name

    if updates.role is not None:
        if updates.role not in [r.value for r in UserRole]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid role. Must be one of: {[r.value for r in UserRole]}",
            )
        user.role = updates.role

    if updates.is_active is not None:
        user.is_active = updates.is_active

    await db.commit()
    await db.refresh(user)

    return UserResponse.model_validate(user)


@router.post("/users/{user_id}/reset-password", summary="Reset user password (admin)")
async def reset_user_password(
    user_id: int,
    request: PasswordReset,
    admin: AdminUser,
    db: AsyncSession = Depends(get_session),
) -> dict:
    """Reset a user's password. Admin only."""
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    user.hashed_password = get_password_hash(request.new_password)
    user.must_change_password = True  # Force password change on next login
    await db.commit()

    return {"message": "Password reset successfully"}


@router.delete("/users/{user_id}", summary="Deactivate user (admin)")
async def deactivate_user(
    user_id: int,
    admin: AdminUser,
    db: AsyncSession = Depends(get_session),
) -> dict:
    """
    Deactivate a user (soft delete). Admin only.
    Users are never hard-deleted to preserve audit trails.
    """
    if user_id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate yourself",
        )

    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    user.is_active = False
    await db.commit()

    return {"message": "User deactivated successfully"}
