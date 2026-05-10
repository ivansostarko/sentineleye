"""Detection event repository."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import desc, func, select

from app.db.repositories.base import BaseRepository
from app.models.detection_event import DetectionEvent


class DetectionEventRepository(BaseRepository[DetectionEvent]):
    model = DetectionEvent

    async def search(
        self,
        *,
        camera_id: UUID | None = None,
        object_class: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[DetectionEvent], int]:
        stmt = select(DetectionEvent)
        count_stmt = select(func.count()).select_from(DetectionEvent)

        if camera_id is not None:
            stmt = stmt.where(DetectionEvent.camera_id == camera_id)
            count_stmt = count_stmt.where(DetectionEvent.camera_id == camera_id)
        if object_class is not None:
            stmt = stmt.where(DetectionEvent.object_class == object_class)
            count_stmt = count_stmt.where(DetectionEvent.object_class == object_class)
        if start is not None:
            stmt = stmt.where(DetectionEvent.occurred_at >= start)
            count_stmt = count_stmt.where(DetectionEvent.occurred_at >= start)
        if end is not None:
            stmt = stmt.where(DetectionEvent.occurred_at <= end)
            count_stmt = count_stmt.where(DetectionEvent.occurred_at <= end)

        stmt = stmt.order_by(desc(DetectionEvent.occurred_at)).offset(offset).limit(limit)

        items = list((await self.session.execute(stmt)).scalars().all())
        total = int((await self.session.execute(count_stmt)).scalar_one())
        return items, total
