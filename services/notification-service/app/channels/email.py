"""Email channel via aiosmtplib."""

from __future__ import annotations

from email.message import EmailMessage

import aiosmtplib

from app.channels import Channel, Notification
from app.config import get_settings


class EmailChannel(Channel):
    name = "email"

    async def send(self, notif: Notification, target: dict) -> None:
        s = get_settings()
        if not s.notify_email_enabled:
            return
        to_addr = target.get("email")
        if not to_addr:
            raise ValueError("EmailChannel requires target['email']")

        msg = EmailMessage()
        msg["From"] = s.smtp_from
        msg["To"] = to_addr
        msg["Subject"] = f"[SentinelEye] {notif.title}"
        msg.set_content(notif.body)

        await aiosmtplib.send(
            msg,
            hostname=s.smtp_host,
            port=s.smtp_port,
            username=s.smtp_user or None,
            password=s.smtp_password or None,
            start_tls=s.smtp_port == 587,
        )
