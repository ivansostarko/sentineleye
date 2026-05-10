"""System configuration: single-row table seeded from env defaults.

Revision ID: 0004_sysconf
Revises: 0003_geo
Create Date: 2026-05-10
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0004_sysconf"
down_revision = "0003_geo"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        DO $$ BEGIN
            CREATE TYPE storage_mode AS ENUM ('local', 's3', 'hybrid');
        EXCEPTION
            WHEN duplicate_object THEN NULL;
        END $$;
        """
    )

    op.create_table(
        "system_config",
        sa.Column(
            "id",
            sa.Integer(),
            primary_key=True,
            # Constrained-to-single-row pattern: id is always 1.
        ),
        sa.Column(
            "storage_mode",
            postgresql.ENUM("local", "s3", "hybrid", name="storage_mode", create_type=False),
            nullable=False,
            server_default=sa.text("'hybrid'"),
        ),
        sa.Column("local_storage_path", sa.String(512), nullable=False, server_default="/data/recordings"),
        sa.Column("s3_endpoint_url", sa.String(512), nullable=True),
        sa.Column("s3_region", sa.String(64), nullable=False, server_default="us-east-1"),
        sa.Column("s3_bucket", sa.String(255), nullable=False, server_default="sentineleye-recordings"),
        sa.Column("s3_access_key", sa.String(255), nullable=False, server_default="minioadmin"),
        sa.Column("s3_secret_key_enc", sa.Text(), nullable=False),
        sa.Column("s3_use_ssl", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("s3_signed_url_ttl", sa.Integer(), nullable=False, server_default="3600"),
        sa.Column("retention_days", sa.Integer(), nullable=False, server_default="14"),
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
        sa.CheckConstraint("id = 1", name="ck_system_config_singleton"),
    )

    # Seed the single row using the same defaults as app/core/config.py.
    # The s3_secret_key is Fernet-encrypted by app.services.crypto in the
    # service layer; for the seed we store an obviously-placeholder string.
    # The placeholder is invalid Fernet — first PATCH from the UI will replace
    # it with a properly-encrypted secret. Until then the service treats a
    # decryption failure as "use the env default" so things still work.
    op.execute(
        """
        INSERT INTO system_config (
            id, storage_mode, local_storage_path,
            s3_endpoint_url, s3_region, s3_bucket, s3_access_key,
            s3_secret_key_enc, s3_use_ssl, s3_signed_url_ttl, retention_days
        ) VALUES (
            1, 'hybrid', '/data/recordings',
            NULL, 'us-east-1', 'sentineleye-recordings', 'minioadmin',
            '__seed_placeholder__', false, 3600, 14
        )
        ON CONFLICT (id) DO NOTHING
        """
    )


def downgrade() -> None:
    op.drop_table("system_config")
    op.execute("DROP TYPE IF EXISTS storage_mode")
