"""Camera management orchestration."""

from __future__ import annotations

from uuid import UUID

from app.core.exceptions import NotFoundError
from app.db.repositories.camera import CameraRepository
from app.models.camera import Camera
from app.schemas.camera import CameraCreate, CameraUpdate
from app.services.control_plane import AiEngineClient, RecordingClient


class CameraService:
    """Persists cameras + reconciles downstream recording/AI pipelines.

    Downstream calls are best-effort (see `control_plane`): a recording-service
    or ai-engine outage will not block the CRUD operation. The camera row is
    the source of truth; downstream services can be reconciled from it.
    """

    def __init__(
        self,
        cameras: CameraRepository,
        recording: RecordingClient | None = None,
        ai_engine: AiEngineClient | None = None,
    ) -> None:
        self.cameras = cameras
        self._recording = recording or RecordingClient()
        self._ai_engine = ai_engine or AiEngineClient()

    async def create(self, payload: CameraCreate) -> Camera:
        camera = Camera(**payload.model_dump())
        await self.cameras.add(camera)
        await self.cameras.session.flush()  # populate camera.id
        await self._reconcile(camera, prev_record=False, prev_detect=False)
        return camera

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
        prev_record = camera.record_continuous and camera.enabled
        prev_detect = camera.detection_enabled and camera.enabled

        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(camera, field, value)
        await self.cameras.session.flush()

        await self._reconcile(camera, prev_record=prev_record, prev_detect=prev_detect)
        return camera

    async def delete(self, camera_id: UUID) -> None:
        camera = await self.get(camera_id)
        # Stop downstream first so they don't keep writing to a deleted camera.
        await self._recording.stop(str(camera.id))
        await self._ai_engine.stop(str(camera.id))
        await self.cameras.delete(camera)

    async def _reconcile(
        self, camera: Camera, *, prev_record: bool, prev_detect: bool,
    ) -> None:
        """Diff desired vs previous state and call start/stop accordingly."""
        wants_record = camera.enabled and camera.record_continuous
        wants_detect = camera.enabled and camera.detection_enabled

        if wants_record and not prev_record:
            await self._recording.start(camera)
        elif prev_record and not wants_record:
            await self._recording.stop(str(camera.id))

        if wants_detect and not prev_detect:
            await self._ai_engine.start(camera)
        elif prev_detect and not wants_detect:
            await self._ai_engine.stop(str(camera.id))
