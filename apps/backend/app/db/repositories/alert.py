"""Alert rule repository."""

from __future__ import annotations

from sqlalchemy import or_, select

from app.db.repositories.base import BaseRepository
from app.models.alert_rule import AlertRule


class AlertRuleRepository(BaseRepository[AlertRule]):
    model = AlertRule

    async def list_for_camera(self, camera_id) -> list[AlertRule]:
        stmt = select(AlertRule).where(
            AlertRule.enabled.is_(True),
            or_(AlertRule.camera_id == camera_id, AlertRule.camera_id.is_(None)),
        )
        return list((await self.session.execute(stmt)).scalars().all())
