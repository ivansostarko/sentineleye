"""SystemConfig service — encrypts S3 secret on write, decrypts on read."""

from __future__ import annotations

from app.db.repositories.system_config import SystemConfigRepository
from app.models.system_config import SystemConfig
from app.schemas.system_config import SystemConfigUpdate
from app.services import crypto

# Sentinel string written by the seed migration so we know no real secret has
# been provided yet — surfaces as `s3_secret_set: false` in the API response.
_SECRET_PLACEHOLDER = "__seed_placeholder__"


class SystemConfigService:
    def __init__(self, repo: SystemConfigRepository) -> None:
        self.repo = repo

    async def get(self) -> SystemConfig:
        return await self.repo.get_singleton()

    async def update(self, payload: SystemConfigUpdate) -> SystemConfig:
        entity = await self.get()
        data = payload.model_dump(exclude_unset=True)

        if "s3_secret_key" in data:
            entity.s3_secret_key_enc = crypto.encrypt(data.pop("s3_secret_key"))

        for field, value in data.items():
            setattr(entity, field, value)

        await self.repo.session.flush()
        return entity

    @staticmethod
    def secret_is_set(entity: SystemConfig) -> bool:
        return entity.s3_secret_key_enc != _SECRET_PLACEHOLDER

    @classmethod
    def decrypt_secret(cls, entity: SystemConfig) -> str | None:
        """Return the plaintext S3 secret, or None if no real secret is set."""
        if not cls.secret_is_set(entity):
            return None
        try:
            return crypto.decrypt(entity.s3_secret_key_enc)
        except Exception:  # noqa: BLE001 — wrong SECRET_KEY etc.
            return None
