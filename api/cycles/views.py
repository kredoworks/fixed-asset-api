from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_session
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
    db: AsyncSession = Depends(get_session),
) -> CycleRead:
    """
    Create a new verification cycle with a unique tag.
    """
    try:
        cycle = await db_manager.create_cycle(db, tag=payload.tag)
    except ValueError as exc:
        # duplicate tag error from db_manager
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
    db: AsyncSession = Depends(get_session),
) -> list[CycleRead]:
    """
    List all verification cycles, newest first.
    """
    cycles = await db_manager.list_cycles(db)
    return [CycleRead.model_validate(c) for c in cycles]
