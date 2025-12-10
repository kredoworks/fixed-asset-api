# api/route1/models.py
from datetime import datetime
from pydantic import BaseModel, Field


class CycleCreate(BaseModel):
    tag: str = Field(..., min_length=1, max_length=100, description="Cycle tag, e.g. 'Q2 2025'")


class CycleRead(BaseModel):
    id: int
    tag: str
    status: str
    created_at: datetime
    locked_at: datetime | None = None

    class Config:
        from_attributes = True  # Pydantic v2: enable ORM mode
