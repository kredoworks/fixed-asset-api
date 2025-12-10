# api/route1/db_manager.py
from sqlalchemy.ext.asyncio import AsyncSession

from db_models.verification_cycle import VerificationCycle
from . import queries


async def create_cycle(db: AsyncSession, tag: str) -> VerificationCycle:
    """Create a new verification cycle with the given tag."""
    # Check if tag already exists
    stmt = queries.select_cycle_by_tag(tag)
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()
    if existing is not None:
        raise ValueError("Cycle with this tag already exists")

    cycle = VerificationCycle(tag=tag, status="ACTIVE")
    db.add(cycle)
    await db.commit()
    await db.refresh(cycle)
    return cycle


async def list_cycles(db: AsyncSession) -> list[VerificationCycle]:
    """Return all cycles ordered by created_at desc."""
    stmt = queries.select_all_cycles()
    result = await db.execute(stmt)
    return list(result.scalars().all())
