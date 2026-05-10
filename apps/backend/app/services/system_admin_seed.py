"""Seeded data for the System Settings admin views.

These views (Jobs / Emails / Logs) are scaffolded ahead of the real
integrations:

* **Jobs** will eventually pull from Celery via ``celery.control.inspect()``
  and the broker's ``queue_lengths`` API.
* **Emails** will pull from the ``email_log`` table once the notification
  service starts persisting send receipts.
* **Logs** will tail structured logs from the JSON log shipper (Loki / a
  flat file fallback).

Until those land, the endpoints serve plausible synthetic data so the UI
can be wired and reviewed end-to-end. Keep the shape stable — when the
real source comes online, only the ``services/system_admin_*.py`` modules
need to change.
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone

from app.schemas.system_admin import (
    EmailLogEntry,
    JobInfo,
    JobsOverview,
    LogEntry,
    QueueInfo,
)

# Use a fixed seed so reloads return the same dataset (prevents jitter
# while clicking around in the UI). Bump if you change the shape.
_RNG = random.Random(20260510)


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


# ─── Jobs / queues ────────────────────────────────────────────────────
def jobs_snapshot() -> JobsOverview:
    """Return a believable snapshot of running/queued jobs across queues."""
    now = _now_utc()
    queues = [
        QueueInfo(name="default",       pending=2,  running=3, workers=4),
        QueueInfo(name="recordings",    pending=12, running=2, workers=2),
        QueueInfo(name="ai-inference",  pending=4,  running=1, workers=1),
        QueueInfo(name="notifications", pending=0,  running=0, workers=2),
        QueueInfo(name="maintenance",   pending=1,  running=0, workers=1),
    ]

    jobs: list[JobInfo] = []

    # ── Active / running ───────────────────────────────────────────
    jobs.append(JobInfo(
        id="job_01HTWQ3FEXR9P2A1",
        name="recordings.archive_segment",
        queue="recordings",
        status="running",
        enqueued_at=now - timedelta(minutes=4, seconds=12),
        started_at=now - timedelta(minutes=3, seconds=58),
        progress=0.62,
        args={"camera_id": "0e8b…", "segment_id": "seg_18412"},
        runtime_seconds=238.4,
        attempts=1,
    ))
    jobs.append(JobInfo(
        id="job_01HTWQ3JFXR9P2A2",
        name="ai_engine.warm_model",
        queue="ai-inference",
        status="running",
        enqueued_at=now - timedelta(seconds=22),
        started_at=now - timedelta(seconds=18),
        progress=0.34,
        args={"model": "yolov8m.pt", "device": "cuda:0"},
        runtime_seconds=18.1,
    ))
    jobs.append(JobInfo(
        id="job_01HTWQ3LMXR9P2A3",
        name="cameras.refresh_tuya_streams",
        queue="default",
        status="running",
        enqueued_at=now - timedelta(seconds=8),
        started_at=now - timedelta(seconds=6),
        progress=0.81,
        args={"batch": 12},
        runtime_seconds=6.3,
    ))

    # ── Queued ────────────────────────────────────────────────────
    for i in range(2):
        jobs.append(JobInfo(
            id=f"job_01HTWQ3PNXR9P2A{4 + i}",
            name="recordings.archive_segment",
            queue="recordings",
            status="queued",
            enqueued_at=now - timedelta(seconds=_RNG.randint(2, 30)),
            args={"camera_id": "0e8b…", "segment_id": f"seg_{18413 + i}"},
        ))
    jobs.append(JobInfo(
        id="job_01HTWQ3QSXR9P2A6",
        name="alerts.dispatch_webhook",
        queue="notifications",
        status="queued",
        enqueued_at=now - timedelta(seconds=4),
        args={"webhook_id": "wh_204", "event_id": "evt_938421"},
    ))

    # ── Recent history ────────────────────────────────────────────
    jobs.append(JobInfo(
        id="job_01HTWQ3RTXR9P2A7",
        name="retention.purge_detections",
        queue="maintenance",
        status="succeeded",
        enqueued_at=now - timedelta(hours=8, minutes=14),
        started_at=now - timedelta(hours=8, minutes=14),
        finished_at=now - timedelta(hours=8, minutes=11),
        progress=1.0,
        args={"older_than_days": 7},
        runtime_seconds=187.4,
    ))
    jobs.append(JobInfo(
        id="job_01HTWQ3UVXR9P2A8",
        name="storage.archive_to_s3",
        queue="recordings",
        status="failed",
        enqueued_at=now - timedelta(hours=2, minutes=4),
        started_at=now - timedelta(hours=2, minutes=4),
        finished_at=now - timedelta(hours=2, minutes=3),
        progress=0.42,
        args={"bucket": "sentineleye-recordings", "prefix": "2026/05/03/"},
        error="botocore.exceptions.EndpointConnectionError: "
              "Could not connect to https://minio:9000",
        attempts=3,
        max_attempts=3,
        runtime_seconds=42.1,
    ))
    jobs.append(JobInfo(
        id="job_01HTWQ3WYXR9P2A9",
        name="cameras.health_check",
        queue="default",
        status="succeeded",
        enqueued_at=now - timedelta(minutes=1, seconds=4),
        started_at=now - timedelta(minutes=1, seconds=4),
        finished_at=now - timedelta(minutes=1, seconds=2),
        progress=1.0,
        runtime_seconds=2.1,
    ))

    return JobsOverview(queues=queues, jobs=jobs)


# ─── Emails ───────────────────────────────────────────────────────────
def email_log(*, offset: int, limit: int) -> tuple[list[EmailLogEntry], int]:
    """Return a paginated slice of seeded email send-receipts.

    Stable across calls (uses the module RNG seeded at import time).
    """
    now = _now_utc()
    catalog: list[EmailLogEntry] = [
        EmailLogEntry(
            id="em_01HTWS1A",
            to="ivan.sostarko@hotmail.com",
            subject="[SentinelEye] Motion detected: Front Gate",
            template="alert_motion_v2",
            status="sent",
            sent_at=now - timedelta(minutes=4),
            provider_message_id="ses-0000-aaaa-bbbb",
            attempts=1,
            payload_size_bytes=12_840,
        ),
        EmailLogEntry(
            id="em_01HTWS2B",
            to="ops@example.com",
            cc=["security@example.com"],
            subject="[SentinelEye] Camera offline: Driveway",
            template="alert_offline_v1",
            status="sent",
            sent_at=now - timedelta(minutes=22),
            provider_message_id="ses-0000-aaaa-cccc",
            attempts=1,
            payload_size_bytes=4_212,
        ),
        EmailLogEntry(
            id="em_01HTWS3C",
            to="admin@example.com",
            subject="[SentinelEye] Weekly storage report",
            template="report_weekly_v3",
            status="sent",
            sent_at=now - timedelta(hours=4),
            provider_message_id="ses-0000-aaaa-dddd",
            attempts=1,
            payload_size_bytes=84_010,
        ),
        EmailLogEntry(
            id="em_01HTWS4D",
            to="bouncy@nonexistent.example",
            subject="[SentinelEye] Welcome aboard",
            template="welcome_v1",
            status="bounced",
            sent_at=now - timedelta(hours=6, minutes=14),
            provider_message_id="ses-0000-aaaa-eeee",
            error="550 5.1.1 The email account that you tried to reach does not exist",
            attempts=1,
            payload_size_bytes=2_104,
        ),
        EmailLogEntry(
            id="em_01HTWS5E",
            to="ops@example.com",
            subject="[SentinelEye] Backup completed",
            template="report_backup_v1",
            status="sent",
            sent_at=now - timedelta(hours=8, minutes=2),
            provider_message_id="ses-0000-aaaa-ffff",
            attempts=1,
            payload_size_bytes=1_804,
        ),
        EmailLogEntry(
            id="em_01HTWS6F",
            to="dev@example.com",
            subject="[SentinelEye] Telegram delivery failed (retry queued)",
            template=None,
            status="failed",
            sent_at=now - timedelta(hours=12, minutes=18),
            error="ConnectionError: Failed to establish a new connection to api.telegram.org:443",
            attempts=3,
            payload_size_bytes=2_410,
        ),
        EmailLogEntry(
            id="em_01HTWS7G",
            to="ivan.sostarko@hotmail.com",
            subject="[SentinelEye] Password changed",
            template="security_pwd_change_v1",
            status="sent",
            sent_at=now - timedelta(days=1, hours=4),
            provider_message_id="ses-0000-aaaa-1111",
            attempts=1,
            payload_size_bytes=1_120,
        ),
        EmailLogEntry(
            id="em_01HTWS8H",
            to="ivan.sostarko@hotmail.com",
            subject="[SentinelEye] New sign-in from 188.252.114.221",
            template="security_signin_v2",
            status="sent",
            sent_at=now - timedelta(days=1, hours=12),
            provider_message_id="ses-0000-aaaa-2222",
            attempts=1,
            payload_size_bytes=2_804,
        ),
        EmailLogEntry(
            id="em_01HTWS9J",
            to="auditor@example.com",
            subject="[SentinelEye] Monthly access report",
            template="audit_monthly_v1",
            status="queued",
            sent_at=now - timedelta(seconds=12),
            attempts=0,
            payload_size_bytes=104_810,
        ),
        EmailLogEntry(
            id="em_01HTWSAK",
            to="ops@example.com",
            subject="[SentinelEye] Alert digest (24 events)",
            template="alert_digest_v2",
            status="sent",
            sent_at=now - timedelta(days=2, hours=2),
            provider_message_id="ses-0000-aaaa-3333",
            attempts=1,
            payload_size_bytes=24_810,
        ),
    ]
    total = len(catalog)
    return catalog[offset : offset + limit], total


# ─── Logs ─────────────────────────────────────────────────────────────
def log_entries(
    *, level: str | None, search: str | None, offset: int, limit: int,
) -> tuple[list[LogEntry], int]:
    """Return a paginated slice of seeded structured log entries."""
    now = _now_utc()
    catalog: list[LogEntry] = [
        LogEntry(
            timestamp=now - timedelta(seconds=2),
            level="INFO",
            logger="app.api.v1.endpoints.cameras",
            message="cameras.list_returned",
            extra={"page": 1, "size": 50, "total": 12, "user": "admin@sentineleye.io"},
            request_id="req_a8f3",
            duration_ms=18.4,
        ),
        LogEntry(
            timestamp=now - timedelta(seconds=4),
            level="DEBUG",
            logger="app.services.cache",
            message="cache.hit",
            extra={"key": "cameras:list:offset=0:limit=50"},
            request_id="req_a8f3",
        ),
        LogEntry(
            timestamp=now - timedelta(seconds=14),
            level="INFO",
            logger="app.services.event_bus",
            message="event_bus.published",
            extra={"channel": "events.detections", "size_bytes": 412},
        ),
        LogEntry(
            timestamp=now - timedelta(seconds=42),
            level="WARNING",
            logger="app.services.tuya_cloud",
            message="tuya.token_refresh_slow",
            extra={"elapsed_ms": 1842, "region": "eu"},
            duration_ms=1842,
        ),
        LogEntry(
            timestamp=now - timedelta(minutes=1, seconds=8),
            level="ERROR",
            logger="app.services.storage",
            message="s3.put_object_failed",
            extra={
                "bucket": "sentineleye-recordings",
                "key": "2026/05/10/cam-04/seg_18412.mp4",
                "error": "EndpointConnectionError",
            },
            request_id="req_b21c",
        ),
        LogEntry(
            timestamp=now - timedelta(minutes=3),
            level="INFO",
            logger="app.workers.tasks",
            message="task.completed",
            extra={"task": "cameras.health_check", "result": "ok", "checked": 12},
            duration_ms=2_104,
        ),
        LogEntry(
            timestamp=now - timedelta(minutes=8),
            level="INFO",
            logger="app.api.v1.endpoints.auth",
            message="auth.login_success",
            extra={"user": "admin@sentineleye.io", "ip": "188.252.114.221"},
            request_id="req_c14d",
            duration_ms=42.1,
        ),
        LogEntry(
            timestamp=now - timedelta(minutes=14),
            level="WARNING",
            logger="app.services.camera_service",
            message="camera.source_resolve_failed",
            extra={"camera_id": "0e8b...", "error": "tuya: device offline"},
        ),
        LogEntry(
            timestamp=now - timedelta(minutes=22),
            level="DEBUG",
            logger="app.db.session",
            message="db.connection_returned_to_pool",
            extra={"pool_size": 10, "in_use": 2},
        ),
        LogEntry(
            timestamp=now - timedelta(minutes=42),
            level="CRITICAL",
            logger="app.workers.tasks",
            message="storage.archive_to_s3.failed_after_retries",
            extra={"job_id": "job_01HTWQ3UVXR9P2A8", "attempts": 3},
        ),
        LogEntry(
            timestamp=now - timedelta(hours=1, minutes=4),
            level="INFO",
            logger="app.main",
            message="lifespan.startup_complete",
            extra={"version": "0.2.0", "env": "development"},
        ),
        LogEntry(
            timestamp=now - timedelta(hours=2),
            level="INFO",
            logger="app.workers.tasks",
            message="retention.purge_complete",
            extra={"removed": 18432, "freed_mb": 412.6},
            duration_ms=187_402,
        ),
    ]

    # Filter
    filtered = catalog
    if level:
        filtered = [e for e in filtered if e.level == level]
    if search:
        needle = search.lower()
        filtered = [
            e for e in filtered
            if needle in e.message.lower()
            or needle in e.logger.lower()
            or any(needle in str(v).lower() for v in e.extra.values())
        ]

    return filtered[offset : offset + limit], len(filtered)
