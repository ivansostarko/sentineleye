"""Alert rule repository."""

from __future__ import annotations

from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import or_, select, update

from app.db.repositories.base import BaseRepository
from app.models.alert_rule import AlertRule


class AlertRuleRepository(BaseRepository[AlertRule]):
    model = AlertRule

    async def list_for_camera(self, camera_id: UUID | None) -> list[AlertRule]:
        """Enabled rules that apply to the given camera (or are global)."""
        stmt = select(AlertRule).where(
            AlertRule.enabled.is_(True),
            or_(AlertRule.camera_id == camera_id, AlertRule.camera_id.is_(None)),
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def try_acquire_fire_slot(self, rule: AlertRule, now: datetime) -> bool:
        """Atomically check + claim the cooldown window for a rule.

        Returns True if the rule has not fired within `cooldown_seconds`
        and the caller may proceed to dispatch. Uses an UPDATE..WHERE
        guard clause so concurrent ingest workers can't double-fire.
        """
        cutoff = now - timedelta(seconds=rule.cooldown_seconds)
        stmt = (
            update(AlertRule)
            .where(
                AlertRule.id == rule.id,
                or_(
                    AlertRule.last_fired_at.is_(None),
                    AlertRule.last_fired_at < cutoff,
                ),
            )
            .values(last_fired_at=now)
        )
        result = await self.session.execute(stmt)
        return (result.rowcount or 0) > 0
