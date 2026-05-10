"""Camera repository."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select

from app.db.repositories.base import BaseRepository
from app.models.camera import Camera


class CameraRepository(BaseRepository[Camera]):
    model = Camera

    async def list(  # type: ignore[override]
        self,
        *,
        offset: int = 0,
        limit: int = 50,
        order_by: Any | None = None,
    ) -> list[Camera]:
        """Override base list() so cameras come back in user-defined order.

        The grid relies on a stable order; sorting by `display_order` then
        `created_at` matches the supporting index added in 0006_pinord.
        """
        stmt = (
            select(Camera)
            .order_by(Camera.display_order, Camera.created_at)
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_enabled(self) -> list[Camera]:
        result = await self.session.execute(
            select(Camera)
            .where(Camera.enabled.is_(True))
            .order_by(Camera.display_order, Camera.created_at),
        )
        return list(result.scalars().all())
