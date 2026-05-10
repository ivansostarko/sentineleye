"""Notification settings endpoints (admin-only)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.v1.deps import get_current_user, notification_settings_service, require_role
from app.models.notification_settings import NotificationSettings
from app.models.user import User, UserRole
from app.schemas.notification_settings import (
    NotificationSettingsPublic,
    NotificationSettingsUpdate,
)
from app.services.notification_settings_service import NotificationSettingsService

router = APIRouter(prefix="/notification-settings", tags=["notifications"])


def _to_public(entity: NotificationSettings) -> NotificationSettingsPublic:
    return NotificationSettingsPublic(
        master_enabled=entity.master_enabled,
        silent_hours_enabled=entity.silent_hours_enabled,
        silent_hours_start=entity.silent_hours_start,
        silent_hours_end=entity.silent_hours_end,
        push_enabled=entity.push_enabled,
        push_sound=entity.push_sound,
        push_vibrate=entity.push_vibrate,
        push_min_severity=entity.push_min_severity,
        push_show_preview=entity.push_show_preview,
        email_enabled=entity.email_enabled,
        email_recipients=list(entity.email_recipients or []),
        email_subject_prefix=entity.email_subject_prefix,
        email_min_severity=entity.email_min_severity,
        email_batch_minutes=entity.email_batch_minutes,
        email_include_snapshot=entity.email_include_snapshot,
        telegram_enabled=entity.telegram_enabled,
        telegram_chat_ids=list(entity.telegram_chat_ids or []),
        telegram_min_severity=entity.telegram_min_severity,
        telegram_silent=entity.telegram_silent,
        telegram_disable_preview=entity.telegram_disable_preview,
        telegram_token_set=NotificationSettingsService.telegram_token_set(entity),
        created_at=entity.created_at,
        updated_at=entity.updated_at,
    )


@router.get(
    "",
    response_model=NotificationSettingsPublic,
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
async def get_settings(
    service: Annotated[NotificationSettingsService, Depends(notification_settings_service)],
) -> NotificationSettingsPublic:
    return _to_public(await service.get())


@router.patch(
    "",
    response_model=NotificationSettingsPublic,
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
async def update_settings(
    payload: NotificationSettingsUpdate,
    service: Annotated[NotificationSettingsService, Depends(notification_settings_service)],
    _user: Annotated[User, Depends(get_current_user)],
) -> NotificationSettingsPublic:
    return _to_public(await service.update(payload))
