"""Recording playback & metadata endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.api.v1.deps import get_current_user, recording_repo
from app.core.exceptions import NotFoundError
from app.db.repositories.recording import RecordingRepository
from app.models.recording import Recording, StorageBackend
from app.models.user import User
from app.schemas.common import Page
from app.schemas.recording import RecordingPublic
from app.services.storage import get_storage

router = APIRouter(prefix="/recordings", tags=["recordings"])


async def _to_public(rec: Recording, *, camera_name: str | None) -> RecordingPublic:
    storage = get_storage()
    playback_url: str | None = None
    if rec.storage_backend in {StorageBackend.LOCAL, StorageBackend.S3}:
        playback_url = await storage.signed_url(rec.storage_key)
    return RecordingPublic(
        id=rec.id,
        camera_id=rec.camera_id,
        camera_name=camera_name,
        started_at=rec.started_at,
        ended_at=rec.ended_at,
        duration_seconds=rec.duration_seconds,
        storage_backend=rec.storage_backend,
        storage_key=rec.storage_key,
        bytes_size=rec.bytes_size,
        codec=rec.codec,
        playback_url=playback_url,
    )


@router.get("", response_model=Page[RecordingPublic])
async def list_recordings(
    repo: Annotated[RecordingRepository, Depends(recording_repo)],
    _user: Annotated[User, Depends(get_current_user)],
    camera_id: UUID | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
    min_duration: float | None = Query(default=None, ge=0),
    max_duration: float | None = Query(default=None, ge=0),
    query: str | None = Query(default=None, max_length=255),
    sort_by: Literal["started_at", "duration_seconds", "bytes_size"] = "started_at",
    sort_desc: bool = True,
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
) -> Page[RecordingPublic]:
    items, total = await repo.search(
        camera_id=camera_id,
        start=start,
        end=end,
        min_duration=min_duration,
        max_duration=max_duration,
        query=query,
        sort_by=sort_by,
        sort_desc=sort_desc,
        offset=(page - 1) * size,
        limit=size,
    )
    return Page[RecordingPublic](
        items=[await _to_public(r, camera_name=name) for (r, name) in items],
        total=total,
        page=page,
        size=size,
    )


@router.get("/{recording_id}", response_model=RecordingPublic)
async def get_recording(
    recording_id: UUID,
    repo: Annotated[RecordingRepository, Depends(recording_repo)],
    _user: Annotated[User, Depends(get_current_user)],
) -> RecordingPublic:
    rec = await repo.get(recording_id)
    if rec is None:
        raise NotFoundError(f"Recording {recording_id} not found.")
    return await _to_public(rec, camera_name=None)
