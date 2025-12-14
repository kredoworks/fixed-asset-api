# api/dashboard/views.py
"""
Dashboard and aggregate statistics endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_session
from core.deps import CurrentUser, AuditorOrAdmin
from .models import (
    DashboardSummary,
    DashboardOverview,
    CycleSummary,
    CycleStats,
    StatusBreakdown,
    ConditionBreakdown,
    SourceBreakdown,
)
from . import db_manager

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get(
    "/overview",
    response_model=DashboardOverview,
    summary="Get high-level overview statistics",
)
async def get_overview_endpoint(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_session),
) -> DashboardOverview:
    """
    Get high-level overview statistics across all cycles.
    Includes total assets, active cycle, and recent cycles.
    """
    stats = await db_manager.get_overview_stats(db)

    # Get active assets count for completion calculation
    active_assets = stats["active_assets"]

    # Build active cycle summary if exists
    active_cycle_summary = None
    if stats["active_cycle"]:
        cycle_data = await db_manager.get_cycle_summary(db, stats["active_cycle"], active_assets)
        active_cycle_summary = CycleSummary(**cycle_data)

    # Build recent cycle summaries
    recent_summaries = []
    for cycle in stats["recent_cycles"]:
        cycle_data = await db_manager.get_cycle_summary(db, cycle, active_assets)
        recent_summaries.append(CycleSummary(**cycle_data))

    return DashboardOverview(
        total_assets=stats["total_assets"],
        active_assets=stats["active_assets"],
        inactive_assets=stats["inactive_assets"],
        total_cycles=stats["total_cycles"],
        active_cycle=active_cycle_summary,
        recent_cycles=recent_summaries,
    )


@router.get(
    "/cycles/{cycle_id}",
    response_model=DashboardSummary,
    summary="Get dashboard summary for a specific cycle",
)
async def get_cycle_dashboard_endpoint(
    cycle_id: int,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_session),
) -> DashboardSummary:
    """
    Get complete dashboard summary for a specific verification cycle.
    Includes status, condition, and source breakdowns.
    """
    try:
        data = await db_manager.get_dashboard_summary(db, cycle_id)
    except db_manager.CycleNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return DashboardSummary(
        cycle_id=data["cycle_id"],
        cycle_tag=data["cycle_tag"],
        cycle_status=data["cycle_status"],
        cycle_created_at=data["cycle_created_at"],
        cycle_locked_at=data["cycle_locked_at"],
        total_assets=data["total_assets"],
        verified_count=data["verified_count"],
        pending_count=data["pending_count"],
        completion_percentage=data["completion_percentage"],
        status_breakdown=StatusBreakdown(**data["status_breakdown"]),
        condition_breakdown=ConditionBreakdown(**data["condition_breakdown"]),
        source_breakdown=SourceBreakdown(**data["source_breakdown"]),
    )


@router.get(
    "/cycles/{cycle_id}/stats",
    response_model=CycleStats,
    summary="Get detailed statistics for a cycle",
)
async def get_cycle_stats_endpoint(
    cycle_id: int,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_session),
) -> CycleStats:
    """
    Get detailed statistics for a specific verification cycle.
    """
    try:
        stats = await db_manager.get_cycle_stats(db, cycle_id)
    except db_manager.CycleNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return CycleStats(**stats)


@router.get(
    "/active",
    response_model=DashboardSummary | None,
    summary="Get dashboard for active cycle",
)
async def get_active_cycle_dashboard_endpoint(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_session),
) -> DashboardSummary | None:
    """
    Get dashboard summary for the currently active cycle.
    Returns null if no active cycle exists.
    """
    stats = await db_manager.get_overview_stats(db)

    if stats["active_cycle"] is None:
        return None

    data = await db_manager.get_dashboard_summary(db, stats["active_cycle"].id)

    return DashboardSummary(
        cycle_id=data["cycle_id"],
        cycle_tag=data["cycle_tag"],
        cycle_status=data["cycle_status"],
        cycle_created_at=data["cycle_created_at"],
        cycle_locked_at=data["cycle_locked_at"],
        total_assets=data["total_assets"],
        verified_count=data["verified_count"],
        pending_count=data["pending_count"],
        completion_percentage=data["completion_percentage"],
        status_breakdown=StatusBreakdown(**data["status_breakdown"]),
        condition_breakdown=ConditionBreakdown(**data["condition_breakdown"]),
        source_breakdown=SourceBreakdown(**data["source_breakdown"]),
    )
