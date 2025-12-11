# api/verification/models.py
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from typing import List, Optional


class AssetSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    asset_code: str
    name: str
    is_active: bool


class VerificationSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source: str
    status: str
    condition: str | None = None
    created_at: datetime
    verified_at: datetime | None = None
    notes: str | None = None
    location_lat: float | None = None
    location_lng: float | None = None
    override_of_verification_id: int | None = None


class AssetLookupResponse(BaseModel):
    not_found: bool
    asset: AssetSummary | None = None
    effective_verification: VerificationSummary | None = None
    already_verified: bool = False

class SearchAssetResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    asset_code: str
    name: str
    is_active: bool


class SearchAssetResponse(BaseModel):
    results: list[SearchAssetResult]





class NewAssetCreate(BaseModel):
    asset_code: str = Field(..., min_length=1, max_length=100)
    name: str = Field(..., min_length=1, max_length=255)
    owner_hint: Optional[str] = None

    # The cycle where this asset is discovered (required)
    cycle_id: int

    # Who reports it (optional string, later will be user_id)
    performed_by: Optional[str] = None

    # Source who discovered it: 'AUDITOR' or 'SELF' (default AUDITOR)
    source: Optional[str] = "AUDITOR"

    # Initial status for the asset verification (default NEW_ASSET)
    status: Optional[str] = "NEW_ASSET"

    # Optional verification metadata
    photos: Optional[List[str]] = None
    location_lat: Optional[float] = None
    location_lng: Optional[float] = None
    notes: Optional[str] = None


class NewAssetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    asset_id: int
    asset_code: str
    name: str

    verification_id: int
    verification_status: str
    verification_source: str
    verification_created_at: datetime | None = None


# --- Photo Upload Models ---
class PhotoUploadResponse(BaseModel):
    keys: List[str]


# --- Verification Create Models (with duplicate detection) ---
class VerificationCreate(BaseModel):
    performed_by: Optional[str] = None
    source: str = "SELF"  # SELF | AUDITOR
    status: str = "VERIFIED"  # VERIFIED | DISCREPANCY | NOT_FOUND | NEW_ASSET
    condition: Optional[str] = None  # GOOD | DAMAGED | NEEDS_REPAIR
    location_lat: Optional[float] = None
    location_lng: Optional[float] = None
    photos: Optional[List[str]] = None
    notes: Optional[str] = None
    allow_duplicate: bool = False  # Client must set true to force create duplicate


class VerificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    asset_id: int
    cycle_id: int
    performed_by: Optional[str] = None
    source: str
    status: str
    condition: Optional[str] = None
    location_lat: Optional[float] = None
    location_lng: Optional[float] = None
    photos: Optional[str] = None
    notes: Optional[str] = None
    override_of_verification_id: Optional[int] = None
    override_reason: Optional[str] = None
    created_at: datetime
    verified_at: Optional[datetime] = None


class DuplicateResponse(BaseModel):
    duplicate: bool = True
    existing_verification: VerificationResponse


# --- Override Models ---
class OverrideCreate(BaseModel):
    performed_by: Optional[str] = None
    source: str = "OVERRIDDEN"  # Should be OVERRIDDEN
    status: str  # New status
    condition: Optional[str] = None
    location_lat: Optional[float] = None
    location_lng: Optional[float] = None
    photos: Optional[List[str]] = None
    notes: Optional[str] = None
    override_reason: str  # Required: explain why overriding


# --- Asset-Cycle Detail with History ---
class AssetCycleDetailResponse(BaseModel):
    effective_verification: Optional[VerificationResponse] = None
    history: List[VerificationResponse]


# --- Pending Assets ---
class PendingAsset(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    asset_code: str
    name: str
    is_active: bool


class PendingAssetsResponse(BaseModel):
    cycle_id: int
    pending_count: int
    assets: List[PendingAsset]
