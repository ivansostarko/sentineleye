"""Notification settings: per-channel config persisted in DB.

Single-row table (CHECK id=1) — same pattern as system_config. Bot token is
Fernet-encrypted at rest via app.services.crypto. Seed is idempotent so the
migration can be re-applied safely.

Revision ID: 0008_notif
Revises: 0007_alerts
Create Date: 2026-05-10
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0008_notif"
down_revision = "0007_alerts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "notification_settings",
        sa.Column("id", sa.Integer(), primary_key=True),

        # ── Global ──
        sa.Column("master_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("silent_hours_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        # Stored as ISO HH:MM strings — easy to render and compare.
        sa.Column("silent_hours_start", sa.String(5), nullable=False, server_default="22:00"),
        sa.Column("silent_hours_end", sa.String(5), nullable=False, server_default="07:00"),

        # ── Push (in-app + future web/mobile push) ──
        sa.Column("push_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("push_sound", sa.String(32), nullable=False, server_default="default"),
        sa.Column("push_vibrate", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "push_min_severity",
            postgresql.ENUM(name="alert_severity", create_type=False),
            nullable=False,
            server_default="low",
        ),
        sa.Column("push_show_preview", sa.Boolean(), nullable=False, server_default=sa.text("true")),

        # ── Email ──
        sa.Column("email_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column(
            "email_recipients",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("email_subject_prefix", sa.String(64), nullable=False, server_default="[SentinelEye]"),
        sa.Column(
            "email_min_severity",
            postgresql.ENUM(name="alert_severity", create_type=False),
            nullable=False,
            server_default="medium",
        ),
        sa.Column(
            "email_batch_minutes",
            sa.Integer(),
            nullable=False,
            server_default="0",  # 0 = realtime, otherwise digest every N min
        ),
        sa.Column("email_include_snapshot", sa.Boolean(), nullable=False, server_default=sa.text("true")),

        # ── Telegram ──
        sa.Column("telegram_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        # Fernet-encrypted; seed inserts a placeholder, real value set via PATCH.
        sa.Column("telegram_bot_token_enc", sa.Text(), nullable=False, server_default="__seed_placeholder__"),
        sa.Column(
            "telegram_chat_ids",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "telegram_min_severity",
            postgresql.ENUM(name="alert_severity", create_type=False),
            nullable=False,
            server_default="medium",
        ),
        sa.Column("telegram_silent", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("telegram_disable_preview", sa.Boolean(), nullable=False, server_default=sa.text("false")),

        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),

        sa.CheckConstraint("id = 1", name="ck_notification_settings_singleton"),
    )

    # Seed the singleton row. All defaults from the schema apply automatically.
    op.execute(
        "INSERT INTO notification_settings (id) VALUES (1) ON CONFLICT (id) DO NOTHING"
    )


def downgrade() -> None:
    op.drop_table("notification_settings")
