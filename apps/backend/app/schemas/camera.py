"""Camera schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl

from app.models.camera import CameraProtocol, CameraStatus


class CameraBase(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    location: str | None = None
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    protocol: CameraProtocol
    url: str = Field(min_length=1, max_length=1024)
    username: str | None = None
    password: str | None = Field(default=None, repr=False)
    enabled: bool = True
    record_continuous: bool = True
    detection_enabled: bool = True
    target_fps: int = Field(default=15, ge=1, le=60)
    bitrate_kbps: int | None = Field(default=None, ge=64, le=50000)
    pinned_to_dashboard: bool = False
    display_order: int = 0
    config: dict[str, Any] = Field(default_factory=dict)


class CameraCreate(CameraBase):
    pass


class CameraUpdate(BaseModel):
    name: str | None = None
    location: str | None = None
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    url: str | None = Field(default=None, min_length=1, max_length=1024)
    username: str | None = None
    password: str | None = Field(default=None, repr=False)
    enabled: bool | None = None
    record_continuous: bool | None = None
    detection_enabled: bool | None = None
    target_fps: int | None = Field(default=None, ge=1, le=60)
    bitrate_kbps: int | None = Field(default=None, ge=64, le=50000)
    pinned_to_dashboard: bool | None = None
    display_order: int | None = None
    config: dict[str, Any] | None = None


class CameraPublic(CameraBase):
    id: UUID
    status: CameraStatus
    created_at: datetime
    updated_at: datetime


class CameraSnapshot(BaseModel):
    camera_id: UUID
    captured_at: datetime
    url: HttpUrl | str
