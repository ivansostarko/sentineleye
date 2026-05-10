"""Notification settings service — encrypts the Telegram bot token on write."""

from __future__ import annotations

from app.db.repositories.notification_settings import NotificationSettingsRepository
from app.models.notification_settings import NotificationSettings
from app.schemas.notification_settings import NotificationSettingsUpdate
from app.services import crypto

_TOKEN_PLACEHOLDER = "__seed_placeholder__"


class NotificationSettingsService:
    def __init__(self, repo: NotificationSettingsRepository) -> None:
        self.repo = repo

    async def get(self) -> NotificationSettings:
        return await self.repo.get_singleton()

    async def update(self, payload: NotificationSettingsUpdate) -> NotificationSettings:
        entity = await self.get()
        data = payload.model_dump(exclude_unset=True)

        if "telegram_bot_token" in data:
            entity.telegram_bot_token_enc = crypto.encrypt(data.pop("telegram_bot_token"))

        # Pydantic returns EmailStr instances for emails; coerce to str for JSON.
        if "email_recipients" in data and data["email_recipients"] is not None:
            data["email_recipients"] = [str(e) for e in data["email_recipients"]]

        for field, value in data.items():
            setattr(entity, field, value)

        await self.repo.session.flush()
        return entity

    @staticmethod
    def telegram_token_set(entity: NotificationSettings) -> bool:
        return entity.telegram_bot_token_enc != _TOKEN_PLACEHOLDER
