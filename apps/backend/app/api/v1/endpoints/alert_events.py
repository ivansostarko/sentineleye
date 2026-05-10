"""Alert event (fired-alert history) endpoints."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.api.v1.deps import alert_event_repo, get_current_user
from app.core.exceptions import NotFoundError
from app.db.repositories import AlertEventRepository
from app.models.alert_event import AlertEvent
from app.models.user import User
from app.schemas.alert import AlertEventPublic
from app.schemas.common import Page

router = APIRouter(prefix="/alert-events", tags=["alerts"])


def _to_public(e: AlertEvent) -> AlertEventPublic:
    return AlertEventPublic.model_validate(e, from_attributes=True)


@router.get("", response_model=Page[AlertEventPublic])
async def list_events(
    repo: Annotated[AlertEventRepository, Depends(alert_event_repo)],
    _user: Annotated[User, Depends(get_current_user)],
    only_unacknowledged: bool = False,
    rule_id: UUID | None = None,
    camera_id: UUID | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
) -> Page[AlertEventPublic]:
    items = await repo.list(
        offset=(page - 1) * size,
        limit=size,
        only_unacknowledged=only_unacknowledged,
        rule_id=rule_id,
        camera_id=camera_id,
    )
    total = await repo.count(only_unacknowledged=only_unacknowledged)
    return Page[AlertEventPublic](
        items=[_to_public(e) for e in items], total=total, page=page, size=size,
    )


@router.post("/{event_id}/acknowledge", status_code=status.HTTP_204_NO_CONTENT)
async def acknowledge_event(
    event_id: UUID,
    repo: Annotated[AlertEventRepository, Depends(alert_event_repo)],
    user: Annotated[User, Depends(get_current_user)],
) -> None:
    ok = await repo.acknowledge(event_id, user_id=user.id, now=datetime.now(UTC))
    if not ok:
        raise NotFoundError("Alert event not found or already acknowledged.")
