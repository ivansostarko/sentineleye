"""Celery tasks (retention, archival, health monitoring)."""

from __future__ import annotations

import asyncio

from app.core.logging import get_logger
from app.db.repositories.camera import CameraRepository
from app.db.repositories.cloud_integration import CloudIntegrationRepository
from app.db.session import _SessionLocal
from app.models.camera import CameraProtocol
from app.services.camera_service import CameraService
from app.services.control_plane import RecordingClient
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


@celery_app.task(name="app.workers.tasks.refresh_tuya_streams")
def refresh_tuya_streams() -> dict[str, int]:
    """Re-allocate stream URLs for every enabled Tuya camera.

    Tuya RTSP URLs expire after a few minutes. We pre-emptively re-allocate
    on a tighter cadence than the expiry, then push the fresh URL into the
    recording-service so its FFmpeg child can reconnect. Best-effort: any
    per-camera failure is logged and skipped — the next tick retries.
    """
    return asyncio.run(_refresh_tuya_streams_async())


async def _refresh_tuya_streams_async() -> dict[str, int]:
    log.info("worker.tuya_refresh.start")
    refreshed = 0
    failed = 0
    recording = RecordingClient()

    async with _SessionLocal() as session:
        cameras = CameraRepository(session)
        integrations = CloudIntegrationRepository(session)
        service = CameraService(cameras, integrations, recording=recording)

        active = [
            c for c in await cameras.list_enabled()
            if c.protocol == CameraProtocol.TUYA and c.record_continuous
        ]
        for camera in active:
            try:
                source = await service.resolve_source(camera)
                if source:
                    await recording.start(camera, source=source)
                    refreshed += 1
                else:
                    failed += 1
            except Exception as exc:  # noqa: BLE001 — best-effort log + continue
                log.warning(
                    "worker.tuya_refresh.error",
                    camera_id=str(camera.id), error=str(exc),
                )
                failed += 1
        await session.commit()

    log.info("worker.tuya_refresh.done", refreshed=refreshed, failed=failed)
    return {"refreshed": refreshed, "failed": failed}
