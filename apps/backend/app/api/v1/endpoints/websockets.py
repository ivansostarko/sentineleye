"""Real-time WebSocket endpoints — live frames + event stream."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect, status

from app.core.logging import get_logger
from app.core.security import decode_token
from app.services.event_bus import (
    ALERT_CHANNEL,
    CAMERA_STATE_CHANNEL,
    DETECTION_CHANNEL,
    subscribe,
)

router = APIRouter(prefix="/ws", tags=["websocket"])
log = get_logger(__name__)


def _authorize_ws(token: str | None) -> dict | None:
    """Validate WS token; close if invalid."""
    if not token:
        return None
    try:
        return decode_token(token, expected_type="access")
    except Exception:
        return None


@router.websocket("/events/stream")
async def event_stream(websocket: WebSocket, token: str | None = Query(default=None)) -> None:
    """Fan-out detection + camera-state + alert events to all authenticated clients."""
    if _authorize_ws(token) is None:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()
    log.info("ws.events.connected")

    async def pump(channel: str) -> None:
        async for msg in subscribe(channel):
            await websocket.send_json({"channel": channel, "data": msg})

    tasks = [
        asyncio.create_task(pump(DETECTION_CHANNEL)),
        asyncio.create_task(pump(CAMERA_STATE_CHANNEL)),
        asyncio.create_task(pump(ALERT_CHANNEL)),
    ]
    try:
        # Block until the client disconnects.
        await websocket.receive_text()
    except WebSocketDisconnect:
        log.info("ws.events.disconnected")
    finally:
        for t in tasks:
            t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)


@router.websocket("/cameras/{camera_id}/live")
async def camera_live(
    websocket: WebSocket,
    camera_id: str,
    token: str | None = Query(default=None),
) -> None:
    """Live frame relay. Frames are pushed by the recording-service as binary blobs.

    For production, switch this to WebRTC or HLS — this WS path is a fallback
    suitable for low-FPS preview tiles in the dashboard.
    """
    if _authorize_ws(token) is None:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()
    channel = f"frames.{camera_id}"
    log.info("ws.live.connected", camera_id=camera_id)

    async def pump() -> None:
        async for msg in subscribe(channel):
            # `msg` is a dict like {"jpeg_b64": "...", "ts": "..."}
            await websocket.send_json(msg)

    task = asyncio.create_task(pump())
    try:
        await websocket.receive_text()
    except WebSocketDisconnect:
        log.info("ws.live.disconnected", camera_id=camera_id)
    finally:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
