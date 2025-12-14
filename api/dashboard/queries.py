# api/dashboard/queries.py
"""
SQLAlchemy query builders for dashboard statistics.
"""
from sqlalchemy import select, func, case, and_

from db_models.asset import Asset
from db_models.verification_cycle import VerificationCycle
from db_models.asset_verification import AssetVerification


def count_total_assets():
    """Count total assets."""
    return select(func.count(Asset.id))


def count_active_assets():
    """Count active assets."""
    return select(func.count(Asset.id)).where(Asset.is_active == True)


def count_inactive_assets():
    """Count inactive assets."""
    return select(func.count(Asset.id)).where(Asset.is_active == False)


def count_total_cycles():
    """Count total verification cycles."""
    return select(func.count(VerificationCycle.id))


def select_recent_cycles(limit: int = 5):
    """Select recent cycles ordered by creation date."""
    return (
        select(VerificationCycle)
        .order_by(VerificationCycle.created_at.desc())
        .limit(limit)
    )


def count_verifications_for_cycle(cycle_id: int):
    """Count total verifications for a cycle."""
    return (
        select(func.count(AssetVerification.id))
        .where(AssetVerification.cycle_id == cycle_id)
    )


def count_verified_assets_in_cycle(cycle_id: int):
    """Count distinct assets that have been verified in a cycle."""
    return (
        select(func.count(func.distinct(AssetVerification.asset_id)))
        .where(AssetVerification.cycle_id == cycle_id)
    )


def count_verifications_by_status(cycle_id: int):
    """
    Count verifications by status for a cycle.
    Returns counts for VERIFIED, DISCREPANCY, NOT_FOUND, NEW_ASSET.
    """
    return (
        select(
            func.sum(case((AssetVerification.status == "VERIFIED", 1), else_=0)).label("verified"),
            func.sum(case((AssetVerification.status == "DISCREPANCY", 1), else_=0)).label("discrepancy"),
            func.sum(case((AssetVerification.status == "NOT_FOUND", 1), else_=0)).label("not_found"),
            func.sum(case((AssetVerification.status == "NEW_ASSET", 1), else_=0)).label("new_asset"),
        )
        .where(AssetVerification.cycle_id == cycle_id)
    )


def count_verifications_by_condition(cycle_id: int):
    """
    Count verifications by condition for a cycle.
    Returns counts for GOOD, DAMAGED, NEEDS_REPAIR, and null/not specified.
    """
    return (
        select(
            func.sum(case((AssetVerification.condition == "GOOD", 1), else_=0)).label("good"),
            func.sum(case((AssetVerification.condition == "DAMAGED", 1), else_=0)).label("damaged"),
            func.sum(case((AssetVerification.condition == "NEEDS_REPAIR", 1), else_=0)).label("needs_repair"),
            func.sum(case((AssetVerification.condition.is_(None), 1), else_=0)).label("not_specified"),
        )
        .where(AssetVerification.cycle_id == cycle_id)
    )


def count_verifications_by_source(cycle_id: int):
    """
    Count verifications by source for a cycle.
    Returns counts for SELF, AUDITOR, OVERRIDDEN.
    """
    return (
        select(
            func.sum(case((AssetVerification.source == "SELF", 1), else_=0)).label("self_verified"),
            func.sum(case((AssetVerification.source == "AUDITOR", 1), else_=0)).label("auditor_verified"),
            func.sum(case((AssetVerification.source == "OVERRIDDEN", 1), else_=0)).label("overridden"),
        )
        .where(AssetVerification.cycle_id == cycle_id)
    )


def select_unverified_assets_in_cycle(cycle_id: int):
    """
    Select active assets that have NOT been verified in the given cycle.
    Uses a NOT EXISTS subquery for efficiency.
    """
    subquery = (
        select(AssetVerification.asset_id)
        .where(AssetVerification.cycle_id == cycle_id)
    )
    return (
        select(Asset)
        .where(
            Asset.is_active == True,
            ~Asset.id.in_(subquery)
        )
        .order_by(Asset.asset_code.asc())
    )


def count_unverified_assets_in_cycle(cycle_id: int):
    """Count active assets not yet verified in a cycle."""
    subquery = (
        select(AssetVerification.asset_id)
        .where(AssetVerification.cycle_id == cycle_id)
    )
    return (
        select(func.count(Asset.id))
        .where(
            Asset.is_active == True,
            ~Asset.id.in_(subquery)
        )
    )
