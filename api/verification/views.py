# api/verification/views.py
import os
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_session
from core.deps import CurrentUser, CanVerify, AuditorOrAdmin
from .models import (
    AssetLookupResponse,
    AssetSummary,
    VerificationSummary,
    SearchAssetResponse,
    SearchAssetResult,
    NewAssetCreate,
    NewAssetResponse,
    PhotoUploadResponse,
    VerificationCreate,
    VerificationResponse,
    DuplicateResponse,
    OverrideCreate,
    AssetCycleDetailResponse,
    PendingAsset,
    PendingAssetsResponse,
)
from . import db_manager

# Asset-focused router
router = APIRouter(
    prefix="/verification/assets",
    tags=["verification"],
)

# Configure upload directory (local fallback; switch to S3/cloud in production)
UPLOAD_DIR = Path(os.environ.get("UPLOAD_DIR", "uploads"))
UPLOAD_DIR.mkdir(exist_ok=True)


@router.get(
    "/lookup",
    response_model=AssetLookupResponse,
    summary="Lookup asset by code for a given verification cycle",
)
async def lookup_asset_endpoint(
    current_user: CurrentUser,
    asset_code: str = Query(..., min_length=1, description="Asset code / barcode"),
    cycle_id: int = Query(..., description="Verification cycle ID"),
    db: AsyncSession = Depends(get_session),
) -> AssetLookupResponse:
    """
    Given an asset_code and cycle_id:
    - If asset not found: not_found = True
    - If found but not verified in this cycle: not_found = False, already_verified = False
    - If found and verified: not_found = False, already_verified = True + effective verification
    """
    try:
        asset, effective_verification, already_verified =await db_manager.lookup_asset_for_cycle(db, asset_code, cycle_id)
    except db_manager.CycleNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    if asset is None:
        return AssetLookupResponse(
            not_found=True,
            asset=None,
            effective_verification=None,
            already_verified=False,
        )

    asset_summary = AssetSummary.model_validate(asset)

    if effective_verification is None:
        return AssetLookupResponse(
            not_found=False,
            asset=asset_summary,
            effective_verification=None,
            already_verified=False,
        )

    verification_summary = VerificationSummary.model_validate(effective_verification)

    return AssetLookupResponse(
        not_found=False,
        asset=asset_summary,
        effective_verification=verification_summary,
        already_verified=already_verified,
    )

@router.get(
    "/search",
    response_model=SearchAssetResponse,
    summary="Manual search for assets by asset_code or name",
)
async def search_assets_endpoint(
    current_user: CurrentUser,
    q: str = Query(..., min_length=1, description="Search text"),
    db: AsyncSession = Depends(get_session),
) -> SearchAssetResponse:

    assets = await db_manager.search_assets(db, q)

    results = [SearchAssetResult.model_validate(a) for a in assets]

    return SearchAssetResponse(results=results)

@router.post(
    "/new",
    response_model=NewAssetResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new asset and an initial verification in a cycle",
)
async def create_new_asset_endpoint(
    payload: NewAssetCreate,
    current_user: AuditorOrAdmin,  # Only auditors and admins can create new assets
    db: AsyncSession = Depends(get_session),
) -> NewAssetResponse:
    """
    Create a new asset and an initial verification record in the specified cycle.
    Enforces cycle lock - returns 409 if cycle is LOCKED.
    """
    # Cycle lock enforcement: check before any writes
    try:
        await db_manager.check_cycle_not_locked(db, payload.cycle_id)
    except db_manager.CycleLockedError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except db_manager.CycleNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    try:
        new_asset, verification = await db_manager.create_asset_and_initial_verification(
            db,
            asset_code=payload.asset_code,
            name=payload.name,
            cycle_id=payload.cycle_id,
            owner_hint=payload.owner_hint,
            performed_by=payload.performed_by,
            source=payload.source or "AUDITOR",
            status=payload.status or "NEW_ASSET",
            photos=payload.photos,
            location_lat=payload.location_lat,
            location_lng=payload.location_lng,
            notes=payload.notes,
        )
    except db_manager.CycleNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except db_manager.AssetAlreadyExistsError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except Exception as exc:
        # Generic fallback
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create asset") from exc

    return NewAssetResponse(
        asset_id=new_asset.id,
        asset_code=new_asset.asset_code,
        name=new_asset.name,
        verification_id=verification.id,
        verification_status=verification.status,
        verification_source=verification.source,
        verification_created_at=verification.created_at,
    )


# --- Photo Upload Endpoint ---
@router.post(
    "/uploads/photo",
    response_model=PhotoUploadResponse,
    summary="Upload verification photos",
    tags=["uploads"],
)
async def upload_photos(
    current_user: CanVerify,  # Only users who can verify can upload photos
    files: list[UploadFile] = File(..., description="Photo files to upload"),
) -> PhotoUploadResponse:
    """
    Accept multipart upload of photos, store locally (or configured storage).
    Returns array of file keys that can be passed to verification endpoints.
    """
    keys = []
    for file in files:
        # Generate unique key for file
        ext = Path(file.filename).suffix if file.filename else ".jpg"
        file_key = f"{uuid.uuid4()}{ext}"
        file_path = UPLOAD_DIR / file_key

        # Save file
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)

        keys.append(file_key)

    return PhotoUploadResponse(keys=keys)


