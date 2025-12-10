# api/route1/models.py
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class CycleCreate(BaseModel):
    tag: str = Field(..., min_length=1, max_length=100, description="Cycle tag, e.g. 'Q2 2025'")


class CycleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tag: str
    status: str
    created_at: datetime
    locked_at: datetime | None = None
