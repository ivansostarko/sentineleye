"""Recording repository."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from sqlalchemy import asc, desc, func, select

from app.db.repositories.base import BaseRepository
from app.models.camera import Camera
from app.models.recording import Recording

SortBy = Literal["started_at", "duration_seconds", "bytes_size"]


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
        """Backwards-compat path used by the recording-service worker."""
        stmt = select(Recording).where(Recording.camera_id == camera_id)
        if start is not None:
            stmt = stmt.where(Recording.started_at >= start)
        if end is not None:
            stmt = stmt.where(Recording.started_at <= end)
        stmt = stmt.order_by(desc(Recording.started_at)).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())

    async def search(
        self,
        *,
        camera_id: UUID | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
        min_duration: float | None = None,
        max_duration: float | None = None,
        query: str | None = None,
        sort_by: SortBy = "started_at",
        sort_desc: bool = True,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[tuple[Recording, str | None]], int]:
        """Generic search returning (recording, camera_name) pairs + total.

        The camera join saves the N+1 the playback list otherwise needs to
        label each row.
        """
        stmt = select(Recording, Camera.name).join(
            Camera, Camera.id == Recording.camera_id, isouter=True,
        )
        count_stmt = select(func.count()).select_from(Recording)

        def _apply(s):
            if camera_id is not None:
                s = s.where(Recording.camera_id == camera_id)
            if start is not None:
                s = s.where(Recording.started_at >= start)
            if end is not None:
                s = s.where(Recording.started_at <= end)
            if min_duration is not None:
                s = s.where(Recording.duration_seconds >= min_duration)
            if max_duration is not None:
                s = s.where(Recording.duration_seconds <= max_duration)
            if query:
                like = f"%{query.strip()}%"
                s = s.where(Recording.storage_key.ilike(like))
            return s

        stmt = _apply(stmt)
        count_stmt = _apply(count_stmt)

        col = {
            "started_at": Recording.started_at,
            "duration_seconds": Recording.duration_seconds,
            "bytes_size": Recording.bytes_size,
        }[sort_by]
        stmt = stmt.order_by(desc(col) if sort_desc else asc(col))
        stmt = stmt.offset(offset).limit(limit)

        rows = (await self.session.execute(stmt)).all()
        items = [(r[0], r[1]) for r in rows]
        total = int((await self.session.execute(count_stmt)).scalar_one())
        return items, total
