"""Cloud integration repository."""

from __future__ import annotations

from sqlalchemy import select

from app.db.repositories.base import BaseRepository
from app.models.cloud_integration import CloudIntegration, CloudProvider


class CloudIntegrationRepository(BaseRepository[CloudIntegration]):
    model = CloudIntegration

    async def first_for(
        self, provider: CloudProvider, *, only_enabled: bool = True
    ) -> CloudIntegration | None:
        """Return the first integration of the given provider.

        We support multiple integrations per provider conceptually, but the
        common case (and what the UI exposes today) is one. Use this on the
        hot path; richer selection logic can come later.
        """
        stmt = select(CloudIntegration).where(CloudIntegration.provider == provider)
        if only_enabled:
            stmt = stmt.where(CloudIntegration.enabled.is_(True))
        result = await self.session.execute(stmt.order_by(CloudIntegration.created_at).limit(1))
        return result.scalar_one_or_none()
