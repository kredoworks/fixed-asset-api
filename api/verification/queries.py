# api/verification/queries.py
from sqlalchemy import select
from sqlalchemy import or_
from sqlalchemy import func

from db_models.asset import Asset
from db_models.verification_cycle import VerificationCycle
from db_models.asset_verification import AssetVerification


def select_cycle_by_id(cycle_id: int):
    return select(VerificationCycle).where(VerificationCycle.id == cycle_id)


def select_asset_by_code(asset_code: str):
    return select(Asset).where(Asset.asset_code == asset_code)


def select_verifications_for_asset_cycle(asset_id: int, cycle_id: int):
    # Latest first
    return (
        select(AssetVerification)
        .where(
            AssetVerification.asset_id == asset_id,
            AssetVerification.cycle_id == cycle_id,
        )
        .order_by(AssetVerification.created_at.desc())
    )



from db_models.asset import Asset

def search_assets_query(text: str):
    pattern = f"%{text.lower()}%"
    return (
        select(Asset)
        .where(
            or_(
                func.lower(Asset.asset_code).like(pattern),
                func.lower(Asset.name).like(pattern),
            )
        )
        .order_by(Asset.asset_code.asc())
        .limit(50)  # simple guardrail
    )



def select_asset_by_code(asset_code: str):
    return select(Asset).where(Asset.asset_code == asset_code)


def select_cycle_by_id(cycle_id: int):
    return select(VerificationCycle).where(VerificationCycle.id == cycle_id)


def select_verification_by_asset_cycle(asset_id: int, cycle_id: int):
    return (
        select(AssetVerification)
        .where(
            AssetVerification.asset_id == asset_id,
            AssetVerification.cycle_id == cycle_id,
        )
        .order_by(AssetVerification.created_at.desc())
    )
