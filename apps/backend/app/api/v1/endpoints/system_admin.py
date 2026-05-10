"""Admin endpoints for the System Settings UI: jobs, emails, logs, cache rebuild.

Most of these serve seeded data today (see :mod:`app.services.system_admin_seed`)
— the schemas are intentionally close to the eventual real shapes so the
frontend wiring doesn't need to change when the integrations land.
"""

from __future__ import annotations

import asyncio
import time
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.v1.deps import require_role
from app.models.user import UserRole
from app.schemas.common import Page
from app.schemas.system_admin import (
    CacheRebuildResult,
    EmailLogEntry,
    JobActionResult,
    JobsOverview,
    LogEntry,
    LogLevel,
    LogsResponse,
)
from app.scripts.warm_cache import warm
from app.services import system_admin_seed

router = APIRouter(
    prefix="/system",
    tags=["system-admin"],
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)


# ─── Jobs ─────────────────────────────────────────────────────────────
@router.get("/jobs", response_model=JobsOverview)
async def list_jobs() -> JobsOverview:
    """Snapshot of running/queued jobs across worker queues.

    TODO: replace with ``celery.control.inspect().active()`` etc. once
    Celery introspection is wired. The ``JobsOverview`` shape is the
    contract — keep it stable.
    """
    return system_admin_seed.jobs_snapshot()


@router.post("/jobs/{job_id}/cancel", response_model=JobActionResult)
async def cancel_job(job_id: str) -> JobActionResult:
    """Mark a queued/running job for cancellation.

    Today: returns synthetic ack. Real version will signal Celery via
    ``AsyncResult(job_id).revoke(terminate=True)``.
    """
    if not job_id.startswith("job_"):
        raise HTTPException(status_code=404, detail="Unknown job id")
    return JobActionResult(
        id=job_id,
        action="cancel",
        accepted=True,
        message="Cancellation signal queued. Job will stop at next safe point.",
    )


@router.post("/jobs/{job_id}/retry", response_model=JobActionResult)
async def retry_job(job_id: str) -> JobActionResult:
    """Re-enqueue a failed job."""
    if not job_id.startswith("job_"):
        raise HTTPException(status_code=404, detail="Unknown job id")
    return JobActionResult(
        id=job_id,
        action="retry",
        accepted=True,
        message="Job re-enqueued. A worker will pick it up shortly.",
    )


# ─── Emails ───────────────────────────────────────────────────────────
@router.get("/emails", response_model=Page[EmailLogEntry])
async def list_emails(
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
) -> Page[EmailLogEntry]:
    """List sent / queued / failed outbound emails with pagination.

    TODO: replace with ``email_log`` table query once the notification
    service starts persisting send-receipts.
    """
    items, total = system_admin_seed.email_log(
        offset=(page - 1) * size, limit=size,
    )
    return Page[EmailLogEntry](items=items, total=total, page=page, size=size)


# ─── Logs ─────────────────────────────────────────────────────────────
@router.get("/logs", response_model=LogsResponse)
async def list_logs(
    level: LogLevel | None = Query(None),
    search: str | None = Query(None, max_length=200),
    page: int = Query(1, ge=1),
    size: int = Query(100, ge=1, le=500),
) -> LogsResponse:
    """Recent backend log entries (level/text filterable, paginated).

    TODO: tail from the structured log shipper (Loki / a flat JSON file
    in production). Keeping the LogEntry shape close to ``structlog``'s
    JSON output so the swap is a noop on the UI.
    """
    items, total = system_admin_seed.log_entries(
        level=level, search=search,
        offset=(page - 1) * size, limit=size,
    )
    return LogsResponse(
        items=items,
        total=total,
        levels_available=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
    )


# ─── Cache rebuild (real — calls the warmer) ──────────────────────────
@router.post("/cache/rebuild", response_model=CacheRebuildResult)
async def rebuild_cache(
    pages: int = Query(3, ge=1, le=20),
    page_size: int = Query(50, ge=1, le=200),
    skip_cameras: bool = Query(False),
    skip_system_config: bool = Query(False),
) -> CacheRebuildResult:
    """Rerun the cache warmer in-process and return per-target stats.

    Mirrors the CLI ``python -m app.scripts.warm_cache`` so admins don't
    need shell access. The warmer caps each target — a dead Redis won't
    hang the request.
    """
    t0 = time.perf_counter()
    try:
        # The warmer talks to its own DB session + Redis pool; no async
        # cancellation surprises if we await it directly.
        stats = await warm(
            cameras=not skip_cameras,
            system_config=not skip_system_config,
            pages=pages,
            page_size=page_size,
            quiet=True,
        )
    except asyncio.CancelledError:
        raise
    except Exception as exc:  # noqa: BLE001 — surface as 5xx with detail
        raise HTTPException(status_code=500, detail=f"Cache warm failed: {exc}") from exc

    elapsed_ms = (time.perf_counter() - t0) * 1000
    return CacheRebuildResult(
        targets=len(stats),
        succeeded=sum(1 for s in stats if s.ok),
        items_warmed=sum(s.items for s in stats if s.ok),
        elapsed_ms=elapsed_ms,
        details=[
            {
                "target": s.target,
                "items": s.items,
                "elapsed_ms": s.elapsed_ms,
                "ok": s.ok,
                "error": s.error,
            }
            for s in stats
        ],
    )
