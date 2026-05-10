"""Celery worker — runs retention sweeps, S3 archival, etc."""

from __future__ import annotations

from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "sentineleye",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_default_queue="sentineleye.default",
    beat_schedule={
        "retention-sweep": {
            "task": "app.workers.tasks.retention_sweep",
            "schedule": 3600.0,  # hourly
        },
        "archive-to-s3": {
            "task": "app.workers.tasks.archive_to_s3",
            "schedule": 1800.0,  # every 30 min
        },
        "camera-health-check": {
            "task": "app.workers.tasks.camera_health_check",
            "schedule": 60.0,  # every minute
        },
        # Tuya RTSP URLs expire ~10 min after allocation; refresh well before.
        "refresh-tuya-streams": {
            "task": "app.workers.tasks.refresh_tuya_streams",
            "schedule": 240.0,  # every 4 minutes
        },
    },
)
