"""Detection event endpoints (search & ingest)."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.api.v1.deps import (
    alert_service,
    detection_repo,
    get_current_user,
)
from app.models.detection_event import DetectionEvent
from app.models.user import User
from app.schemas.common import Page
from app.schemas.detection_event import DetectionEventCreate, DetectionEventPublic
from app.services.alert_service import AlertService
from app.services.event_bus import DETECTION_CHANNEL, publish

router = APIRouter(prefix="/detection-events", tags=["detection-events"])


def _to_public(event: DetectionEvent, *, camera_name: str | None = None) -> DetectionEventPublic:
    return DetectionEventPublic.model_validate(
        {
            "id": event.id,
            "camera_id": event.camera_id,
            "camera_name": camera_name,
            "occurred_at": event.occurred_at,
            "object_class": event.object_class,
            "confidence": event.confidence,
            "track_id": event.track_id,
            "bbox": event.bbox,
            "snapshot_key": event.snapshot_key,
            "recording_id": event.recording_id,
            "created_at": event.created_at,
        }
    )


@router.get("", response_model=Page[DetectionEventPublic])
async def list_events(
    repo: Annotated[..., Depends(detection_repo)],  # type: ignore[valid-type]
    _user: Annotated[User, Depends(get_current_user)],
    camera_id: UUID | None = None,
    object_class: str | None = None,
    classes_in: list[str] | None = Query(default=None),
    min_confidence: float | None = Query(default=None, ge=0.0, le=1.0),
    start: datetime | None = None,
    end: datetime | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
) -> Page[DetectionEventPublic]:
    items, total = await repo.search(
        camera_id=camera_id,
        object_class=object_class,
        classes_in=classes_in,
        min_confidence=min_confidence,
        start=start,
        end=end,
        offset=(page - 1) * size,
        limit=size,
    )
    return Page[DetectionEventPublic](
        items=[_to_public(e, camera_name=name) for (e, name) in items],
        total=total,
        page=page,
        size=size,
    )


@router.post("", response_model=DetectionEventPublic, status_code=status.HTTP_201_CREATED)
async def ingest_event(
    payload: DetectionEventCreate,
    repo: Annotated[..., Depends(detection_repo)],  # type: ignore[valid-type]
    alerts: Annotated[AlertService, Depends(alert_service)],
    # Note: in production the AI engine authenticates via service token, not user JWT.
) -> DetectionEventPublic:
    event = DetectionEvent(
        camera_id=payload.camera_id,
        occurred_at=payload.occurred_at,
        object_class=payload.object_class,
        confidence=payload.confidence,
        track_id=payload.track_id,
        bbox=payload.bbox.model_dump(),
        snapshot_key=payload.snapshot_key,
        recording_id=payload.recording_id,
    )
    event = await repo.add(event)
    public = _to_public(event)
    await publish(DETECTION_CHANNEL, public.model_dump(mode="json"))
    # Best-effort alert evaluation. Any failure is logged inside AlertService;
    # the ingest path itself never blocks on alerting or notification.
    await alerts.evaluate_detection(event)
    return public
