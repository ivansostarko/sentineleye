"""Camera management endpoints."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.api.v1.deps import camera_service, get_current_user, require_role
from app.models.user import User, UserRole
from app.schemas.camera import CameraCreate, CameraPublic, CameraUpdate
from app.schemas.common import Page
from app.services.camera_service import CameraService

router = APIRouter(prefix="/cameras", tags=["cameras"])


def _to_public(camera) -> CameraPublic:
    return CameraPublic.model_validate(camera, from_attributes=True)


@router.get("", response_model=Page[CameraPublic])
async def list_cameras(
    service: Annotated[CameraService, Depends(camera_service)],
    _user: Annotated[User, Depends(get_current_user)],
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
) -> Page[CameraPublic]:
    items, total = await service.list(offset=(page - 1) * size, limit=size)
    return Page[CameraPublic](
        items=[_to_public(c) for c in items], total=total, page=page, size=size
    )


@router.post(
    "",
    response_model=CameraPublic,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(UserRole.ADMIN, UserRole.OPERATOR))],
)
async def create_camera(
    payload: CameraCreate,
    service: Annotated[CameraService, Depends(camera_service)],
) -> CameraPublic:
    return _to_public(await service.create(payload))


@router.get("/{camera_id}", response_model=CameraPublic)
async def get_camera(
    camera_id: UUID,
    service: Annotated[CameraService, Depends(camera_service)],
    _user: Annotated[User, Depends(get_current_user)],
) -> CameraPublic:
    return _to_public(await service.get(camera_id))


@router.patch(
    "/{camera_id}",
    response_model=CameraPublic,
    dependencies=[Depends(require_role(UserRole.ADMIN, UserRole.OPERATOR))],
)
async def update_camera(
    camera_id: UUID,
    payload: CameraUpdate,
    service: Annotated[CameraService, Depends(camera_service)],
) -> CameraPublic:
    return _to_public(await service.update(camera_id, payload))


@router.delete(
    "/{camera_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
async def delete_camera(
    camera_id: UUID,
    service: Annotated[CameraService, Depends(camera_service)],
) -> None:
    await service.delete(camera_id)
