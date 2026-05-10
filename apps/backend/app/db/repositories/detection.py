"""Detection event repository."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import desc, func, select

from app.db.repositories.base import BaseRepository
from app.models.camera import Camera
from app.models.detection_event import DetectionEvent


class DetectionEventRepository(BaseRepository[DetectionEvent]):
    model = DetectionEvent

    async def search(
        self,
        *,
        camera_id: UUID | None = None,
        object_class: str | None = None,
        classes_in: list[str] | None = None,
        min_confidence: float | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[tuple[DetectionEvent, str | None]], int]:
        """Return (event, camera_name) pairs + total.

        The camera join saves the N+1 the events list otherwise needs to
        label each row.
        """
        stmt = select(DetectionEvent, Camera.name).join(
            Camera, Camera.id == DetectionEvent.camera_id, isouter=True,
        )
        count_stmt = select(func.count()).select_from(DetectionEvent)

        def _apply(s):
            if camera_id is not None:
                s = s.where(DetectionEvent.camera_id == camera_id)
            if object_class is not None:
                s = s.where(DetectionEvent.object_class == object_class)
            if classes_in:
                s = s.where(DetectionEvent.object_class.in_(classes_in))
            if min_confidence is not None:
                s = s.where(DetectionEvent.confidence >= min_confidence)
            if start is not None:
                s = s.where(DetectionEvent.occurred_at >= start)
            if end is not None:
                s = s.where(DetectionEvent.occurred_at <= end)
            return s

        stmt = (
            _apply(stmt)
            .order_by(desc(DetectionEvent.occurred_at))
            .offset(offset)
            .limit(limit)
        )
        count_stmt = _apply(count_stmt)

        rows = (await self.session.execute(stmt)).all()
        items = [(r[0], r[1]) for r in rows]
        total = int((await self.session.execute(count_stmt)).scalar_one())
        return items, total
