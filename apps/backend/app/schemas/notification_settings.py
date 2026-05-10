"""Notification settings schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.models.alert_rule import AlertSeverity

PUSH_SOUNDS = ("default", "silent", "alert", "bell", "chime")
_TIME_RE = r"^([01]\d|2[0-3]):[0-5]\d$"


class NotificationSettingsPublic(BaseModel):
    """Response shape — never includes the raw Telegram bot token."""

    # Global
    master_enabled: bool
    silent_hours_enabled: bool
    silent_hours_start: str
    silent_hours_end: str

    # Push
    push_enabled: bool
    push_sound: str
    push_vibrate: bool
    push_min_severity: AlertSeverity
    push_show_preview: bool

    # Email
    email_enabled: bool
    email_recipients: list[str]
    email_subject_prefix: str
    email_min_severity: AlertSeverity
    email_batch_minutes: int
    email_include_snapshot: bool

    # Telegram
    telegram_enabled: bool
    telegram_chat_ids: list[str]
    telegram_min_severity: AlertSeverity
    telegram_silent: bool
    telegram_disable_preview: bool

    # Tells the UI whether a real bot token is saved (vs the seed placeholder).
    telegram_token_set: bool

    created_at: datetime
    updated_at: datetime


class NotificationSettingsUpdate(BaseModel):
    # Global
    master_enabled: bool | None = None
    silent_hours_enabled: bool | None = None
    silent_hours_start: str | None = Field(default=None, pattern=_TIME_RE)
    silent_hours_end: str | None = Field(default=None, pattern=_TIME_RE)

    # Push
    push_enabled: bool | None = None
    push_sound: str | None = Field(default=None, max_length=32)
    push_vibrate: bool | None = None
    push_min_severity: AlertSeverity | None = None
    push_show_preview: bool | None = None

    # Email
    email_enabled: bool | None = None
    email_recipients: list[EmailStr] | None = None
    email_subject_prefix: str | None = Field(default=None, max_length=64)
    email_min_severity: AlertSeverity | None = None
    email_batch_minutes: int | None = Field(default=None, ge=0, le=1440)
    email_include_snapshot: bool | None = None

    # Telegram
    telegram_enabled: bool | None = None
    telegram_bot_token: str | None = Field(
        default=None, min_length=20, max_length=128, repr=False,
    )
    telegram_chat_ids: list[str] | None = None
    telegram_min_severity: AlertSeverity | None = None
    telegram_silent: bool | None = None
    telegram_disable_preview: bool | None = None
