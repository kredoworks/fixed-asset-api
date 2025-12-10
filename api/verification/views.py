# api/verification/views.py
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_session
from .models import AssetLookupResponse, AssetSummary, VerificationSummary,SearchAssetResponse, SearchAssetResult,NewAssetCreate, NewAssetResponse 
from . import db_manager

router = APIRouter(
    prefix="/verification/assets",
    tags=["verification"],
)


@router.get(
    "/lookup",
    response_model=AssetLookupResponse,
    summary="Lookup asset by code for a given verification cycle",
)
async def lookup_asset_endpoint(
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
    db: AsyncSession = Depends(get_session),
) -> NewAssetResponse:
    """
    Create a new asset and an initial verification record in the specified cycle.
    """
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