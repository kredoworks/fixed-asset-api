# api/verification/models.py
from datetime import datetime
from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional


class AssetSummary(BaseModel):
    id: int
    asset_code: str
    name: str
    is_active: bool

    class Config:
        from_attributes = True  # Pydantic v2 ORM mode


class VerificationSummary(BaseModel):
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

    class Config:
        from_attributes = True


class AssetLookupResponse(BaseModel):
    not_found: bool
    asset: AssetSummary | None = None
    effective_verification: VerificationSummary | None = None
    already_verified: bool = False

class SearchAssetResult(BaseModel):
    id: int
    asset_code: str
    name: str
    is_active: bool

    class Config:
        from_attributes = True


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
    asset_id: int
    asset_code: str
    name: str

    verification_id: int
    verification_status: str
    verification_source: str
    verification_created_at: datetime | None = None

    class Config:
        from_attributes = True
