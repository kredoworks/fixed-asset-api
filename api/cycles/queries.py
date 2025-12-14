# api/cycles/queries.py
"""
SQLAlchemy query builders for verification cycle operations.
"""
from sqlalchemy import select, func

from db_models.verification_cycle import VerificationCycle
from db_models.asset_verification import AssetVerification


def select_cycle_by_id(cycle_id: int):
    """Select a cycle by its ID."""
    return select(VerificationCycle).where(VerificationCycle.id == cycle_id)


def select_cycle_by_tag(tag: str):
    """Select a cycle by its tag."""
    return select(VerificationCycle).where(VerificationCycle.tag == tag)


def select_all_cycles():
    """Select all cycles ordered by creation time (newest first)."""
    return select(VerificationCycle).order_by(VerificationCycle.created_at.desc())


def select_active_cycle():
    """Select the most recent ACTIVE cycle."""
    return (
        select(VerificationCycle)
        .where(VerificationCycle.status == "ACTIVE")
        .order_by(VerificationCycle.created_at.desc())
        .limit(1)
    )


def count_verifications_for_cycle(cycle_id: int):
    """Count verifications for a cycle."""
    return (
        select(func.count(AssetVerification.id))
        .where(AssetVerification.cycle_id == cycle_id)
    )
