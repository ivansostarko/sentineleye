"""Object detector implementations."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

import numpy as np


@dataclass
class Detection:
    """One detected object in image coordinates."""

    class_id: int
    class_name: str
    confidence: float
    # Pixel-space xyxy (x1, y1, x2, y2)
    xyxy: tuple[float, float, float, float]

    def normalized(self, width: int, height: int) -> dict[str, float]:
        """Return bbox in [0,1]^4 with x/y/w/h."""
        x1, y1, x2, y2 = self.xyxy
        return {
            "x": x1 / width,
            "y": y1 / height,
            "w": (x2 - x1) / width,
            "h": (y2 - y1) / height,
        }


class Detector(ABC):
    @abstractmethod
    def infer(self, frame: np.ndarray) -> list[Detection]: ...

    @property
    @abstractmethod
    def class_names(self) -> dict[int, str]: ...
