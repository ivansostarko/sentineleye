"""Telegram channel via Bot API."""

from __future__ import annotations

import httpx

from app.channels import Channel, Notification
from app.config import get_settings


class TelegramChannel(Channel):
    name = "telegram"

    async def send(self, notif: Notification, target: dict) -> None:
        s = get_settings()
        if not s.notify_telegram_enabled:
            return
        chat_id = target.get("chat_id") or s.telegram_chat_id
        if not chat_id or not s.telegram_bot_token:
            raise ValueError("Telegram bot token + chat_id required")

        text = f"*{notif.title}*\n\n{notif.body}"
        url = f"https://api.telegram.org/bot{s.telegram_bot_token}/sendMessage"
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.post(
                url,
                json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"},
            )
            r.raise_for_status()
