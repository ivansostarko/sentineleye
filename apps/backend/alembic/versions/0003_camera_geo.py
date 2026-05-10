"""Add latitude/longitude to cameras for map display.

Revision ID: 0003_geo
Revises: 0002_tuya
Create Date: 2026-05-10
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "0003_geo"
down_revision = "0002_tuya"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "cameras",
        sa.Column("latitude", sa.Float(), nullable=True),
    )
    op.add_column(
        "cameras",
        sa.Column("longitude", sa.Float(), nullable=True),
    )
    # Partial index — most cameras will have coords, but skip ones that don't
    # so the index stays compact.
    op.create_index(
        "ix_cameras_geo",
        "cameras",
        ["latitude", "longitude"],
        postgresql_where=sa.text("latitude IS NOT NULL AND longitude IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_cameras_geo", table_name="cameras")
    op.drop_column("cameras", "longitude")
    op.drop_column("cameras", "latitude")
