"""Schemas for the System Settings admin pages (jobs, emails, logs)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


# ─── Jobs / queues ────────────────────────────────────────────────────
JobStatus = Literal["queued", "running", "succeeded", "failed", "cancelled"]


class JobInfo(BaseModel):
    id: str
    name: str
    queue: str
    status: JobStatus
    enqueued_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    progress: float = Field(ge=0.0, le=1.0, default=0.0)
    args: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    attempts: int = 1
    max_attempts: int = 3
    runtime_seconds: float | None = None


class QueueInfo(BaseModel):
    name: str
    pending: int
    running: int
    workers: int


class JobsOverview(BaseModel):
    queues: list[QueueInfo]
    jobs: list[JobInfo]


class JobActionResult(BaseModel):
    id: str
    action: Literal["cancel", "retry"]
    accepted: bool
    message: str


# ─── Email log ────────────────────────────────────────────────────────
EmailStatus = Literal["sent", "queued", "failed", "bounced"]


class EmailLogEntry(BaseModel):
    id: str
    to: str
    cc: list[str] = Field(default_factory=list)
    subject: str
    template: str | None = None
    status: EmailStatus
    sent_at: datetime
    provider_message_id: str | None = None
    error: str | None = None
    attempts: int = 1
    payload_size_bytes: int = 0


# ─── Logs ─────────────────────────────────────────────────────────────
LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


class LogEntry(BaseModel):
    timestamp: datetime
    level: LogLevel
    logger: str
    message: str
    extra: dict[str, Any] = Field(default_factory=dict)
    request_id: str | None = None
    duration_ms: float | None = None


class LogsResponse(BaseModel):
    items: list[LogEntry]
    total: int
    levels_available: list[LogLevel]


# ─── Cache rebuild result (returned by POST /system/cache/rebuild) ────
class CacheRebuildResult(BaseModel):
    targets: int
    succeeded: int
    items_warmed: int
    elapsed_ms: float
    details: list[dict[str, Any]]
