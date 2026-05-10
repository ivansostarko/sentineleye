"""Camera pin-to-dashboard + display order.

Lets users dock a camera onto the dashboard widget grid and reorder cards on
the cameras screen via drag-and-drop. Both columns are nullable / default-able
so existing rows continue to work without backfill.

Revision ID: 0006_pinord
Revises: 0005_classes
Create Date: 2026-05-10
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "0006_pinord"
down_revision = "0005_classes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "cameras",
        sa.Column(
            "pinned_to_dashboard",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "cameras",
        sa.Column(
            "display_order",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    # Ordering uses (display_order ASC, created_at ASC) — index supports it.
    op.create_index(
        "ix_cameras_display_order",
        "cameras",
        ["display_order", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_cameras_display_order", table_name="cameras")
    op.drop_column("cameras", "display_order")
    op.drop_column("cameras", "pinned_to_dashboard")
