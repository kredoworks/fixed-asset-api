# api/dashboard/db_manager.py
"""
Business logic for dashboard statistics.
"""
from sqlalchemy.ext.asyncio import AsyncSession

from db_models.verification_cycle import VerificationCycle
from . import queries
from api.cycles import queries as cycle_queries


class CycleNotFoundError(Exception):
    """Raised when cycle doesn't exist."""
    pass


async def get_overview_stats(db: AsyncSession) -> dict:
    """
    Get high-level overview statistics across all cycles.
    """
    # Total assets
    result = await db.execute(queries.count_total_assets())
    total_assets = result.scalar() or 0

    # Active assets
    result = await db.execute(queries.count_active_assets())
    active_assets = result.scalar() or 0

    # Inactive assets
    result = await db.execute(queries.count_inactive_assets())
    inactive_assets = result.scalar() or 0

    # Total cycles
    result = await db.execute(queries.count_total_cycles())
    total_cycles = result.scalar() or 0

    # Active cycle
    result = await db.execute(cycle_queries.select_active_cycle())
    active_cycle = result.scalar_one_or_none()

    # Recent cycles
    result = await db.execute(queries.select_recent_cycles(limit=5))
    recent_cycles = list(result.scalars().all())

    return {
        "total_assets": total_assets,
        "active_assets": active_assets,
        "inactive_assets": inactive_assets,
        "total_cycles": total_cycles,
        "active_cycle": active_cycle,
        "recent_cycles": recent_cycles,
    }


async def get_cycle_summary(db: AsyncSession, cycle: VerificationCycle, total_active_assets: int) -> dict:
    """
    Get summary stats for a single cycle.
    """
    # Count verifications
    result = await db.execute(queries.count_verifications_for_cycle(cycle.id))
    total_verifications = result.scalar() or 0

    # Completion percentage
    completion = (total_verifications / total_active_assets * 100) if total_active_assets > 0 else 0.0

    return {
        "id": cycle.id,
        "tag": cycle.tag,
        "status": cycle.status,
        "created_at": cycle.created_at,
        "locked_at": cycle.locked_at,
        "total_verifications": total_verifications,
        "completion_percentage": round(completion, 2),
    }


async def get_dashboard_summary(db: AsyncSession, cycle_id: int) -> dict:
    """
    Get complete dashboard summary for a specific cycle.
    """
    # Get cycle
    result = await db.execute(cycle_queries.select_cycle_by_id(cycle_id))
    cycle = result.scalar_one_or_none()
    if cycle is None:
        raise CycleNotFoundError(f"Cycle {cycle_id} not found")

    # Total active assets
    result = await db.execute(queries.count_active_assets())
    total_assets = result.scalar() or 0

    # Verified count (distinct assets)
    result = await db.execute(queries.count_verified_assets_in_cycle(cycle_id))
    verified_count = result.scalar() or 0

    # Pending count
    result = await db.execute(queries.count_unverified_assets_in_cycle(cycle_id))
    pending_count = result.scalar() or 0

    # Completion percentage
    completion = (verified_count / total_assets * 100) if total_assets > 0 else 0.0

    # Status breakdown
    result = await db.execute(queries.count_verifications_by_status(cycle_id))
    row = result.one()
    status_breakdown = {
        "verified": row.verified or 0,
        "discrepancy": row.discrepancy or 0,
        "not_found": row.not_found or 0,
        "new_asset": row.new_asset or 0,
    }

    # Condition breakdown
    result = await db.execute(queries.count_verifications_by_condition(cycle_id))
    row = result.one()
    condition_breakdown = {
        "good": row.good or 0,
        "damaged": row.damaged or 0,
        "needs_repair": row.needs_repair or 0,
        "not_specified": row.not_specified or 0,
    }

    # Source breakdown
    result = await db.execute(queries.count_verifications_by_source(cycle_id))
    row = result.one()
    source_breakdown = {
        "self_verified": row.self_verified or 0,
        "auditor_verified": row.auditor_verified or 0,
        "overridden": row.overridden or 0,
    }

    return {
        "cycle_id": cycle.id,
        "cycle_tag": cycle.tag,
        "cycle_status": cycle.status,
        "cycle_created_at": cycle.created_at,
        "cycle_locked_at": cycle.locked_at,
        "total_assets": total_assets,
        "verified_count": verified_count,
        "pending_count": pending_count,
        "completion_percentage": round(completion, 2),
        "status_breakdown": status_breakdown,
        "condition_breakdown": condition_breakdown,
        "source_breakdown": source_breakdown,
    }


async def get_cycle_stats(db: AsyncSession, cycle_id: int) -> dict:
    """
    Get detailed statistics for a specific cycle.
    """
    # Get cycle
    result = await db.execute(cycle_queries.select_cycle_by_id(cycle_id))
    cycle = result.scalar_one_or_none()
    if cycle is None:
        raise CycleNotFoundError(f"Cycle {cycle_id} not found")

    # Total active assets
    result = await db.execute(queries.count_active_assets())
    total_assets = result.scalar() or 0

    # Verified assets count
    result = await db.execute(queries.count_verified_assets_in_cycle(cycle_id))
    verified_count = result.scalar() or 0

    # Pending count
    result = await db.execute(queries.count_unverified_assets_in_cycle(cycle_id))
    pending_count = result.scalar() or 0

    # Source breakdown
    result = await db.execute(queries.count_verifications_by_source(cycle_id))
    row = result.one()
    self_verified = row.self_verified or 0
    auditor_verified = row.auditor_verified or 0
    overridden = row.overridden or 0

    # Status breakdown
    result = await db.execute(queries.count_verifications_by_status(cycle_id))
    row = result.one()
    discrepancy_count = row.discrepancy or 0
    not_found_count = row.not_found or 0
    new_asset_count = row.new_asset or 0

    # Completion percentage
    completion = (verified_count / total_assets * 100) if total_assets > 0 else 0.0

    return {
        "cycle_id": cycle.id,
        "tag": cycle.tag,
        "status": cycle.status,
        "total_assets": total_assets,
        "verified_count": verified_count,
        "pending_count": pending_count,
        "self_verified_count": self_verified,
        "auditor_verified_count": auditor_verified,
        "overridden_count": overridden,
        "discrepancy_count": discrepancy_count,
        "not_found_count": not_found_count,
        "new_asset_count": new_asset_count,
        "completion_percentage": round(completion, 2),
    }
