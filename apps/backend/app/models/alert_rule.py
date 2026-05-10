"""Alert rules — declarative trigger configurations."""

from __future__ import annotations

import enum
from uuid import UUID

from sqlalchemy import JSON, Boolean, Enum, Float, ForeignKey, String
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


class AlertRule(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "alert_rules"

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Optional camera scope; null = applies to all
    camera_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("cameras.id", ondelete="CASCADE"),
    )

    trigger: Mapped[AlertTrigger] = mapped_column(
        Enum(AlertTrigger, name="alert_trigger"),
        nullable=False,
    )
    # Trigger-specific params, e.g. {"classes": ["person"], "min_confidence": 0.6}
    parameters: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    channels: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    cooldown_seconds: Mapped[float] = mapped_column(Float, default=60.0, nullable=False)
