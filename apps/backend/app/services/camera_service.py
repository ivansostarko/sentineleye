"""Camera management orchestration."""

from __future__ import annotations

from uuid import UUID

from app.core.exceptions import NotFoundError
from app.db.repositories.camera import CameraRepository
from app.models.camera import Camera
from app.schemas.camera import CameraCreate, CameraUpdate


class CameraService:
    def __init__(self, cameras: CameraRepository) -> None:
        self.cameras = cameras

    async def create(self, payload: CameraCreate) -> Camera:
        camera = Camera(**payload.model_dump())
        return await self.cameras.add(camera)

    async def get(self, camera_id: UUID) -> Camera:
        camera = await self.cameras.get(camera_id)
        if camera is None:
            raise NotFoundError(f"Camera {camera_id} not found.")
        return camera

    async def list(self, *, offset: int, limit: int) -> tuple[list[Camera], int]:
        items = await self.cameras.list(offset=offset, limit=limit)
        total = await self.cameras.count()
        return items, total

    async def update(self, camera_id: UUID, payload: CameraUpdate) -> Camera:
        camera = await self.get(camera_id)
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(camera, field, value)
        await self.cameras.session.flush()
        return camera

    async def delete(self, camera_id: UUID) -> None:
        camera = await self.get(camera_id)
        await self.cameras.delete(camera)
