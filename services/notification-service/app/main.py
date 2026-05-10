"""Notification service control plane."""

from __future__ import annotations

import asyncio

import structlog
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app.channels import Notification
from app.channels.email import EmailChannel
from app.channels.telegram import TelegramChannel
from app.channels.webhook import WebhookChannel

log = structlog.get_logger(__name__)
app = FastAPI(title="SentinelEye Notification Service", version="0.1.0")

_channels = {
    "email": EmailChannel(),
    "telegram": TelegramChannel(),
    "webhook": WebhookChannel(),
}


class DispatchRequest(BaseModel):
    channel: str
    target: dict
    title: str
    body: str
    severity: str = "info"
    metadata: dict | None = None


@app.get("/healthz")
async def healthz() -> dict[str, object]:
    return {"status": "ok", "channels": list(_channels.keys())}


@app.post("/dispatch")
async def dispatch(req: DispatchRequest) -> dict[str, str]:
    ch = _channels.get(req.channel)
    if ch is None:
        raise HTTPException(400, f"Unknown channel: {req.channel}")
    notif = Notification(
        title=req.title, body=req.body, severity=req.severity, metadata=req.metadata
    )
    try:
        await ch.send(notif, req.target)
    except Exception as exc:
        log.error("notify.dispatch_failed", channel=req.channel, error=str(exc))
        raise HTTPException(502, f"Channel error: {exc}") from exc
    return {"status": "sent", "channel": req.channel}


class BulkDispatchRequest(BaseModel):
    items: list[DispatchRequest]


@app.post("/dispatch/bulk")
async def dispatch_bulk(req: BulkDispatchRequest) -> dict[str, int]:
    """Fan-out concurrently; partial failures are acceptable."""

    async def _safe(item: DispatchRequest) -> bool:
        try:
            await dispatch(item)
            return True
        except Exception as exc:
            log.warning("notify.bulk_item_failed", error=str(exc))
            return False

    results = await asyncio.gather(*[_safe(i) for i in req.items])
    return {"sent": sum(results), "failed": len(results) - sum(results)}
