"""Alert evaluation + dispatch.

Lives between the detection-event ingest endpoint and the notification-service.
For every detection event:

  1. Look up enabled rules that apply to the camera (or are global).
  2. For each rule, check its trigger + class allowlist + min_confidence.
  3. Atomically claim a cooldown slot — concurrent ingest workers can't
     double-fire the same rule within `cooldown_seconds`.
  4. Persist an `AlertEvent` row.
  5. Fire-and-forget dispatch to notification-service for any non-realtime
     channel; realtime is delivered via WebSocket on the backend itself
     (the WS pubsub is wired separately).

Dispatch failures are logged and recorded in `channels_dispatched` but never
block the ingest path.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import httpx

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.repositories.alert import AlertRuleRepository
from app.db.repositories.alert_event import AlertEventRepository
from app.models.alert_event import AlertEvent
from app.models.alert_rule import AlertChannel, AlertRule, AlertSeverity, AlertTrigger
from app.models.detection_event import DetectionEvent

log = get_logger(__name__)


class AlertService:
    """Evaluates rules against an incoming detection event."""

    def __init__(
        self,
        rules: AlertRuleRepository,
        events: AlertEventRepository,
    ) -> None:
        self.rules = rules
        self.events = events

    # ── Public API ─────────────────────────────────────────────────
    async def evaluate_detection(self, det: DetectionEvent) -> list[AlertEvent]:
        """Evaluate every applicable rule for a detection event.

        Returns the list of AlertEvent rows that were created (i.e. rules
        that matched + passed cooldown).
        """
        candidates = await self.rules.list_for_camera(det.camera_id)
        fired: list[AlertEvent] = []
        for rule in candidates:
            if not self._matches(rule, det):
                continue
            now = datetime.now(UTC)
            claimed = await self.rules.try_acquire_fire_slot(rule, now)
            if not claimed:
                continue
            event = await self._record(rule, det, now)
            await self._dispatch(event, rule)
            fired.append(event)
        return fired

    # ── Matching ───────────────────────────────────────────────────
    @staticmethod
    def _matches(rule: AlertRule, det: DetectionEvent) -> bool:
        # We only fire object_detected rules from this hot path — other
        # triggers (camera_offline, motion, line_crossed, ...) are emitted
        # by their own producers.
        if rule.trigger != AlertTrigger.OBJECT_DETECTED:
            return False
        if det.confidence < rule.min_confidence:
            return False
        allowlist = rule.object_classes or []
        if allowlist and det.object_class not in allowlist:
            return False
        return True

    # ── Persistence ────────────────────────────────────────────────
    async def _record(
        self, rule: AlertRule, det: DetectionEvent, now: datetime
    ) -> AlertEvent:
        title = f"{rule.name}: {det.object_class}"
        body = (
            f"Detected {det.object_class} (confidence {det.confidence:.0%}) "
            f"at {det.occurred_at.isoformat()}"
        )
        context: dict[str, Any] = {
            "object_class": det.object_class,
            "confidence": det.confidence,
            "track_id": det.track_id,
        }
        event = AlertEvent(
            rule_id=rule.id,
            camera_id=det.camera_id,
            detection_event_id=det.id,
            occurred_at=now,
            severity=rule.severity,
            title=title,
            body=body,
            context=context,
            channels_dispatched=[],
        )
        return await self.events.add(event)

    # ── Dispatch ───────────────────────────────────────────────────
    async def _dispatch(self, event: AlertEvent, rule: AlertRule) -> None:
        """Fire-and-forget dispatch to notification-service.

        Realtime is handled by the WS publisher on the backend itself — we
        only call notification-service for the external channels.
        """
        external = [c for c in rule.channels if c != AlertChannel.REALTIME.value]
        if not external:
            return

        results: list[dict[str, Any]] = []
        url = get_settings().notification_service_url.rstrip("/") + "/dispatch"
        try:
            async with httpx.AsyncClient(timeout=4.0) as client:
                for ch in external:
                    payload = {
                        "channel": ch,
                        # Notification-service interprets this per-channel —
                        # for now it falls back to its own configured target.
                        "target": {},
                        "title": event.title,
                        "body": event.body or "",
                        "severity": _severity_to_log(rule.severity),
                        "metadata": {
                            "rule_id": str(rule.id),
                            "camera_id": str(event.camera_id) if event.camera_id else None,
                            "alert_event_id": str(event.id),
                            **(event.context or {}),
                        },
                    }
                    try:
                        r = await client.post(url, json=payload)
                        results.append({
                            "channel": ch,
                            "success": r.status_code < 400,
                            "detail": None if r.status_code < 400 else r.text[:200],
                        })
                    except httpx.HTTPError as exc:
                        results.append({"channel": ch, "success": False, "detail": str(exc)})
        except Exception as exc:  # noqa: BLE001 — never block ingest
            log.warning("alerts.dispatch_failed", error=str(exc))
            results.append({"channel": "*", "success": False, "detail": str(exc)})

        # Persist the per-channel result. We do this on the same session
        # so it commits with the AlertEvent row.
        event.channels_dispatched = results
        await self.events.session.flush()


def _severity_to_log(s: AlertSeverity) -> str:
    return {
        AlertSeverity.LOW: "info",
        AlertSeverity.MEDIUM: "info",
        AlertSeverity.HIGH: "warning",
        AlertSeverity.CRITICAL: "critical",
    }[s]
