"""Tuya OpenAPI v2 client.

Implements the v2 signing scheme used by Tuya's IoT Cloud:

    sign_str = ACCESS_ID + [ACCESS_TOKEN] + TIMESTAMP + NONCE + STRING_TO_SIGN
    STRING_TO_SIGN = HTTP_METHOD + "\\n" + SHA256(body) + "\\n" + headers + "\\n" + path
    sign = HMAC_SHA256(sign_str, ACCESS_SECRET).hexdigest().upper()

For unauthenticated calls (the token endpoint itself) ACCESS_TOKEN is omitted.
Reference: https://developer.tuya.com/en/docs/iot/api-reference
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
import time
from dataclasses import dataclass
from typing import Any

import httpx

from app.core.exceptions import AppError
from app.core.logging import get_logger

log = get_logger(__name__)


REGION_ENDPOINTS = {
    "eu": "https://openapi.tuyaeu.com",
    "us": "https://openapi.tuyaus.com",
    "cn": "https://openapi.tuyacn.com",
    "in": "https://openapi.tuyain.com",
}


class TuyaError(AppError):
    code = "tuya_error"


@dataclass(slots=True)
class _Token:
    access_token: str
    expires_at: float  # epoch seconds


class TuyaClient:
    """Async client for one Tuya cloud project."""

    def __init__(
        self,
        access_id: str,
        access_secret: str,
        region: str,
        *,
        timeout: float = 8.0,
    ) -> None:
        if region not in REGION_ENDPOINTS:
            raise TuyaError(f"Unknown Tuya region: {region!r}")
        self._access_id = access_id
        self._access_secret = access_secret.encode()
        self._base = REGION_ENDPOINTS[region]
        self._timeout = timeout
        self._token: _Token | None = None

    # ── Signing ────────────────────────────────────────────────────────
    def _sign(
        self,
        method: str,
        path: str,
        *,
        body: str = "",
        timestamp: str,
        nonce: str,
        access_token: str | None = None,
    ) -> str:
        body_sha = hashlib.sha256(body.encode()).hexdigest()
        string_to_sign = f"{method}\n{body_sha}\n\n{path}"
        sign_payload = f"{self._access_id}{access_token or ''}{timestamp}{nonce}{string_to_sign}"
        digest = hmac.new(self._access_secret, sign_payload.encode(), hashlib.sha256).hexdigest()
        return digest.upper()

    def _headers(self, sign: str, timestamp: str, nonce: str, *, with_token: bool) -> dict[str, str]:
        headers = {
            "client_id": self._access_id,
            "sign": sign,
            "sign_method": "HMAC-SHA256",
            "t": timestamp,
            "nonce": nonce,
            "Content-Type": "application/json",
        }
        if with_token:
            assert self._token is not None
            headers["access_token"] = self._token.access_token
        return headers

    # ── Token lifecycle ────────────────────────────────────────────────
    async def _refresh_token(self, client: httpx.AsyncClient) -> _Token:
        path = "/v1.0/token?grant_type=1"
        timestamp = str(int(time.time() * 1000))
        nonce = secrets.token_hex(8)
        sign = self._sign("GET", path, timestamp=timestamp, nonce=nonce)
        headers = self._headers(sign, timestamp, nonce, with_token=False)

        r = await client.get(f"{self._base}{path}", headers=headers)
        data = r.json()
        if not data.get("success"):
            raise TuyaError(f"Tuya token error: {data.get('msg')} (code={data.get('code')})")
        result = data["result"]
        return _Token(
            access_token=result["access_token"],
            # Tuya gives `expire_time` in seconds from now; refresh a minute early.
            expires_at=time.time() + max(60, int(result["expire_time"]) - 60),
        )

    async def _ensure_token(self, client: httpx.AsyncClient) -> None:
        if self._token is None or time.time() >= self._token.expires_at:
            self._token = await self._refresh_token(client)

    # ── Public API ─────────────────────────────────────────────────────
    async def allocate_stream(self, device_id: str, *, kind: str = "rtsp") -> str:
        """Allocate a streaming URL for a camera. URL is short-lived (~minutes)."""
        if kind not in {"rtsp", "hls"}:
            raise TuyaError(f"Unsupported stream kind: {kind!r}")
        path = f"/v1.0/devices/{device_id}/stream/actions/allocate"
        body = '{"type":"' + kind + '"}'

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            await self._ensure_token(client)
            timestamp = str(int(time.time() * 1000))
            nonce = secrets.token_hex(8)
            sign = self._sign(
                "POST", path,
                body=body, timestamp=timestamp, nonce=nonce,
                access_token=self._token.access_token,  # type: ignore[union-attr]
            )
            headers = self._headers(sign, timestamp, nonce, with_token=True)

            r = await client.post(f"{self._base}{path}", headers=headers, content=body)
            data = r.json()
            if not data.get("success"):
                raise TuyaError(
                    f"Tuya allocate-stream failed for {device_id}: "
                    f"{data.get('msg')} (code={data.get('code')})"
                )
            url = data["result"]["url"]
            log.info("tuya.stream_allocated", device_id=device_id, kind=kind)
            return url

    async def get_device(self, device_id: str) -> dict[str, Any]:
        """Fetch device metadata — useful for validating a device_id."""
        path = f"/v1.0/devices/{device_id}"
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            await self._ensure_token(client)
            timestamp = str(int(time.time() * 1000))
            nonce = secrets.token_hex(8)
            sign = self._sign(
                "GET", path,
                timestamp=timestamp, nonce=nonce,
                access_token=self._token.access_token,  # type: ignore[union-attr]
            )
            headers = self._headers(sign, timestamp, nonce, with_token=True)
            r = await client.get(f"{self._base}{path}", headers=headers)
            data = r.json()
            if not data.get("success"):
                raise TuyaError(
                    f"Tuya get-device failed for {device_id}: "
                    f"{data.get('msg')} (code={data.get('code')})"
                )
            return data["result"]
