"""Notification settings — single-row config for all notification channels.

Same pattern as `system_config`: one row, edited via PATCH, encrypted secrets.
"""

from __future__ import annotations

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Enum,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin
from app.models.alert_rule import AlertSeverity


def _sev_values(enum_cls):
    return [m.value for m in enum_cls]


class NotificationSettings(Base, TimestampMixin):
    __tablename__ = "notification_settings"
    __table_args__ = (
        CheckConstraint("id = 1", name="ck_notification_settings_singleton"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)

    # ── Global ──────────────────────────────────────────────────────────
    master_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    silent_hours_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    silent_hours_start: Mapped[str] = mapped_column(String(5), nullable=False, default="22:00")
    silent_hours_end: Mapped[str] = mapped_column(String(5), nullable=False, default="07:00")

    # ── Push ────────────────────────────────────────────────────────────
    push_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    push_sound: Mapped[str] = mapped_column(String(32), nullable=False, default="default")
    push_vibrate: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    push_min_severity: Mapped[AlertSeverity] = mapped_column(
        Enum(AlertSeverity, name="alert_severity", values_callable=_sev_values),
        nullable=False,
        default=AlertSeverity.LOW,
    )
    push_show_preview: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # ── Email ───────────────────────────────────────────────────────────
    email_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    email_recipients: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    email_subject_prefix: Mapped[str] = mapped_column(
        String(64), nullable=False, default="[SentinelEye]",
    )
    email_min_severity: Mapped[AlertSeverity] = mapped_column(
        Enum(AlertSeverity, name="alert_severity", values_callable=_sev_values),
        nullable=False,
        default=AlertSeverity.MEDIUM,
    )
    email_batch_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    email_include_snapshot: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # ── Telegram ────────────────────────────────────────────────────────
    telegram_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    telegram_bot_token_enc: Mapped[str] = mapped_column(Text, nullable=False)
    telegram_chat_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    telegram_min_severity: Mapped[AlertSeverity] = mapped_column(
        Enum(AlertSeverity, name="alert_severity", values_callable=_sev_values),
        nullable=False,
        default=AlertSeverity.MEDIUM,
    )
    telegram_silent: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    telegram_disable_preview: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
