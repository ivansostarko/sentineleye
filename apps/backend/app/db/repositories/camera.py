"""Camera repository."""

from __future__ import annotations

from sqlalchemy import select

from app.db.repositories.base import BaseRepository
from app.models.camera import Camera


class CameraRepository(BaseRepository[Camera]):
    model = Camera

    async def list_enabled(self) -> list[Camera]:
        result = await self.session.execute(select(Camera).where(Camera.enabled.is_(True)))
        return list(result.scalars().all())
