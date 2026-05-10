"""Detector factory — register new model families here."""

from __future__ import annotations

from functools import lru_cache

from app.detectors import Detector
from app.detectors.yolo import YOLODetector


@lru_cache
def get_detector() -> Detector:
    """Return a singleton detector instance."""
    return YOLODetector()
