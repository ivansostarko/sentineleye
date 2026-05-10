"""Tuya integration: add 'tuya' protocol + cloud_integrations table.

Revision ID: 0002_tuya
Revises: 0001_initial
Create Date: 2026-05-10
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0002_tuya"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1) Extend the existing camera_protocol enum (PG 12+ supports this in tx).
    op.execute("ALTER TYPE camera_protocol ADD VALUE IF NOT EXISTS 'tuya'")

    # 2) Create the cloud_provider enum idempotently. We do this manually with
    #    a DO-block so re-running after a partial migration doesn't blow up.
    op.execute(
        """
        DO $$ BEGIN
            CREATE TYPE cloud_provider AS ENUM ('tuya');
        EXCEPTION
            WHEN duplicate_object THEN NULL;
        END $$;
        """
    )

    # 3) cloud_integrations: stores credentials for external cloud providers.
    #    Secrets are Fernet-encrypted at rest — see app.services.crypto.
    #    Use postgresql.ENUM(..., create_type=False) explicitly because the
    #    dialect-agnostic sa.Enum() ignores create_type and would re-CREATE
    #    the type we just made.
    op.create_table(
        "cloud_integrations",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "provider",
            postgresql.ENUM("tuya", name="cloud_provider", create_type=False),
            nullable=False,
        ),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("region", sa.String(8), nullable=False),
        sa.Column("access_id_enc", sa.Text(), nullable=False),
        sa.Column("access_secret_enc", sa.Text(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "ix_cloud_integrations_provider_enabled",
        "cloud_integrations",
        ["provider", "enabled"],
    )


def downgrade() -> None:
    op.drop_index("ix_cloud_integrations_provider_enabled", table_name="cloud_integrations")
    op.drop_table("cloud_integrations")
    op.execute("DROP TYPE IF EXISTS cloud_provider")
    # Note: removing a value from a Postgres enum is not safely reversible
    # without recreating the type and updating every dependent column.
    # The 'tuya' value is left behind on downgrade — harmless if unused.
