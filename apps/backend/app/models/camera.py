"""Camera configuration."""

from __future__ import annotations

import enum

from sqlalchemy import JSON, Boolean, Enum, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class CameraProtocol(str, enum.Enum):
    RTSP = "rtsp"
    RTMP = "rtmp"
    ONVIF = "onvif"
    USB = "usb"
    HTTP = "http"
    MJPEG = "mjpeg"


class CameraStatus(str, enum.Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"


class Camera(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "cameras"

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    location: Mapped[str | None] = mapped_column(String(255))
    protocol: Mapped[CameraProtocol] = mapped_column(
        Enum(CameraProtocol, name="camera_protocol"),
        nullable=False,
    )
    url: Mapped[str] = mapped_column(String(1024), nullable=False)
    username: Mapped[str | None] = mapped_column(String(255))
    password: Mapped[str | None] = mapped_column(String(255))  # consider envelope-encrypting

    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    record_continuous: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    detection_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    target_fps: Mapped[int] = mapped_column(Integer, default=15, nullable=False)
    bitrate_kbps: Mapped[int | None] = mapped_column(Integer)

    status: Mapped[CameraStatus] = mapped_column(
        Enum(CameraStatus, name="camera_status"),
        default=CameraStatus.UNKNOWN,
        nullable=False,
    )

    # Free-form extras: zones, line-crossing definitions, vendor metadata
    config: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
