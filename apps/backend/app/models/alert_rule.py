"""Alert rules — declarative trigger configurations."""

from __future__ import annotations

import enum
from datetime import datetime
from uuid import UUID

from sqlalchemy import JSON, Boolean, DateTime, Enum, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class AlertTrigger(str, enum.Enum):
    OBJECT_DETECTED = "object_detected"
    MOTION = "motion"
    INTRUSION = "intrusion"
    LINE_CROSSED = "line_crossed"
    CAMERA_OFFLINE = "camera_offline"
    STORAGE_FAILURE = "storage_failure"


class AlertChannel(str, enum.Enum):
    EMAIL = "email"
    TELEGRAM = "telegram"
    WEBHOOK = "webhook"
    PUSH = "push"
    REALTIME = "realtime"  # in-app via WS


class AlertSeverity(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


def _enum_values(enum_cls):
    return [m.value for m in enum_cls]


class AlertRule(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "alert_rules"

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Optional camera scope; null = applies to all
    camera_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("cameras.id", ondelete="CASCADE"),
    )

    trigger: Mapped[AlertTrigger] = mapped_column(
        Enum(
            AlertTrigger,
            name="alert_trigger",
            values_callable=lambda e: _enum_values(e),
        ),
        nullable=False,
    )
    severity: Mapped[AlertSeverity] = mapped_column(
        Enum(
            AlertSeverity,
            name="alert_severity",
            values_callable=lambda e: _enum_values(e),
        ),
        default=AlertSeverity.MEDIUM,
        nullable=False,
    )

    # COCO class allowlist for OBJECT_DETECTED triggers. Empty = all classes.
    object_classes: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    min_confidence: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)

    # Trigger-specific extras (e.g. line_crossed coords, intrusion zone polygon).
    parameters: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    channels: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    cooldown_seconds: Mapped[float] = mapped_column(Float, default=60.0, nullable=False)

    # Tracks the most recent fire time so the service can enforce cooldown
    # without reaching for Redis. Atomic UPDATE..WHERE last_fired_at < cutoff
    # makes concurrent fires safe.
    last_fired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
