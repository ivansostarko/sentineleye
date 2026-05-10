"""Database repositories."""

from app.db.repositories.alert import AlertRuleRepository
from app.db.repositories.camera import CameraRepository
from app.db.repositories.detection import DetectionEventRepository
from app.db.repositories.recording import RecordingRepository
from app.db.repositories.user import UserRepository

__all__ = [
    "AlertRuleRepository",
    "CameraRepository",
    "DetectionEventRepository",
    "RecordingRepository",
    "UserRepository",
]
