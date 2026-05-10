"""Alert history + extended rule metadata.

Adds severity / description / class-filter / last-fired columns to alert_rules
so the UI can render rich cards and the firing logic can enforce cooldowns
without Redis.

Creates alert_events as the immutable history of every fired alert. Indexed
on (occurred_at DESC) for the activity feed and on (rule_id, occurred_at)
for per-rule timelines.

Seeds four sensible default rules so a fresh deployment has something useful.

Revision ID: 0007_alerts
Revises: 0006_pinord
Create Date: 2026-05-10
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0007_alerts"
down_revision = "0006_pinord"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1) Severity enum, idempotent.
    op.execute(
        """
        DO $$ BEGIN
            CREATE TYPE alert_severity AS ENUM ('low','medium','high','critical');
        EXCEPTION WHEN duplicate_object THEN NULL; END $$;
        """
    )

    # 2) Extend alert_rules with the new columns.
    op.add_column(
        "alert_rules",
        sa.Column("description", sa.String(500), nullable=True),
    )
    op.add_column(
        "alert_rules",
        sa.Column(
            "severity",
            postgresql.ENUM(
                "low", "medium", "high", "critical",
                name="alert_severity", create_type=False,
            ),
            nullable=False,
            server_default="medium",
        ),
    )
    op.add_column(
        "alert_rules",
        sa.Column(
            "object_classes",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.add_column(
        "alert_rules",
        sa.Column(
            "min_confidence",
            sa.Float(),
            nullable=False,
            server_default="0.5",
        ),
    )
    op.add_column(
        "alert_rules",
        sa.Column("last_fired_at", sa.DateTime(timezone=True), nullable=True),
    )

    # 3) alert_events — immutable history.
    op.create_table(
        "alert_events",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "rule_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("alert_rules.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "camera_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("cameras.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "detection_event_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("detection_events.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column(
            "severity",
            postgresql.ENUM(name="alert_severity", create_type=False),
            nullable=False,
        ),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column(
            "context",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "channels_dispatched",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "acknowledged_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_alert_events_occurred_at",
        "alert_events",
        [sa.text("occurred_at DESC")],
    )
    op.create_index(
        "ix_alert_events_rule_occurred",
        "alert_events",
        ["rule_id", sa.text("occurred_at DESC")],
    )
    op.create_index(
        "ix_alert_events_unack",
        "alert_events",
        ["acknowledged_at"],
        postgresql_where=sa.text("acknowledged_at IS NULL"),
    )

    # 4) Seed four sensible default rules — all global (camera_id NULL).
    op.execute(
        """
        INSERT INTO alert_rules (
            id, name, description, enabled, camera_id, trigger,
            severity, object_classes, min_confidence,
            parameters, channels, cooldown_seconds
        ) VALUES
        (gen_random_uuid(), 'Person detected',
         'Fires whenever YOLO detects a person on any camera.',
         true, NULL, 'object_detected', 'high',
         '["person"]'::jsonb, 0.55,
         '{}'::jsonb, '["realtime","email"]'::jsonb, 60),
        (gen_random_uuid(), 'Vehicle detected',
         'Fires for cars, trucks, motorcycles or buses.',
         true, NULL, 'object_detected', 'medium',
         '["car","truck","motorcycle","bus"]'::jsonb, 0.5,
         '{}'::jsonb, '["realtime"]'::jsonb, 120),
        (gen_random_uuid(), 'Pet on camera',
         'Fires when a dog or cat is seen — useful for keeping an eye on indoor cams.',
         false, NULL, 'object_detected', 'low',
         '["dog","cat"]'::jsonb, 0.5,
         '{}'::jsonb, '["realtime"]'::jsonb, 300),
        (gen_random_uuid(), 'Camera offline',
         'Notify when a camera health check fails for more than one tick.',
         true, NULL, 'camera_offline', 'critical',
         '[]'::jsonb, 0.0,
         '{"after_seconds": 120}'::jsonb, '["realtime","email","telegram"]'::jsonb, 300)
        ON CONFLICT DO NOTHING
        """
    )


def downgrade() -> None:
    op.drop_index("ix_alert_events_unack", table_name="alert_events")
    op.drop_index("ix_alert_events_rule_occurred", table_name="alert_events")
    op.drop_index("ix_alert_events_occurred_at", table_name="alert_events")
    op.drop_table("alert_events")
    op.drop_column("alert_rules", "last_fired_at")
    op.drop_column("alert_rules", "min_confidence")
    op.drop_column("alert_rules", "object_classes")
    op.drop_column("alert_rules", "severity")
    op.drop_column("alert_rules", "description")
    op.execute("DROP TYPE IF EXISTS alert_severity")
