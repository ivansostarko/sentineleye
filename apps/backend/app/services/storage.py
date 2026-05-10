"""Storage abstraction for recordings & snapshots (local + S3-compatible)."""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import BinaryIO

import boto3
from botocore.client import Config

from app.core.config import get_settings
from app.core.logging import get_logger

log = get_logger(__name__)
settings = get_settings()


class StorageBackend(ABC):
    @abstractmethod
    async def put(self, key: str, body: BinaryIO | bytes, *, content_type: str | None = None) -> str: ...

    @abstractmethod
    async def signed_url(self, key: str, *, ttl_seconds: int | None = None) -> str: ...

    @abstractmethod
    async def delete(self, key: str) -> None: ...


class LocalStorage(StorageBackend):
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    async def put(self, key: str, body: BinaryIO | bytes, *, content_type: str | None = None) -> str:
        path = self.root / key
        path.parent.mkdir(parents=True, exist_ok=True)
        data = body.read() if hasattr(body, "read") else body  # type: ignore[union-attr]
        path.write_bytes(data)  # type: ignore[arg-type]
        return str(path)

    async def signed_url(self, key: str, *, ttl_seconds: int | None = None) -> str:
        # Local files are served by the backend's /media route.
        return f"{settings.backend_public_url}/api/v1/media/{key}"

    async def delete(self, key: str) -> None:
        path = self.root / key
        if path.exists():
            path.unlink()


class S3Storage(StorageBackend):
    def __init__(self) -> None:
        self.bucket = settings.s3_bucket
        self.client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url,
            region_name=settings.s3_region,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
            use_ssl=settings.s3_use_ssl,
            config=Config(signature_version="s3v4"),
        )

    async def put(self, key: str, body: BinaryIO | bytes, *, content_type: str | None = None) -> str:
        extra: dict[str, str] = {}
        if content_type:
            extra["ContentType"] = content_type
        self.client.put_object(Bucket=self.bucket, Key=key, Body=body, **extra)
        return f"s3://{self.bucket}/{key}"

    async def signed_url(self, key: str, *, ttl_seconds: int | None = None) -> str:
        return self.client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": key},
            ExpiresIn=ttl_seconds or settings.s3_signed_url_ttl,
        )

    async def delete(self, key: str) -> None:
        self.client.delete_object(Bucket=self.bucket, Key=key)


def get_storage() -> StorageBackend:
    """Pick the active storage backend per settings."""
    if settings.storage_mode == "local":
        return LocalStorage(settings.local_storage_path)
    return S3Storage()


def make_recording_key(camera_id, started_at: datetime, ext: str = "mp4") -> str:
    """Build a deterministic, sortable storage key."""
    d = started_at.strftime("%Y/%m/%d")
    ts = started_at.strftime("%Y%m%dT%H%M%SZ")
    return os.path.join("recordings", str(camera_id), d, f"{ts}.{ext}")
