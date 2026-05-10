"""Recording playback & metadata endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.api.v1.deps import get_current_user, recording_repo
from app.models.recording import Recording, StorageBackend
from app.models.user import User
from app.schemas.recording import RecordingPublic
from app.services.storage import get_storage

router = APIRouter(prefix="/recordings", tags=["recordings"])


async def _to_public(rec: Recording) -> RecordingPublic:
    storage = get_storage()
    playback_url: str | None = None
    if rec.storage_backend == StorageBackend.S3:
        playback_url = await storage.signed_url(rec.storage_key)
    elif rec.storage_backend == StorageBackend.LOCAL:
        playback_url = await storage.signed_url(rec.storage_key)
    return RecordingPublic(
        id=rec.id,
        camera_id=rec.camera_id,
        started_at=rec.started_at,
        ended_at=rec.ended_at,
        duration_seconds=rec.duration_seconds,
        storage_backend=rec.storage_backend,
        storage_key=rec.storage_key,
        bytes_size=rec.bytes_size,
        codec=rec.codec,
        playback_url=playback_url,
    )


@router.get("", response_model=list[RecordingPublic])
async def list_recordings(
    repo: Annotated[..., Depends(recording_repo)],  # type: ignore[valid-type]
    _user: Annotated[User, Depends(get_current_user)],
    camera_id: UUID = Query(...),
    start: datetime | None = None,
    end: datetime | None = None,
    limit: int = Query(100, ge=1, le=500),
) -> list[RecordingPublic]:
    items = await repo.list_for_camera(camera_id, start=start, end=end, limit=limit)
    return [await _to_public(r) for r in items]


@router.get("/{recording_id}", response_model=RecordingPublic)
async def get_recording(
    recording_id: UUID,
    repo: Annotated[..., Depends(recording_repo)],  # type: ignore[valid-type]
    _user: Annotated[User, Depends(get_current_user)],
) -> RecordingPublic:
    from app.core.exceptions import NotFoundError

    rec = await repo.get(recording_id)
    if rec is None:
        raise NotFoundError(f"Recording {recording_id} not found.")
    return await _to_public(rec)
