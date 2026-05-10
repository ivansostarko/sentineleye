"""Detection event schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class BoundingBox(BaseModel):
    """Normalized bounding box (all values in [0, 1])."""

    x: float = Field(ge=0, le=1)
    y: float = Field(ge=0, le=1)
    w: float = Field(gt=0, le=1)
    h: float = Field(gt=0, le=1)


class DetectionEventCreate(BaseModel):
    camera_id: UUID
    occurred_at: datetime
    object_class: str = Field(min_length=1, max_length=64)
    confidence: float = Field(ge=0, le=1)
    track_id: int | None = None
    bbox: BoundingBox
    snapshot_key: str | None = None
    recording_id: UUID | None = None


class DetectionEventPublic(DetectionEventCreate):
    id: UUID
    created_at: datetime
    snapshot_url: str | None = None
