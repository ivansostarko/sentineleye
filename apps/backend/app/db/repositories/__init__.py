"""Database repositories."""

from app.db.repositories.alert import AlertRuleRepository
from app.db.repositories.alert_event import AlertEventRepository
from app.db.repositories.camera import CameraRepository
from app.db.repositories.cloud_integration import CloudIntegrationRepository
from app.db.repositories.detection import DetectionEventRepository
from app.db.repositories.recording import RecordingRepository
from app.db.repositories.system_config import SystemConfigRepository
from app.db.repositories.user import UserRepository

__all__ = [
    "AlertEventRepository",
    "AlertRuleRepository",
    "CameraRepository",
    "CloudIntegrationRepository",
    "DetectionEventRepository",
    "RecordingRepository",
    "SystemConfigRepository",
    "UserRepository",
]
