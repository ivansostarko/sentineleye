"""Cloud integration request/response schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.cloud_integration import CloudProvider

# Tuya regional endpoints. Pick the one closest to your cameras.
TUYA_REGIONS = ("eu", "us", "cn", "in")
_REGION_PATTERN = r"^(eu|us|cn|in)$"


class CloudIntegrationBase(BaseModel):
    provider: CloudProvider
    name: str = Field(min_length=1, max_length=120)
    region: str = Field(pattern=_REGION_PATTERN)
    enabled: bool = True


class CloudIntegrationCreate(CloudIntegrationBase):
    access_id: str = Field(min_length=8, max_length=128)
    access_secret: str = Field(min_length=16, max_length=128, repr=False)


class CloudIntegrationUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    region: str | None = Field(default=None, pattern=_REGION_PATTERN)
    enabled: bool | None = None
    access_id: str | None = Field(default=None, min_length=8, max_length=128)
    access_secret: str | None = Field(default=None, min_length=16, max_length=128, repr=False)


class CloudIntegrationPublic(CloudIntegrationBase):
    """Response shape — never includes raw secrets."""

    id: UUID
    created_at: datetime
    updated_at: datetime
