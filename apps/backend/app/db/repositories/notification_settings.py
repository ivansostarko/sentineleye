"""NotificationSettings repository — single-row pattern."""

from __future__ import annotations

from sqlalchemy import select

from app.db.repositories.base import BaseRepository
from app.models.notification_settings import NotificationSettings


class NotificationSettingsRepository(BaseRepository[NotificationSettings]):
    model = NotificationSettings
    SINGLETON_ID = 1

    async def get_singleton(self) -> NotificationSettings:
        result = await self.session.execute(
            select(NotificationSettings).where(NotificationSettings.id == self.SINGLETON_ID),
        )
        row = result.scalar_one_or_none()
        if row is None:
            raise RuntimeError(
                "notification_settings row missing — migration 0008_notif must run first.",
            )
        return row
