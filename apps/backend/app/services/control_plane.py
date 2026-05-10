"""HTTP control-plane clients for downstream services.

The recording-service and ai-engine are stateless workers that don't read the
DB themselves — the backend tells them which cameras to record and which to
analyse. These clients are intentionally best-effort: if a downstream service
is unreachable, we log a warning and let the camera CRUD operation succeed.
The reconciler (future work) can re-sync state on the next pass.
"""

from __future__ import annotations

import httpx

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.camera import Camera

log = get_logger(__name__)


def _camera_source(camera: Camera) -> str:
    """Build the URL that downstream services pass to FFmpeg/OpenCV.

    For protocols that authenticate inside the URL (rtsp/rtmp/http/mjpeg),
    we splice user:pass into the URL if creds were provided out-of-band.
    """
    url = camera.url
    if not (camera.username or camera.password):
        return url
    if camera.protocol in {"rtsp", "rtmp", "http", "mjpeg"} and "://" in url:
        scheme, rest = url.split("://", 1)
        if "@" in rest.split("/", 1)[0]:  # creds already embedded
            return url
        creds = f"{camera.username or ''}:{camera.password or ''}"
        return f"{scheme}://{creds}@{rest}"
    return url


class _BaseControlClient:
    def __init__(self, base_url: str, *, name: str, timeout: float = 5.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._name = name
        self._timeout = timeout

    async def _post(self, path: str, json: dict | None = None) -> None:
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                r = await client.post(f"{self._base_url}{path}", json=json)
                if r.status_code >= 400:
                    log.warning(
                        "control_plane.error",
                        service=self._name, path=path,
                        status=r.status_code, body=r.text[:200],
                    )
        except httpx.HTTPError as exc:
            # Best-effort: never block the user request on a downstream outage.
            log.warning(
                "control_plane.unreachable",
                service=self._name, path=path, error=str(exc),
            )


class RecordingClient(_BaseControlClient):
    def __init__(self, base_url: str | None = None) -> None:
        super().__init__(base_url or get_settings().recording_service_url, name="recording")

    async def start(self, camera: Camera) -> None:
        await self._post(
            "/recorders/start",
            json={"camera_id": str(camera.id), "source": _camera_source(camera)},
        )

    async def stop(self, camera_id: str) -> None:
        await self._post(f"/recorders/{camera_id}/stop")


class AiEngineClient(_BaseControlClient):
    def __init__(self, base_url: str | None = None) -> None:
        super().__init__(base_url or get_settings().ai_engine_url, name="ai-engine")

    async def start(self, camera: Camera) -> None:
        await self._post(
            "/pipelines/start",
            json={
                "camera_id": str(camera.id),
                "source": _camera_source(camera),
                "target_fps": camera.target_fps,
            },
        )

    async def stop(self, camera_id: str) -> None:
        await self._post(f"/pipelines/{camera_id}/stop")
