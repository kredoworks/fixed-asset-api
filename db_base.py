from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    """
    Base class for all ORM models.

    This file intentionally has NO engine/session imports so that tools like
    Alembic can import Base without pulling in async drivers.
    """
    pass