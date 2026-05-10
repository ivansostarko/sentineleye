"""Camera management orchestration."""

from __future__ import annotations

from uuid import UUID

from app.core.exceptions import AppError, NotFoundError
from app.core.logging import get_logger
from app.db.repositories.camera import CameraRepository
from app.db.repositories.cloud_integration import CloudIntegrationRepository
from app.models.camera import Camera, CameraProtocol
from app.models.cloud_integration import CloudProvider
from app.schemas.camera import CameraCreate, CameraPublic, CameraUpdate
from app.services import crypto
from app.services.cache import TTL_MEDIUM, TTL_SHORT, Cache, Keys, get_cache
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
        cache: Cache | None = None,
    ) -> None:
        self.cameras = cameras
        self.integrations = integrations
        self._recording = recording or RecordingClient()
        self._ai_engine = ai_engine or AiEngineClient()
        self._cache = cache or get_cache()

    # ── CRUD ─────────────────────────────────────────────────────────
    async def create(self, payload: CameraCreate) -> Camera:
        camera = Camera(**payload.model_dump())
        await self.cameras.add(camera)
        await self.cameras.session.flush()  # populate camera.id
        await self._reconcile(camera, prev_record=False, prev_detect=False)
        # Server-side defaults (created_at, updated_at) are written by Postgres
        # but not visible on the in-memory ORM object until we refresh. Without
        # this, `CameraPublic.model_validate(camera, from_attributes=True)`
        # triggers a sync lazy-load and blows up with `MissingGreenlet` under
        # the async session.
        await self.cameras.session.refresh(camera)
        await self._cache.invalidate(Keys.CAMERAS_ALL)
        return camera

    async def get(self, camera_id: UUID) -> Camera:
        camera = await self.cameras.get(camera_id)
        if camera is None:
            raise NotFoundError(f"Camera {camera_id} not found.")
        return camera

    async def get_public_cached(self, camera_id: UUID) -> CameraPublic:
        """Read-through cached lookup returning the API schema directly.

        The endpoint layer should prefer this over ``get()`` — a hit avoids
        the DB round-trip entirely and skips ORM hydration.
        """
        cached = await self._cache.get(Keys.camera(camera_id))
        if cached is not None:
            return CameraPublic.model_validate(cached)
        camera = await self.get(camera_id)
        public = CameraPublic.model_validate(camera, from_attributes=True)
        await self._cache.set(
            Keys.camera(camera_id),
            public.model_dump(mode="json"),
            ttl_seconds=TTL_MEDIUM,
        )
        return public

    async def list(self, *, offset: int, limit: int) -> tuple[list[Camera], int]:
        items = await self.cameras.list(offset=offset, limit=limit)
        total = await self.cameras.count()
        return items, total

    async def list_public_cached(
        self, *, offset: int, limit: int,
    ) -> tuple[list[CameraPublic], int]:
        """Cached paginated list. Short TTL — dashboard refreshes every 30s."""
        cached = await self._cache.get(Keys.camera_list(offset, limit))
        if cached is not None:
            return (
                [CameraPublic.model_validate(c) for c in cached["items"]],
                int(cached["total"]),
            )
        items, total = await self.list(offset=offset, limit=limit)
        publics = [CameraPublic.model_validate(c, from_attributes=True) for c in items]
        await self._cache.set(
            Keys.camera_list(offset, limit),
            {"items": [p.model_dump(mode="json") for p in publics], "total": total},
            ttl_seconds=TTL_SHORT,
        )
        return publics, total

    async def update(self, camera_id: UUID, payload: CameraUpdate) -> Camera:
        camera = await self.get(camera_id)
        prev_record = camera.record_continuous and camera.enabled
        prev_detect = camera.detection_enabled and camera.enabled

        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(camera, field, value)
        await self.cameras.session.flush()

        # `_reconcile` may itself flush (Tuya URL refresh) so we let it run
        # first, then refresh once at the end.
        await self._reconcile(camera, prev_record=prev_record, prev_detect=prev_detect)
        # `updated_at` has onupdate=func.now() — server picked the new value.
        # Pull it back so `_to_public` and the warmer don't trigger lazy-load
        # outside the async greenlet (raises `MissingGreenlet` otherwise).
        await self.cameras.session.refresh(camera)
        await self._cache.invalidate(Keys.CAMERAS_ALL)
        return camera

    async def delete(self, camera_id: UUID) -> None:
        camera = await self.get(camera_id)
        await self._recording.stop(str(camera.id))
        await self._ai_engine.stop(str(camera.id))
        await self.cameras.delete(camera)
        await self._cache.invalidate(Keys.CAMERAS_ALL)

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
