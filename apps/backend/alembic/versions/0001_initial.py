"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2025-01-01 00:00:00
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("full_name", sa.String(255)),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column(
            "role",
            sa.Enum("admin", "operator", "viewer", name="user_role"),
            nullable=False,
            server_default="viewer",
        ),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "cameras",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("location", sa.String(255)),
        sa.Column(
            "protocol",
            sa.Enum("rtsp", "rtmp", "onvif", "usb", "http", "mjpeg", name="camera_protocol"),
            nullable=False,
        ),
        sa.Column("url", sa.String(1024), nullable=False),
        sa.Column("username", sa.String(255)),
        sa.Column("password", sa.String(255)),
        sa.Column("enabled", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("record_continuous", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("detection_enabled", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("target_fps", sa.Integer, nullable=False, server_default="15"),
        sa.Column("bitrate_kbps", sa.Integer),
        sa.Column(
            "status",
            sa.Enum("online", "offline", "degraded", "unknown", name="camera_status"),
            nullable=False,
            server_default="unknown",
        ),
        sa.Column("config", postgresql.JSON, nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "recordings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("camera_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("cameras.id", ondelete="CASCADE"), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True)),
        sa.Column("duration_seconds", sa.Float),
        sa.Column("storage_backend", sa.Enum("local", "s3", name="storage_backend"), nullable=False),
        sa.Column("storage_key", sa.String(1024), nullable=False),
        sa.Column("bytes_size", sa.BigInteger),
        sa.Column("codec", sa.String(32)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_recordings_camera_started", "recordings", ["camera_id", "started_at"])

    op.create_table(
        "detection_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("camera_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("cameras.id", ondelete="CASCADE"), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("object_class", sa.String(64), nullable=False),
        sa.Column("confidence", sa.Float, nullable=False),
        sa.Column("track_id", sa.Integer),
        sa.Column("bbox", postgresql.JSON, nullable=False),
        sa.Column("snapshot_key", sa.String(512)),
        sa.Column("recording_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("recordings.id", ondelete="SET NULL")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_events_camera_time", "detection_events", ["camera_id", "occurred_at"])
    op.create_index("ix_events_class_time", "detection_events", ["object_class", "occurred_at"])
    op.create_index("ix_detection_events_occurred_at", "detection_events", ["occurred_at"])

    op.create_table(
        "alert_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("enabled", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("camera_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("cameras.id", ondelete="CASCADE")),
        sa.Column(
            "trigger",
            sa.Enum(
                "object_detected",
                "motion",
                "intrusion",
                "line_crossed",
                "camera_offline",
                "storage_failure",
                name="alert_trigger",
            ),
            nullable=False,
        ),
        sa.Column("parameters", postgresql.JSON, nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("channels", postgresql.JSON, nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("cooldown_seconds", sa.Float, nullable=False, server_default="60"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("alert_rules")
    op.drop_index("ix_detection_events_occurred_at", table_name="detection_events")
    op.drop_index("ix_events_class_time", table_name="detection_events")
    op.drop_index("ix_events_camera_time", table_name="detection_events")
    op.drop_table("detection_events")
    op.drop_index("ix_recordings_camera_started", table_name="recordings")
    op.drop_table("recordings")
    op.drop_table("cameras")
    op.drop_table("users")
    for enum_name in (
        "alert_trigger",
        "storage_backend",
        "camera_status",
        "camera_protocol",
        "user_role",
    ):
        op.execute(f"DROP TYPE IF EXISTS {enum_name}")
