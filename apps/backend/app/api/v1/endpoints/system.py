"""System health, info, and configuration endpoints."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends

from app import __version__
from app.api.v1.deps import get_current_user, require_role, system_config_service
from app.core.config import get_settings
from app.models.user import User, UserRole
from app.schemas.system_config import AppVersion, SystemConfigPublic, SystemConfigUpdate
from app.services.cache import get_cache
from app.services.system_config_service import SystemConfigService

router = APIRouter(prefix="/system", tags=["system"])


@router.get("/info")
async def info() -> dict[str, str]:
    s = get_settings()
    return {
        "name": "SentinelEye",
        "version": __version__,
        "environment": s.environment,
    }


@router.get("/version", response_model=AppVersion)
async def version() -> AppVersion:
    """Lightweight unauthenticated endpoint the frontend hits at startup."""
    s = get_settings()
    return AppVersion(name="SentinelEye", version=__version__, environment=s.environment)


def _to_public(entity, *, secret_set: bool) -> SystemConfigPublic:
    return SystemConfigPublic(
        storage_mode=entity.storage_mode,
        local_storage_path=entity.local_storage_path,
        s3_endpoint_url=entity.s3_endpoint_url,
        s3_region=entity.s3_region,
        s3_bucket=entity.s3_bucket,
        s3_access_key=entity.s3_access_key,
        s3_use_ssl=entity.s3_use_ssl,
        s3_signed_url_ttl=entity.s3_signed_url_ttl,
        retention_days=entity.retention_days,
        detection_classes=list(entity.detection_classes or []),
        s3_secret_set=secret_set,
        created_at=entity.created_at,
        updated_at=entity.updated_at,
    )


@router.get(
    "/config",
    response_model=SystemConfigPublic,
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
async def get_config(
    service: Annotated[SystemConfigService, Depends(system_config_service)],
) -> SystemConfigPublic:
    cached = await service.get_cached_payload()
    if cached is not None:
        return SystemConfigPublic.model_validate(cached)
    entity = await service.get()
    public = _to_public(entity, secret_set=SystemConfigService.secret_is_set(entity))
    await service.cache_payload(public.model_dump(mode="json"))
    return public


@router.patch(
    "/config",
    response_model=SystemConfigPublic,
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
async def update_config(
    payload: SystemConfigUpdate,
    service: Annotated[SystemConfigService, Depends(system_config_service)],
    _user: Annotated[User, Depends(get_current_user)],
) -> SystemConfigPublic:
    entity = await service.update(payload)
    return _to_public(entity, secret_set=SystemConfigService.secret_is_set(entity))


# ─── Cache observability + admin ──────────────────────────────────────
@router.get(
    "/cache/stats",
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
async def cache_stats() -> dict[str, Any]:
    """Hit/miss counters, key count for our namespace, memory used."""
    return await get_cache().stats()


@router.post(
    "/cache/invalidate",
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
async def cache_invalidate(pattern: str = "*") -> dict[str, Any]:
    """Drop every key matching ``pattern`` (default ``*`` = whole namespace).

    Useful after a manual data fix. Pattern is a Redis glob — e.g.
    ``cameras:*`` or ``cameras:id:<uuid>``.
    """
    deleted = await get_cache().invalidate(pattern)
    return {"pattern": pattern, "deleted": deleted}
