# api/cycles/db_manager.py
"""
Business logic for verification cycle management.
"""
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from db_models.verification_cycle import VerificationCycle
from . import queries


class CycleNotFoundError(Exception):
    """Raised when cycle doesn't exist."""
    pass


class CycleStatusError(Exception):
    """Raised when cycle status transition is invalid."""
    pass


class DuplicateTagError(Exception):
    """Raised when cycle tag already exists."""
    pass


async def get_cycle_by_id(db: AsyncSession, cycle_id: int) -> VerificationCycle:
    """Get a cycle by ID. Raises CycleNotFoundError if not found."""
    stmt = queries.select_cycle_by_id(cycle_id)
    result = await db.execute(stmt)
    cycle = result.scalar_one_or_none()
    if cycle is None:
        raise CycleNotFoundError(f"Cycle {cycle_id} not found")
    return cycle


async def create_cycle(
    db: AsyncSession,
    tag: str,
    status: str = "ACTIVE"
) -> VerificationCycle:
    """
    Create a new verification cycle with the given tag.

    Args:
        db: Database session
        tag: Unique tag for the cycle (e.g., "Q2 2025")
        status: Initial status (DRAFT or ACTIVE, default ACTIVE)

    Raises:
        DuplicateTagError: If tag already exists
        ValueError: If status is invalid
    """
    # Validate status
    if status not in ("DRAFT", "ACTIVE"):
        raise ValueError(f"Invalid initial status: {status}. Must be DRAFT or ACTIVE")

    # Check if tag already exists
    stmt = queries.select_cycle_by_tag(tag)
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()
    if existing is not None:
        raise DuplicateTagError(f"Cycle with tag '{tag}' already exists")

    cycle = VerificationCycle(tag=tag, status=status)
    db.add(cycle)
    await db.commit()
    await db.refresh(cycle)
    return cycle


async def list_cycles(db: AsyncSession) -> list[VerificationCycle]:
    """Return all cycles ordered by created_at desc."""
    stmt = queries.select_all_cycles()
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_active_cycle(db: AsyncSession) -> VerificationCycle | None:
    """Get the most recent ACTIVE cycle, or None if none exists."""
    stmt = queries.select_active_cycle()
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def activate_cycle(db: AsyncSession, cycle_id: int) -> VerificationCycle:
    """
    Activate a DRAFT cycle.

    Raises:
        CycleNotFoundError: If cycle doesn't exist
        CycleStatusError: If cycle is not in DRAFT status
    """
    cycle = await get_cycle_by_id(db, cycle_id)

    if cycle.status != "DRAFT":
        raise CycleStatusError(
            f"Cannot activate cycle {cycle_id}: current status is {cycle.status}. "
            "Only DRAFT cycles can be activated."
        )

    cycle.status = "ACTIVE"
    await db.commit()
    await db.refresh(cycle)
    return cycle


async def lock_cycle(db: AsyncSession, cycle_id: int) -> VerificationCycle:
    """
    Lock an ACTIVE cycle. Prevents further verifications.

    Raises:
        CycleNotFoundError: If cycle doesn't exist
        CycleStatusError: If cycle is not in ACTIVE status
    """
    cycle = await get_cycle_by_id(db, cycle_id)

    if cycle.status != "ACTIVE":
        raise CycleStatusError(
            f"Cannot lock cycle {cycle_id}: current status is {cycle.status}. "
            "Only ACTIVE cycles can be locked."
        )

    cycle.status = "LOCKED"
    cycle.locked_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(cycle)
    return cycle


async def unlock_cycle(db: AsyncSession, cycle_id: int) -> VerificationCycle:
    """
    Unlock a LOCKED cycle. Allows further verifications.

    Raises:
        CycleNotFoundError: If cycle doesn't exist
        CycleStatusError: If cycle is not in LOCKED status
    """
    cycle = await get_cycle_by_id(db, cycle_id)

    if cycle.status != "LOCKED":
        raise CycleStatusError(
            f"Cannot unlock cycle {cycle_id}: current status is {cycle.status}. "
            "Only LOCKED cycles can be unlocked."
        )

    cycle.status = "ACTIVE"
    cycle.locked_at = None
    await db.commit()
    await db.refresh(cycle)
    return cycle


async def get_cycle_stats(db: AsyncSession, cycle_id: int) -> dict:
    """
    Get verification statistics for a cycle.

    Returns dict with counts for verified, pending, discrepancy, etc.
    """
    cycle = await get_cycle_by_id(db, cycle_id)

    # Count verifications
    stmt = queries.count_verifications_for_cycle(cycle_id)
    result = await db.execute(stmt)
    total_verifications = result.scalar() or 0

    return {
        "cycle_id": cycle.id,
        "tag": cycle.tag,
        "status": cycle.status,
        "total_verifications": total_verifications,
    }
