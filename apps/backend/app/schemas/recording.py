"""Recording schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.models.recording import StorageBackend


class RecordingPublic(BaseModel):
    id: UUID
    camera_id: UUID
    started_at: datetime
    ended_at: datetime | None = None
    duration_seconds: float | None = None
    storage_backend: StorageBackend
    storage_key: str
    bytes_size: int | None = None
    codec: str | None = None
    playback_url: str | None = None
