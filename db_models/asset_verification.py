# db_models/asset_verification.py
from datetime import datetime

from sqlalchemy import (
    String,
    DateTime,
    Float,
    Text,
    ForeignKey,
    Index,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db_base import Base
from db_models.asset import Asset
from db_models.verification_cycle import VerificationCycle


class AssetVerification(Base):
    __tablename__ = "asset_verifications"
    # Composite index for efficient lookups by asset+cycle (spec requirement)
    __table_args__ = (
        Index("ix_asset_cycle", "asset_id", "cycle_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    # FK to asset and cycle
    asset_id: Mapped[int] = mapped_column(
        ForeignKey("assets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    cycle_id: Mapped[int] = mapped_column(
        ForeignKey("verification_cycles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Who performed the verification (for now, simple string; later can be user_id FK)
    performed_by: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    # Source: SELF / AUDITOR / OVERRIDDEN
    source: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    # Status: VERIFIED / DISCREPANCY / NOT_FOUND / NEW_ASSET
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    # Condition: GOOD / DAMAGED / NEEDS_REPAIR
    condition: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    # Geo location (optional)
    location_lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    location_lng: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Photos: for now, simple JSON-ish string (comma-separated or JSON string)
    # You can later move this to a separate table or JSONB column.
    photos: Mapped[str | None] = mapped_column(Text, nullable=True)

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Override chain: if this record overrides another verification
    override_of_verification_id: Mapped[int | None] = mapped_column(
        ForeignKey("asset_verifications.id", ondelete="SET NULL"),
        nullable=True,
    )
    override_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    asset: Mapped[Asset] = relationship(
        "Asset",
        back_populates="verifications",
    )
    cycle: Mapped[VerificationCycle] = relationship(
        "VerificationCycle",
        back_populates="verifications",
    )

    # Self-referential relationship for overrides (optional, handy later)
    override_of: Mapped["AssetVerification | None"] = relationship(
        "AssetVerification",
        remote_side="AssetVerification.id",
        backref="overridden_by",
    )
