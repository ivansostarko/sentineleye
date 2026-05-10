"""SystemConfig repository — single-row pattern."""

from __future__ import annotations

from sqlalchemy import select

from app.db.repositories.base import BaseRepository
from app.models.system_config import SystemConfig


class SystemConfigRepository(BaseRepository[SystemConfig]):
    model = SystemConfig
    SINGLETON_ID = 1

    async def get_singleton(self) -> SystemConfig:
        """Return the (only) config row. Raises if the seed migration hasn't run."""
        result = await self.session.execute(
            select(SystemConfig).where(SystemConfig.id == self.SINGLETON_ID)
        )
        row = result.scalar_one_or_none()
        if row is None:
            raise RuntimeError(
                "system_config row missing — migration 0004_sysconf must run first."
            )
        return row
