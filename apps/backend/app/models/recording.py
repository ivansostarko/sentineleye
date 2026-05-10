"""Recording / video segment metadata."""

from __future__ import annotations

import enum
from datetime import datetime
from uuid import UUID

from sqlalchemy import BigInteger, DateTime, Enum, Float, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class StorageBackend(str, enum.Enum):
    LOCAL = "local"
    S3 = "s3"


class Recording(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "recordings"
    __table_args__ = (
        Index("ix_recordings_camera_started", "camera_id", "started_at"),
    )

    camera_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("cameras.id", ondelete="CASCADE"),
        nullable=False,
    )

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_seconds: Mapped[float | None] = mapped_column(Float)

    storage_backend: Mapped[StorageBackend] = mapped_column(
        Enum(StorageBackend, name="storage_backend"),
        nullable=False,
    )
    storage_key: Mapped[str] = mapped_column(String(1024), nullable=False)
    bytes_size: Mapped[int | None] = mapped_column(BigInteger)
    codec: Mapped[str | None] = mapped_column(String(32))
