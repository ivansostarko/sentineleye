"""Recording repository."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import desc, select

from app.db.repositories.base import BaseRepository
from app.models.recording import Recording


class RecordingRepository(BaseRepository[Recording]):
    model = Recording

    async def list_for_camera(
        self,
        camera_id: UUID,
        *,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int = 100,
    ) -> list[Recording]:
        stmt = select(Recording).where(Recording.camera_id == camera_id)
        if start is not None:
            stmt = stmt.where(Recording.started_at >= start)
        if end is not None:
            stmt = stmt.where(Recording.started_at <= end)
        stmt = stmt.order_by(desc(Recording.started_at)).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())
