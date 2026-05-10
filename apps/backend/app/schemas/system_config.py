"""System config schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.models.system_config import StorageMode


class SystemConfigPublic(BaseModel):
    """Response shape — never includes the raw S3 secret."""

    storage_mode: StorageMode
    local_storage_path: str
    s3_endpoint_url: str | None = None
    s3_region: str
    s3_bucket: str
    s3_access_key: str
    s3_use_ssl: bool
    s3_signed_url_ttl: int
    retention_days: int
    detection_classes: list[str] = Field(default_factory=list)

    # Surfaces whether a real secret has been set (vs the seed placeholder).
    s3_secret_set: bool

    created_at: datetime
    updated_at: datetime


class SystemConfigUpdate(BaseModel):
    storage_mode: StorageMode | None = None
    local_storage_path: str | None = Field(default=None, min_length=1, max_length=512)
    s3_endpoint_url: str | None = Field(default=None, max_length=512)
    s3_region: str | None = Field(default=None, max_length=64)
    s3_bucket: str | None = Field(default=None, min_length=1, max_length=255)
    s3_access_key: str | None = Field(default=None, min_length=1, max_length=255)
    s3_secret_key: str | None = Field(default=None, min_length=8, max_length=512, repr=False)
    s3_use_ssl: bool | None = None
    s3_signed_url_ttl: int | None = Field(default=None, ge=60, le=86400)
    retention_days: int | None = Field(default=None, ge=1, le=3650)
    # No length cap so admins can enable all 80 COCO classes if they want.
    detection_classes: list[str] | None = None


class AppVersion(BaseModel):
    name: str
    version: str
    environment: str
