"""Celery tasks (retention, archival, health monitoring)."""

from __future__ import annotations

from app.core.logging import get_logger
from app.workers import celery_app

log = get_logger(__name__)


@celery_app.task(name="app.workers.tasks.retention_sweep")
def retention_sweep() -> dict[str, int]:
    """Delete recordings older than RETENTION_DAYS (and orphan S3 objects).

    TODO: implement using `RecordingRepository` + `Storage.delete`.
    """
    log.info("worker.retention_sweep.start")
    return {"deleted": 0}


@celery_app.task(name="app.workers.tasks.archive_to_s3")
def archive_to_s3() -> dict[str, int]:
    """Move local recordings older than ARCHIVE_AFTER_DAYS to S3 (hybrid mode).

    TODO: stream from local FS → S3, update Recording.storage_backend.
    """
    log.info("worker.archive.start")
    return {"archived": 0}


@celery_app.task(name="app.workers.tasks.camera_health_check")
def camera_health_check() -> dict[str, int]:
    """Probe each enabled camera and update CameraStatus.

    TODO: use ONVIF GetSystemDateAndTime / RTSP DESCRIBE / ffprobe to verify.
    """
    log.info("worker.camera_health.start")
    return {"checked": 0}
