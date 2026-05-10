"""Cloud integration management endpoints (admin-only)."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.api.v1.deps import cloud_integration_service, get_current_user, require_role
from app.models.user import User, UserRole
from app.schemas.cloud_integration import (
    CloudIntegrationCreate,
    CloudIntegrationPublic,
    CloudIntegrationUpdate,
)
from app.schemas.common import Page
from app.services.cloud_integration_service import CloudIntegrationService

router = APIRouter(prefix="/cloud-integrations", tags=["cloud-integrations"])


def _to_public(entity) -> CloudIntegrationPublic:
    return CloudIntegrationPublic.model_validate(entity, from_attributes=True)


@router.get(
    "",
    response_model=Page[CloudIntegrationPublic],
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
async def list_integrations(
    service: Annotated[CloudIntegrationService, Depends(cloud_integration_service)],
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
) -> Page[CloudIntegrationPublic]:
    items, total = await service.list(offset=(page - 1) * size, limit=size)
    return Page[CloudIntegrationPublic](
        items=[_to_public(i) for i in items], total=total, page=page, size=size,
    )


@router.post(
    "",
    response_model=CloudIntegrationPublic,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
async def create_integration(
    payload: CloudIntegrationCreate,
    service: Annotated[CloudIntegrationService, Depends(cloud_integration_service)],
) -> CloudIntegrationPublic:
    return _to_public(await service.create(payload))


@router.get(
    "/{integration_id}",
    response_model=CloudIntegrationPublic,
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
async def get_integration(
    integration_id: UUID,
    service: Annotated[CloudIntegrationService, Depends(cloud_integration_service)],
) -> CloudIntegrationPublic:
    return _to_public(await service.get(integration_id))


@router.patch(
    "/{integration_id}",
    response_model=CloudIntegrationPublic,
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
async def update_integration(
    integration_id: UUID,
    payload: CloudIntegrationUpdate,
    service: Annotated[CloudIntegrationService, Depends(cloud_integration_service)],
) -> CloudIntegrationPublic:
    return _to_public(await service.update(integration_id, payload))


@router.delete(
    "/{integration_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
async def delete_integration(
    integration_id: UUID,
    service: Annotated[CloudIntegrationService, Depends(cloud_integration_service)],
    _user: Annotated[User, Depends(get_current_user)],
) -> None:
    await service.delete(integration_id)
