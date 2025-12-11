# api/verification/db_manager.py
import json
from datetime import datetime, timezone

from sqlalchemy import select, and_, not_
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


# --- Cycle Lock Enforcement ---
class CycleLockedError(Exception):
    """Raised when trying to modify a locked cycle"""
    pass


class AssetNotFoundError(Exception):
    """Raised when asset doesn't exist"""
    pass


class VerificationNotFoundError(Exception):
    """Raised when verification doesn't exist"""
    pass


async def check_cycle_not_locked(db: AsyncSession, cycle_id: int) -> VerificationCycle:
    """Ensure cycle exists and is not LOCKED. Returns cycle if valid."""
    cycle = await get_cycle_or_raise(db, cycle_id)
    if cycle.status == "LOCKED":
        raise CycleLockedError("Cycle is locked. No further edits allowed.")
    return cycle


async def get_asset_or_raise(db: AsyncSession, asset_id: int) -> Asset:
    """Get asset by ID or raise AssetNotFoundError"""
    stmt = select(Asset).where(Asset.id == asset_id)
    result = await db.execute(stmt)
    asset = result.scalar_one_or_none()
    if asset is None:
        raise AssetNotFoundError(f"Asset {asset_id} not found")
    return asset


async def get_verification_or_raise(db: AsyncSession, verification_id: int) -> AssetVerification:
    """Get verification by ID or raise VerificationNotFoundError"""
    stmt = select(AssetVerification).where(AssetVerification.id == verification_id)
    result = await db.execute(stmt)
    verification = result.scalar_one_or_none()
    if verification is None:
        raise VerificationNotFoundError(f"Verification {verification_id} not found")
    return verification


# --- Duplicate Detection ---
async def find_existing_verification(
    db: AsyncSession,
    asset_id: int,
    cycle_id: int
) -> AssetVerification | None:
    """
    Find existing finalized verification for asset+cycle.
    Returns latest verification if exists, None otherwise.
    """
    stmt = (
        select(AssetVerification)
        .where(
            AssetVerification.asset_id == asset_id,
            AssetVerification.cycle_id == cycle_id,
        )
        .order_by(AssetVerification.created_at.desc())
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


# --- Create Verification with Duplicate Detection ---
async def create_verification(
    db: AsyncSession,
    asset_id: int,
    cycle_id: int,
    *,
    performed_by: str | None = None,
    source: str = "SELF",
    status: str = "VERIFIED",
    condition: str | None = None,
    location_lat: float | None = None,
    location_lng: float | None = None,
    photos: list[str] | None = None,
    notes: str | None = None,
    allow_duplicate: bool = False,
) -> tuple[AssetVerification | None, AssetVerification | None, bool]:
    """
    Create verification with duplicate detection.

    Returns: (new_verification, existing_verification, is_duplicate)
    - If duplicate exists and allow_duplicate=False: (None, existing, True)
    - If created: (new_verification, None, False)

    Raises: CycleLockedError, AssetNotFoundError, CycleNotFoundError
    """
    # Check cycle not locked
    await check_cycle_not_locked(db, cycle_id)

    # Check asset exists
    await get_asset_or_raise(db, asset_id)

    # Check for existing verification
    existing = await find_existing_verification(db, asset_id, cycle_id)

    if existing and not allow_duplicate:
        return None, existing, True

    # Create new verification
    photos_text = json.dumps(photos) if photos else None

    verification = AssetVerification(
        asset_id=asset_id,
        cycle_id=cycle_id,
        performed_by=performed_by,
        source=source,
        status=status,
        condition=condition,
        location_lat=location_lat,
        location_lng=location_lng,
        photos=photos_text,
        notes=notes,
        verified_at=datetime.now(timezone.utc),
    )
    db.add(verification)
    await db.commit()
    await db.refresh(verification)

    return verification, None, False


# --- Override Verification ---
async def create_override(
    db: AsyncSession,
    verification_id: int,
    *,
    performed_by: str | None = None,
    source: str = "OVERRIDDEN",
    status: str,
    condition: str | None = None,
    location_lat: float | None = None,
    location_lng: float | None = None,
    photos: list[str] | None = None,
    notes: str | None = None,
    override_reason: str,
) -> AssetVerification:
    """
    Create an override of an existing verification.

    Raises: CycleLockedError, VerificationNotFoundError
    """
    # Get original verification
    original = await get_verification_or_raise(db, verification_id)

    # Check cycle not locked
    await check_cycle_not_locked(db, original.cycle_id)

    # Create override verification
    photos_text = json.dumps(photos) if photos else None

    override = AssetVerification(
        asset_id=original.asset_id,
        cycle_id=original.cycle_id,
        performed_by=performed_by,
        source=source,
        status=status,
        condition=condition,
        location_lat=location_lat,
        location_lng=location_lng,
        photos=photos_text,
        notes=notes,
        override_of_verification_id=verification_id,
        override_reason=override_reason,
        verified_at=datetime.now(timezone.utc),
    )
    db.add(override)
    await db.commit()
    await db.refresh(override)

    return override


# --- Get Effective Verification with History ---
async def get_asset_cycle_detail(
    db: AsyncSession,
    asset_id: int,
    cycle_id: int,
) -> tuple[AssetVerification | None, list[AssetVerification]]:
    """
    Get effective verification and full history for asset+cycle.

    Rule: effective = latest OVERRIDDEN if exists, else latest non-overridden.

    Returns: (effective_verification, history_list)
    """
    # Ensure both exist
    await get_asset_or_raise(db, asset_id)
    await get_cycle_or_raise(db, cycle_id)

    # Get all verifications for this asset+cycle, newest first
    stmt = (
        select(AssetVerification)
        .where(
            AssetVerification.asset_id == asset_id,
            AssetVerification.cycle_id == cycle_id,
        )
        .order_by(AssetVerification.created_at.desc())
    )
    result = await db.execute(stmt)
    history = list(result.scalars().all())

    if not history:
        return None, []

    # Find effective: prefer latest OVERRIDDEN, else latest overall
    effective = None
    for v in history:
        if v.source == "OVERRIDDEN":
            effective = v
            break

    if effective is None:
        effective = history[0]  # Latest non-overridden

    return effective, history


# --- Get Pending Assets (not verified in cycle) ---
async def get_pending_assets(
    db: AsyncSession,
    cycle_id: int,
) -> list[Asset]:
    """
    Get all active assets that do NOT have any verification in the given cycle.
    """
    await get_cycle_or_raise(db, cycle_id)

    # Subquery: asset_ids that have been verified in this cycle
    verified_subq = (
        select(AssetVerification.asset_id)
        .where(AssetVerification.cycle_id == cycle_id)
        .distinct()
    )

    # Main query: active assets NOT in the verified list
    stmt = (
        select(Asset)
        .where(
            Asset.is_active == True,
            not_(Asset.id.in_(verified_subq)),
        )
        .order_by(Asset.asset_code.asc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


# --- Get Active Cycle (most recent ACTIVE) ---
async def get_active_cycle(db: AsyncSession) -> VerificationCycle | None:
    """Get the most recent active cycle, or None if no active cycle."""
    stmt = (
        select(VerificationCycle)
        .where(VerificationCycle.status == "ACTIVE")
        .order_by(VerificationCycle.created_at.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()
