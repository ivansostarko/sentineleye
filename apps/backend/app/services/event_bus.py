"""Redis pub/sub event bus — broadcasts detections & camera state to WS clients."""

from __future__ import annotations

import json
from typing import AsyncIterator

from app.services.redis_client import get_redis

DETECTION_CHANNEL = "events.detections"
CAMERA_STATE_CHANNEL = "events.camera_state"
ALERT_CHANNEL = "events.alerts"


async def publish(channel: str, payload: dict) -> None:
    await get_redis().publish(channel, json.dumps(payload, default=str))


async def subscribe(channel: str) -> AsyncIterator[dict]:
    pubsub = get_redis().pubsub()
    await pubsub.subscribe(channel)
    try:
        async for message in pubsub.listen():
            if message["type"] != "message":
                continue
            data = message["data"]
            if isinstance(data, bytes):
                data = data.decode()
            try:
                yield json.loads(data)
            except json.JSONDecodeError:
                continue
    finally:
        await pubsub.unsubscribe(channel)
        await pubsub.close()
