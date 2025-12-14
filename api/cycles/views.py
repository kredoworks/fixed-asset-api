# api/cycles/views.py
"""
Verification cycle management endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_session
from core.deps import AdminUser, CurrentUser
from .models import CycleCreate, CycleRead
from . import db_manager

router = APIRouter(prefix="/cycles", tags=["cycles"])


@router.post(
    "",
    response_model=CycleRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a verification cycle",
)
async def create_cycle_endpoint(
    payload: CycleCreate,
    admin: AdminUser,  # Only admins can create cycles
    db: AsyncSession = Depends(get_session),
) -> CycleRead:
    """
    Create a new verification cycle with a unique tag. Admin only.
    """
    try:
        cycle = await db_manager.create_cycle(db, tag=payload.tag)
    except db_manager.DuplicateTagError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return CycleRead.model_validate(cycle)


@router.get(
    "",
    response_model=list[CycleRead],
    summary="List verification cycles",
)
async def list_cycles_endpoint(
    current_user: CurrentUser,  # Any authenticated user can list cycles
    db: AsyncSession = Depends(get_session),
) -> list[CycleRead]:
    """
    List all verification cycles, newest first.
    """
    cycles = await db_manager.list_cycles(db)
    return [CycleRead.model_validate(c) for c in cycles]


@router.get(
    "/active",
    response_model=CycleRead | None,
    summary="Get active verification cycle",
)
async def get_active_cycle_endpoint(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_session),
) -> CycleRead | None:
    """
    Get the most recent ACTIVE cycle, or null if none exists.
    """
    cycle = await db_manager.get_active_cycle(db)
    if cycle is None:
        return None
    return CycleRead.model_validate(cycle)


@router.get(
    "/{cycle_id}",
    response_model=CycleRead,
    summary="Get verification cycle by ID",
)
async def get_cycle_endpoint(
    cycle_id: int,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_session),
) -> CycleRead:
    """
    Get a specific verification cycle by ID.
    """
    try:
        cycle = await db_manager.get_cycle_by_id(db, cycle_id)
    except db_manager.CycleNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return CycleRead.model_validate(cycle)


@router.post(
    "/{cycle_id}/activate",
    response_model=CycleRead,
    summary="Activate a DRAFT cycle",
)
async def activate_cycle_endpoint(
    cycle_id: int,
    admin: AdminUser,  # Only admins can change cycle status
    db: AsyncSession = Depends(get_session),
) -> CycleRead:
    """
    Activate a DRAFT cycle. Admin only.
    """
    try:
        cycle = await db_manager.activate_cycle(db, cycle_id)
    except db_manager.CycleNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except db_manager.CycleStatusError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    return CycleRead.model_validate(cycle)


@router.post(
    "/{cycle_id}/lock",
    response_model=CycleRead,
    summary="Lock an ACTIVE cycle",
)
async def lock_cycle_endpoint(
    cycle_id: int,
    admin: AdminUser,  # Only admins can lock cycles
    db: AsyncSession = Depends(get_session),
) -> CycleRead:
    """
    Lock an ACTIVE cycle. Prevents further verifications. Admin only.
    """
    try:
        cycle = await db_manager.lock_cycle(db, cycle_id)
    except db_manager.CycleNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except db_manager.CycleStatusError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    return CycleRead.model_validate(cycle)


@router.post(
    "/{cycle_id}/unlock",
    response_model=CycleRead,
    summary="Unlock a LOCKED cycle",
)
async def unlock_cycle_endpoint(
    cycle_id: int,
    admin: AdminUser,  # Only admins can unlock cycles
    db: AsyncSession = Depends(get_session),
) -> CycleRead:
    """
    Unlock a LOCKED cycle. Allows further verifications. Admin only.
    """
    try:
        cycle = await db_manager.unlock_cycle(db, cycle_id)
    except db_manager.CycleNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except db_manager.CycleStatusError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    return CycleRead.model_validate(cycle)
