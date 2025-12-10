# api/verification/db_manager.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from db_models.asset import Asset
from db_models.verification_cycle import VerificationCycle
from db_models.asset_verification import AssetVerification
from . import queries



class CycleNotFoundError(Exception):
    pass


async def get_cycle_or_raise(db: AsyncSession, cycle_id: int) -> VerificationCycle:
    stmt = queries.select_cycle_by_id(cycle_id)
    result = await db.execute(stmt)
    cycle = result.scalar_one_or_none()
    if cycle is None:
        raise CycleNotFoundError(f"Cycle {cycle_id} not found")
    return cycle


async def lookup_asset_for_cycle(
    db: AsyncSession,
    asset_code: str,
    cycle_id: int,
) -> tuple[Asset | None, AssetVerification | None, bool]:
    """
    Returns:
      asset,
      effective_verification (or None),
      already_verified flag
    """
    # Ensure cycle exists (for now we don't use the result directly)
    await get_cycle_or_raise(db, cycle_id)

    # Find asset by code
    stmt = queries.select_asset_by_code(asset_code)
    result = await db.execute(stmt)
    asset = result.scalar_one_or_none()

    if asset is None:
        return None, None, False

    # Fetch verifications for this asset + cycle
    stmt = queries.select_verifications_for_asset_cycle(asset.id, cycle_id)
    result = await db.execute(stmt)
    verifications = list(result.scalars().all())

    if not verifications:
        return asset, None, False

    # Simple rule for now:
    # effective_verification = first in list (latest created_at)
    effective = verifications[0]
    already_verified = True

    return asset, effective, already_verified

async def search_assets(db: AsyncSession, query_text: str) -> list[Asset]:
    stmt = queries.search_assets_query(query_text)
    result = await db.execute(stmt)
    return list(result.scalars().all())


class CycleNotFoundError(Exception):
    pass


class AssetAlreadyExistsError(Exception):
    pass


async def ensure_cycle_exists(db: AsyncSession, cycle_id: int) -> VerificationCycle:
    stmt = queries.select_cycle_by_id(cycle_id)
    result = await db.execute(stmt)
    cycle = result.scalar_one_or_none()
    if cycle is None:
        raise CycleNotFoundError(f"Cycle {cycle_id} not found")
    return cycle


async def create_asset_and_initial_verification(
    db: AsyncSession,
    asset_code: str,
    name: str,
    cycle_id: int,
    *,
    owner_hint: str | None = None,
    performed_by: str | None = None,
    source: str = "AUDITOR",
    status: str = "NEW_ASSET",
    photos: list[str] | None = None,
    location_lat: float | None = None,
    location_lng: float | None = None,
    notes: str | None = None,
) -> tuple[Asset, AssetVerification]:
    """
    Creates a new Asset and an initial AssetVerification record atomically.
    Raises:
      - CycleNotFoundError if cycle missing
      - AssetAlreadyExistsError if asset_code already exists
    """

    # Ensure cycle exists
    await ensure_cycle_exists(db, cycle_id)

    # Check asset uniqueness first (best-effort; DB unique constraint is final authority)
    stmt = queries.select_asset_by_code(asset_code)
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()
    if existing is not None:
        raise AssetAlreadyExistsError(f"Asset with code {asset_code} already exists (id={existing.id})")

    # Create asset
    new_asset = Asset(asset_code=asset_code, name=name, owner_id=None, is_active=True)
    db.add(new_asset)
    try:
        await db.flush()  # get new_asset.id populated (does not commit)
    except IntegrityError as exc:
        await db.rollback()
        raise AssetAlreadyExistsError(f"Asset with code {asset_code} already exists") from exc

    # Create verification record
    photos_text = None
    if photos:
        # store as JSON-like string for now (you can change to JSONB later)
        import json
        photos_text = json.dumps(photos)

    verification = AssetVerification(
        asset_id=new_asset.id,
        cycle_id=cycle_id,
        performed_by=performed_by,
        source=source,
        status=status,
        condition=None,
        location_lat=location_lat,
        location_lng=location_lng,
        photos=photos_text,
        notes=notes,
    )
    db.add(verification)

    # Commit both
    await db.commit()

    # refresh objects
    await db.refresh(new_asset)
    await db.refresh(verification)

    return new_asset, verification
