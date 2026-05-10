"""Multi-object trackers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.detectors import Detection


@dataclass
class Track:
    track_id: int
    detection: Detection


class Tracker(ABC):
    @abstractmethod
    def update(self, detections: list[Detection], frame_idx: int) -> list[Track]: ...
