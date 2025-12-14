# api/dashboard/models.py
"""
Pydantic models for dashboard responses.
"""
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class CycleStats(BaseModel):
    """Statistics for a single verification cycle."""
    model_config = ConfigDict(from_attributes=True)

    cycle_id: int
    tag: str
    status: str
    total_assets: int
    verified_count: int
    pending_count: int
    self_verified_count: int
    auditor_verified_count: int
    overridden_count: int
    discrepancy_count: int
    not_found_count: int
    new_asset_count: int
    completion_percentage: float


class StatusBreakdown(BaseModel):
    """Breakdown of verification statuses."""
    verified: int = 0
    discrepancy: int = 0
    not_found: int = 0
    new_asset: int = 0


class ConditionBreakdown(BaseModel):
    """Breakdown of asset conditions."""
    good: int = 0
    damaged: int = 0
    needs_repair: int = 0
    not_specified: int = 0


class SourceBreakdown(BaseModel):
    """Breakdown of verification sources."""
    self_verified: int = 0
    auditor_verified: int = 0
    overridden: int = 0


class DashboardSummary(BaseModel):
    """Complete dashboard summary for a cycle."""
    model_config = ConfigDict(from_attributes=True)

    cycle_id: int
    cycle_tag: str
    cycle_status: str
    cycle_created_at: datetime
    cycle_locked_at: datetime | None = None

    total_assets: int
    verified_count: int
    pending_count: int
    completion_percentage: float

    status_breakdown: StatusBreakdown
    condition_breakdown: ConditionBreakdown
    source_breakdown: SourceBreakdown


class CycleSummary(BaseModel):
    """Summary of a cycle for listing."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    tag: str
    status: str
    created_at: datetime
    locked_at: datetime | None = None
    total_verifications: int
    completion_percentage: float


class DashboardOverview(BaseModel):
    """High-level overview across all cycles."""
    total_assets: int
    active_assets: int
    inactive_assets: int
    total_cycles: int
    active_cycle: CycleSummary | None = None
    recent_cycles: list[CycleSummary]
