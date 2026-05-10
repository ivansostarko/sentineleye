"""Generic outbound webhook channel."""

from __future__ import annotations

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.channels import Channel, Notification
from app.config import get_settings


class WebhookChannel(Channel):
    name = "webhook"

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def send(self, notif: Notification, target: dict) -> None:
        if not get_settings().notify_webhook_enabled:
            return
        url = target.get("url")
        if not url:
            raise ValueError("WebhookChannel requires target['url']")

        body = {
            "title": notif.title,
            "body": notif.body,
            "severity": notif.severity,
            "metadata": notif.metadata or {},
        }
        headers = target.get("headers") or {}
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.post(url, json=body, headers=headers)
            r.raise_for_status()
