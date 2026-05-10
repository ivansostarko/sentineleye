"""Alert rule + alert event schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.alert_rule import AlertChannel, AlertSeverity, AlertTrigger


# ─── Rules ─────────────────────────────────────────────────────────────

class AlertRuleBase(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    enabled: bool = True
    camera_id: UUID | None = None
    trigger: AlertTrigger
    severity: AlertSeverity = AlertSeverity.MEDIUM
    object_classes: list[str] = Field(default_factory=list)
    min_confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    parameters: dict[str, Any] = Field(default_factory=dict)
    channels: list[AlertChannel]
    cooldown_seconds: float = Field(default=60.0, ge=0)


class AlertRuleCreate(AlertRuleBase):
    pass


class AlertRuleUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    enabled: bool | None = None
    camera_id: UUID | None = None
    severity: AlertSeverity | None = None
    object_classes: list[str] | None = None
    min_confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    parameters: dict[str, Any] | None = None
    channels: list[AlertChannel] | None = None
    cooldown_seconds: float | None = Field(default=None, ge=0)


class AlertRulePublic(AlertRuleBase):
    id: UUID
    last_fired_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


# ─── Events (history) ──────────────────────────────────────────────────

class DispatchedChannel(BaseModel):
    channel: AlertChannel
    success: bool
    detail: str | None = None


class AlertEventPublic(BaseModel):
    id: UUID
    rule_id: UUID
    camera_id: UUID | None = None
    detection_event_id: UUID | None = None
    occurred_at: datetime
    severity: AlertSeverity
    title: str
    body: str | None = None
    context: dict[str, Any] = Field(default_factory=dict)
    channels_dispatched: list[DispatchedChannel] = Field(default_factory=list)
    acknowledged_at: datetime | None = None
    acknowledged_by: UUID | None = None
