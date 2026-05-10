"""System-wide configuration (single-row table).

Storage backend selection + per-backend settings, persisted in the DB so admins
can edit them at runtime without an env-var redeploy. Constrained to a single
row via `CHECK (id = 1)`.
"""

from __future__ import annotations

import enum

from sqlalchemy import Boolean, CheckConstraint, Enum, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class StorageMode(str, enum.Enum):
    LOCAL = "local"
    S3 = "s3"
    HYBRID = "hybrid"


class SystemConfig(Base, TimestampMixin):
    __tablename__ = "system_config"
    __table_args__ = (CheckConstraint("id = 1", name="ck_system_config_singleton"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    storage_mode: Mapped[StorageMode] = mapped_column(
        Enum(
            StorageMode,
            name="storage_mode",
            values_callable=lambda enum_cls: [m.value for m in enum_cls],
        ),
        nullable=False,
        default=StorageMode.HYBRID,
    )

    local_storage_path: Mapped[str] = mapped_column(
        String(512), nullable=False, default="/data/recordings"
    )

    s3_endpoint_url: Mapped[str | None] = mapped_column(String(512))
    s3_region: Mapped[str] = mapped_column(String(64), nullable=False, default="us-east-1")
    s3_bucket: Mapped[str] = mapped_column(
        String(255), nullable=False, default="sentineleye-recordings"
    )
    s3_access_key: Mapped[str] = mapped_column(String(255), nullable=False, default="minioadmin")
    s3_secret_key_enc: Mapped[str] = mapped_column(Text, nullable=False)
    s3_use_ssl: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    s3_signed_url_ttl: Mapped[int] = mapped_column(Integer, nullable=False, default=3600)

    retention_days: Mapped[int] = mapped_column(Integer, nullable=False, default=14)
