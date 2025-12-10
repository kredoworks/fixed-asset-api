# db_models/verification_cycle.py
from datetime import datetime

from sqlalchemy import String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db_base import Base


class VerificationCycle(Base):
    __tablename__ = "verification_cycles"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    tag: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        index=True,
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="ACTIVE",
        server_default="ACTIVE",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    locked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # NEW: backref to verifications
    verifications: Mapped[list["AssetVerification"]] = relationship(
        "AssetVerification",
        back_populates="cycle",
        cascade="all, delete-orphan",
    )
