"""Wire-format schemas for inter-service events."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class BoundingBox(BaseModel):
    x: float = Field(ge=0, le=1)
    y: float = Field(ge=0, le=1)
    w: float = Field(gt=0, le=1)
    h: float = Field(gt=0, le=1)


class DetectionEventEnvelope(BaseModel):
    """The shape an AI engine pushes to the backend."""

    camera_id: UUID
    occurred_at: datetime
    object_class: str
    confidence: float = Field(ge=0, le=1)
    track_id: int | None = None
    bbox: BoundingBox
    snapshot_b64: str | None = None