# --- Create Verification (with duplicate detection and cycle lock) ---
@router.post(
    "/{asset_id}/cycles/{cycle_id}",
    responses={
        201: {"model": VerificationResponse, "description": "Verification created"},
        200: {"model": DuplicateResponse, "description": "Duplicate exists"},
        409: {"description": "Cycle is locked"},
        423: {"description": "Cycle is locked"},
    },
    summary="Create verification for asset in cycle",
)
async def create_verification_endpoint(
    asset_id: int,
    cycle_id: int,
    payload: VerificationCreate,
    current_user: CanVerify,  # Requires verification permissions
    db: AsyncSession = Depends(get_session),
):
    """
    Create a new verification record for asset in cycle.

    - If cycle is LOCKED: returns 409/423.
    - If duplicate exists and allow_duplicate=False: returns 200 with duplicate info.
    - If allowed or no duplicate: creates and returns 201.
    """
    try:
        new_verification, existing, is_duplicate = await db_manager.create_verification(
            db,
            asset_id=asset_id,
            cycle_id=cycle_id,
            performed_by=payload.performed_by,
            source=payload.source,
            status=payload.status,
            condition=payload.condition,
            location_lat=payload.location_lat,
            location_lng=payload.location_lng,
            photos=payload.photos,
            notes=payload.notes,
            allow_duplicate=payload.allow_duplicate,
        )
    except db_manager.CycleLockedError as exc:
        # Cycle is locked - no edits allowed (spec: 409 or 423)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except db_manager.CycleNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except db_manager.AssetNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    if is_duplicate and existing:
        # Return 200 with duplicate info (client must decide to re-submit with allow_duplicate=true)
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "duplicate": True,
                "existing_verification": VerificationResponse.model_validate(existing).model_dump(mode="json"),
            },
        )

    # Created successfully
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content=VerificationResponse.model_validate(new_verification).model_dump(mode="json"),
    )


# --- Get Asset-Cycle Detail with History ---
@router.get(
    "/{asset_id}/cycles/{cycle_id}",
    response_model=AssetCycleDetailResponse,
    summary="Get effective verification and history for asset in cycle",
)
async def get_asset_cycle_detail_endpoint(
    asset_id: int,
    cycle_id: int,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_session),
) -> AssetCycleDetailResponse:
    """
    Returns the effective verification (latest OVERRIDDEN or latest overall)
    and full history for an asset in a cycle.
    """
    try:
        effective, history = await db_manager.get_asset_cycle_detail(db, asset_id, cycle_id)
    except db_manager.AssetNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except db_manager.CycleNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return AssetCycleDetailResponse(
        effective_verification=VerificationResponse.model_validate(effective) if effective else None,
        history=[VerificationResponse.model_validate(v) for v in history],
    )


# --- Additional router for non-asset endpoints (uploads, overrides, pending) ---
verification_router = APIRouter(
    prefix="/verification",
    tags=["verification"],
)


# --- Override Verification Endpoint ---
@verification_router.post(
    "/{verification_id}/override",
    response_model=VerificationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Override an existing verification",
)
async def override_verification_endpoint(
    verification_id: int,
    payload: OverrideCreate,
    current_user: AuditorOrAdmin,  # Only auditors and admins can override
    db: AsyncSession = Depends(get_session),
) -> VerificationResponse:
    """
    Create an override for an existing verification.
    Sets source='OVERRIDDEN' and links to original via override_of_verification_id.
    """
    try:
        override = await db_manager.create_override(
            db,
            verification_id=verification_id,
            performed_by=payload.performed_by,
            source=payload.source,
            status=payload.status,
            condition=payload.condition,
            location_lat=payload.location_lat,
            location_lng=payload.location_lng,
            photos=payload.photos,
            notes=payload.notes,
            override_reason=payload.override_reason,
        )
    except db_manager.CycleLockedError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except db_manager.VerificationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return VerificationResponse.model_validate(override)


# --- Pending Assets Endpoint ---
@verification_router.get(
    "/pending",
    response_model=PendingAssetsResponse,
    summary="List assets without verification in cycle",
)
async def get_pending_assets_endpoint(
    current_user: CurrentUser,
    cycle_id: int = Query(..., description="Verification cycle ID"),
    db: AsyncSession = Depends(get_session),
) -> PendingAssetsResponse:
    """
    Returns all active assets that do NOT have any verification in the specified cycle.
    """
    try:
        pending = await db_manager.get_pending_assets(db, cycle_id)
    except db_manager.CycleNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return PendingAssetsResponse(
        cycle_id=cycle_id,
        pending_count=len(pending),
        assets=[PendingAsset.model_validate(a) for a in pending],
    )