"""Alert event (history) repository."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import desc, func, select, update

from app.db.repositories.base import BaseRepository
from app.models.alert_event import AlertEvent


class AlertEventRepository(BaseRepository[AlertEvent]):
    model = AlertEvent

    async def list(  # type: ignore[override]
        self,
        *,
        offset: int = 0,
        limit: int = 50,
        only_unacknowledged: bool = False,
        rule_id: UUID | None = None,
        camera_id: UUID | None = None,
    ) -> list[AlertEvent]:
        stmt = select(AlertEvent).order_by(desc(AlertEvent.occurred_at))
        if only_unacknowledged:
            stmt = stmt.where(AlertEvent.acknowledged_at.is_(None))
        if rule_id is not None:
            stmt = stmt.where(AlertEvent.rule_id == rule_id)
        if camera_id is not None:
            stmt = stmt.where(AlertEvent.camera_id == camera_id)
        stmt = stmt.offset(offset).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())

    async def count(self, *, only_unacknowledged: bool = False) -> int:  # type: ignore[override]
        stmt = select(func.count()).select_from(AlertEvent)
        if only_unacknowledged:
            stmt = stmt.where(AlertEvent.acknowledged_at.is_(None))
        return int((await self.session.execute(stmt)).scalar_one())

    async def acknowledge(
        self, event_id: UUID, *, user_id: UUID, now: datetime
    ) -> bool:
        """Mark a single event as acknowledged. No-op (returns False) if it
        was already acknowledged or doesn't exist."""
        stmt = (
            update(AlertEvent)
            .where(
                AlertEvent.id == event_id,
                AlertEvent.acknowledged_at.is_(None),
            )
            .values(acknowledged_at=now, acknowledged_by=user_id)
        )
        result = await self.session.execute(stmt)
        return (result.rowcount or 0) > 0
