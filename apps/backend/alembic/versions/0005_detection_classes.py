"""Add detection_classes allowlist to system_config.

Stores which COCO-80 class names YOLO should emit detection events for. The
AI engine reads this on pipeline start so we don't pollute the events table
with detections we don't care about (cup, knife, toaster, ...).

Revision ID: 0005_classes
Revises: 0004_sysconf
Create Date: 2026-05-10
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0005_classes"
down_revision = "0004_sysconf"
branch_labels = None
depends_on = None


# Sane surveillance defaults — covers the common "did a person/vehicle/pet
# cross the frame" use cases without flooding events with kitchen objects.
_DEFAULT_CLASSES = [
    "person",
    "bicycle",
    "car",
    "motorcycle",
    "bus",
    "truck",
    "dog",
    "cat",
]


def upgrade() -> None:
    op.add_column(
        "system_config",
        sa.Column(
            "detection_classes",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text(f"'{_classes_to_json(_DEFAULT_CLASSES)}'::jsonb"),
        ),
    )


def downgrade() -> None:
    op.drop_column("system_config", "detection_classes")


def _classes_to_json(classes: list[str]) -> str:
    inner = ",".join(f'"{c}"' for c in classes)
    return f"[{inner}]"
