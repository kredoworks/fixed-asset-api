# api/verification/queries.py
"""
SQLAlchemy query builders for verification-related database operations.
"""
from sqlalchemy import select, or_, func

from db_models.asset import Asset
from db_models.verification_cycle import VerificationCycle
from db_models.asset_verification import AssetVerification


def select_cycle_by_id(cycle_id: int):
    """Select a verification cycle by its ID."""
    return select(VerificationCycle).where(VerificationCycle.id == cycle_id)


def select_asset_by_code(asset_code: str):
    """Select an asset by its unique asset_code."""
    return select(Asset).where(Asset.asset_code == asset_code)


def select_asset_by_id(asset_id: int):
    """Select an asset by its ID."""
    return select(Asset).where(Asset.id == asset_id)


def select_verifications_for_asset_cycle(asset_id: int, cycle_id: int):
    """
    Select all verifications for an asset in a cycle.
    Returns newest first (ordered by created_at DESC).
    """
    return (
        select(AssetVerification)
        .where(
            AssetVerification.asset_id == asset_id,
            AssetVerification.cycle_id == cycle_id,
        )
        .order_by(AssetVerification.created_at.desc())
    )


def search_assets_query(text: str, limit: int = 50):
    """
    Search assets by partial match on asset_code or name (case-insensitive).
    Returns up to `limit` results ordered by asset_code.
    """
    pattern = f"%{text.lower()}%"
    return (
        select(Asset)
        .where(
            or_(
                func.lower(Asset.asset_code).like(pattern),
                func.lower(Asset.name).like(pattern),
            )
        )
        .order_by(Asset.asset_code.asc())
        .limit(limit)
    )


def select_active_assets():
    """Select all active assets."""
    return select(Asset).where(Asset.is_active == True).order_by(Asset.asset_code.asc())


def select_active_cycle():
    """Select the most recent ACTIVE cycle."""
    return (
        select(VerificationCycle)
        .where(VerificationCycle.status == "ACTIVE")
        .order_by(VerificationCycle.created_at.desc())
        .limit(1)
    )
