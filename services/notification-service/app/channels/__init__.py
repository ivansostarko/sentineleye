"""Notification channels."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class Notification:
    title: str
    body: str
    severity: str = "info"  # info | warning | critical
    metadata: dict | None = None


class Channel(ABC):
    name: str

    @abstractmethod
    async def send(self, notif: Notification, target: dict) -> None: ...
