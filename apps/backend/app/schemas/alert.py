"""Alert rule schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.alert_rule import AlertChannel, AlertTrigger


class AlertRuleBase(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    enabled: bool = True
    camera_id: UUID | None = None
    trigger: AlertTrigger
    parameters: dict[str, Any] = Field(default_factory=dict)
    channels: list[AlertChannel]
    cooldown_seconds: float = Field(default=60.0, ge=0)


class AlertRuleCreate(AlertRuleBase):
    pass


class AlertRuleUpdate(BaseModel):
    name: str | None = None
    enabled: bool | None = None
    parameters: dict[str, Any] | None = None
    channels: list[AlertChannel] | None = None
    cooldown_seconds: float | None = Field(default=None, ge=0)


class AlertRulePublic(AlertRuleBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
