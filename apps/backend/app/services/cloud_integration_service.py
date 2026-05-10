"""Cloud integration CRUD orchestration."""

from __future__ import annotations

from uuid import UUID

from app.core.exceptions import NotFoundError
from app.db.repositories.cloud_integration import CloudIntegrationRepository
from app.models.cloud_integration import CloudIntegration, CloudProvider
from app.schemas.cloud_integration import CloudIntegrationCreate, CloudIntegrationUpdate
from app.services import crypto


class CloudIntegrationService:
    """Persists cloud-provider credentials with field-level encryption."""

    def __init__(self, repo: CloudIntegrationRepository) -> None:
        self.repo = repo

    async def create(self, payload: CloudIntegrationCreate) -> CloudIntegration:
        entity = CloudIntegration(
            provider=payload.provider,
            name=payload.name,
            region=payload.region,
            enabled=payload.enabled,
            access_id_enc=crypto.encrypt(payload.access_id),
            access_secret_enc=crypto.encrypt(payload.access_secret),
        )
        return await self.repo.add(entity)

    async def get(self, integration_id: UUID) -> CloudIntegration:
        entity = await self.repo.get(integration_id)
        if entity is None:
            raise NotFoundError(f"Cloud integration {integration_id} not found.")
        return entity

    async def list(self, *, offset: int, limit: int) -> tuple[list[CloudIntegration], int]:
        items = await self.repo.list(offset=offset, limit=limit)
        total = await self.repo.count()
        return items, total

    async def update(
        self, integration_id: UUID, payload: CloudIntegrationUpdate
    ) -> CloudIntegration:
        entity = await self.get(integration_id)
        data = payload.model_dump(exclude_unset=True)

        # Re-encrypt the rotated secrets, never store plaintext.
        if "access_id" in data:
            entity.access_id_enc = crypto.encrypt(data.pop("access_id"))
        if "access_secret" in data:
            entity.access_secret_enc = crypto.encrypt(data.pop("access_secret"))
        for field, value in data.items():
            setattr(entity, field, value)

        await self.repo.session.flush()
        return entity

    async def delete(self, integration_id: UUID) -> None:
        entity = await self.get(integration_id)
        await self.repo.delete(entity)

    async def first_decrypted(
        self, provider: CloudProvider
    ) -> tuple[CloudIntegration, str, str] | None:
        """Return (integration, access_id, access_secret) for the active integration
        of the given provider, or None if no enabled integration exists."""
        entity = await self.repo.first_for(provider)
        if entity is None:
            return None
        return entity, crypto.decrypt(entity.access_id_enc), crypto.decrypt(entity.access_secret_enc)
