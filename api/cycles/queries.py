# api/route1/queries.py
from sqlalchemy import select

from db_models.verification_cycle import VerificationCycle


def select_cycle_by_tag(tag: str):
    """Select a cycle by its tag."""
    return select(VerificationCycle).where(VerificationCycle.tag == tag)


def select_all_cycles():
    """Select all cycles ordered by creation time (newest first)."""
    return select(VerificationCycle).order_by(VerificationCycle.created_at.desc())
