# db_models/user.py
"""
User model with role-based access control for Fixed Asset Verification.

Roles:
- ADMIN: Full system access, can manage cycles, users, and all assets
- AUDITOR: Can verify any asset, override verifications, view all data
- OWNER: Can self-verify owned assets only
- VIEWER: Read-only access to assets and verifications
"""
from datetime import datetime
from enum import Enum

from sqlalchemy import String, Boolean, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from db_base import Base


class UserRole(str, Enum):
    """User roles for authorization."""
    ADMIN = "ADMIN"
    AUDITOR = "AUDITOR"
    OWNER = "OWNER"
    VIEWER = "VIEWER"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    # Login credentials
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )
    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    # Profile
    full_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    # Role-based access control
    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=UserRole.VIEWER.value,
    )

    # Account status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    # Force password change on first login (for auto-created users)
    must_change_password: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        onupdate=func.now(),
    )
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    def is_admin(self) -> bool:
        return self.role == UserRole.ADMIN.value

    def is_auditor(self) -> bool:
        return self.role == UserRole.AUDITOR.value

    def is_owner(self) -> bool:
        return self.role == UserRole.OWNER.value

    def can_verify_any_asset(self) -> bool:
        """ADMIN and AUDITOR can verify any asset."""
        return self.role in (UserRole.ADMIN.value, UserRole.AUDITOR.value)

    def can_override_verification(self) -> bool:
        """Only ADMIN and AUDITOR can override verifications."""
        return self.role in (UserRole.ADMIN.value, UserRole.AUDITOR.value)

    def can_manage_cycles(self) -> bool:
        """Only ADMIN can create/lock/unlock cycles."""
        return self.role == UserRole.ADMIN.value

    def can_manage_users(self) -> bool:
        """Only ADMIN can manage users."""
        return self.role == UserRole.ADMIN.value
