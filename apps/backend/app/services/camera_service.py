"""Camera management orchestration."""

from __future__ import annotations

from uuid import UUID

from app.core.exceptions import AppError, NotFoundError
from app.core.logging import get_logger
from app.db.repositories.camera import CameraRepository
from app.db.repositories.cloud_integration import CloudIntegrationRepository
from app.models.camera import Camera, CameraProtocol
from app.models.cloud_integration import CloudProvider
from app.schemas.camera import CameraCreate, CameraUpdate
from app.services import crypto
from app.services.control_plane import AiEngineClient, RecordingClient
from app.services.tuya_cloud import TuyaClient, TuyaError

log = get_logger(__name__)


class CameraService:
    """Persists cameras + reconciles downstream recording/AI pipelines.

    For LAN-native protocols (RTSP/ONVIF/etc.) the camera URL goes straight
    to the recording-service / ai-engine. For `tuya` cameras the URL is
    allocated dynamically against the Tuya cloud and refreshed periodically
    by `app.workers.tasks.refresh_tuya_streams`.

    Downstream calls are best-effort: a recording-service or ai-engine
    outage will not block the CRUD operation.
    """

    def __init__(
        self,
        cameras: CameraRepository,
        integrations: CloudIntegrationRepository,
        recording: RecordingClient | None = None,
        ai_engine: AiEngineClient | None = None,
    ) -> None:
        self.cameras = cameras
        self.integrations = integrations
        self._recording = recording or RecordingClient()
        self._ai_engine = ai_engine or AiEngineClient()

    # ── CRUD ─────────────────────────────────────────────────────────
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
        await self._recording.stop(str(camera.id))
        await self._ai_engine.stop(str(camera.id))
        await self.cameras.delete(camera)

    # ── Source resolution ────────────────────────────────────────────
    async def resolve_source(self, camera: Camera) -> str | None:
        """Return the URL the recording-service / ai-engine should connect to.

        For Tuya cameras: allocate a fresh stream URL via the Tuya cloud and
        cache it on the camera row. Returns None on resolution failure
        (best-effort; orchestrator logs and skips).
        """
        if camera.protocol != CameraProtocol.TUYA:
            return self._embed_credentials(camera)

        device_id = (camera.config or {}).get("tuya_device_id")
        if not device_id:
            log.warning("camera.tuya_no_device_id", camera_id=str(camera.id))
            return None

        client = await self._tuya_client()
        if client is None:
            log.warning("camera.tuya_no_integration", camera_id=str(camera.id))
            return None
        try:
            url = await client.allocate_stream(device_id, kind="rtsp")
        except TuyaError as exc:
            log.warning("camera.tuya_allocate_failed", camera_id=str(camera.id), error=str(exc))
            return None

        # Cache the URL on the camera row so the recording-service can read it
        # via /api/v1/cameras/{id} at start-up time too.
        camera.url = url
        await self.cameras.session.flush()
        return url

    async def _tuya_client(self) -> TuyaClient | None:
        entity = await self.integrations.first_for(CloudProvider.TUYA)
        if entity is None:
            return None
        return TuyaClient(
            access_id=crypto.decrypt(entity.access_id_enc),
            access_secret=crypto.decrypt(entity.access_secret_enc),
            region=entity.region,
        )

    @staticmethod
    def _embed_credentials(camera: Camera) -> str:
        """Splice user:pass into a URL when stored out-of-band."""
        url = camera.url
        if not (camera.username or camera.password):
            return url
        if camera.protocol.value not in {"rtsp", "rtmp", "http", "mjpeg"} or "://" not in url:
            return url
        scheme, rest = url.split("://", 1)
        if "@" in rest.split("/", 1)[0]:
            return url
        creds = f"{camera.username or ''}:{camera.password or ''}"
        return f"{scheme}://{creds}@{rest}"

    # ── Reconciliation ───────────────────────────────────────────────
    async def _reconcile(
        self, camera: Camera, *, prev_record: bool, prev_detect: bool,
    ) -> None:
        wants_record = camera.enabled and camera.record_continuous
        wants_detect = camera.enabled and camera.detection_enabled

        # Resolve the source URL once if any pipeline needs to start.
        source: str | None = None
        if (wants_record and not prev_record) or (wants_detect and not prev_detect):
            try:
                source = await self.resolve_source(camera)
            except AppError as exc:
                log.warning("camera.source_resolve_failed", camera_id=str(camera.id), error=str(exc))

        if wants_record and not prev_record and source:
            await self._recording.start(camera, source=source)
        elif prev_record and not wants_record:
            await self._recording.stop(str(camera.id))

        if wants_detect and not prev_detect and source:
            await self._ai_engine.start(camera, source=source)
        elif prev_detect and not wants_detect:
            await self._ai_engine.stop(str(camera.id))
