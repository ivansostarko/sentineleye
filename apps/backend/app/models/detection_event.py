"""Detection events emitted by the AI engine."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class DetectionEvent(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "detection_events"
    __table_args__ = (
        Index("ix_events_camera_time", "camera_id", "occurred_at"),
        Index("ix_events_class_time", "object_class", "occurred_at"),
    )

    camera_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("cameras.id", ondelete="CASCADE"),
        nullable=False,
    )
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    object_class: Mapped[str] = mapped_column(String(64), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    track_id: Mapped[int | None] = mapped_column(Integer)

    # Bounding box in normalized coords [0,1]: {"x":..,"y":..,"w":..,"h":..}
    bbox: Mapped[dict] = mapped_column(JSON, nullable=False)

    snapshot_key: Mapped[str | None] = mapped_column(String(512))  # S3 key or local path
    recording_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("recordings.id", ondelete="SET NULL"),
    )
