"""Cross-service Pydantic schemas (single source of truth)."""

from sentineleye_schemas.events import (
    BoundingBox,
    DetectionEventEnvelope,
)

__all__ = ["BoundingBox", "DetectionEventEnvelope"]
