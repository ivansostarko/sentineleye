"""Per-camera recorder that segments output via FFmpeg."""

from __future__ import annotations

import asyncio
import os
import shlex
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import httpx
import structlog

from app.config import get_settings

log = structlog.get_logger(__name__)


class CameraRecorder:
    """Continuous segment recorder.

    Spawns one ffmpeg process per camera that splits output into N-second
    fragments using `-f segment`. After each segment is closed on disk,
    the recorder POSTs metadata to the backend.
    """

    def __init__(self, camera_id: UUID, source: str) -> None:
        self.camera_id = camera_id
        self.source = source
        self._proc: asyncio.subprocess.Process | None = None
        self._watcher: asyncio.Task | None = None
        self._stop = asyncio.Event()
        self.settings = get_settings()
        self.out_dir = Path(self.settings.local_storage_path) / str(camera_id)
        self.out_dir.mkdir(parents=True, exist_ok=True)

    @property
    def _segment_pattern(self) -> str:
        # ffmpeg-friendly pattern; includes camera id for safety.
        return str(self.out_dir / f"%Y%m%dT%H%M%SZ.{self.settings.recording_format}")

    def _build_ffmpeg_cmd(self) -> list[str]:
        s = self.settings
        # Note: -strftime 1 enables strftime in -segment output filenames.
        return [
            "ffmpeg",
            "-hide_banner",
            "-loglevel", "warning",
            "-rtsp_transport", "tcp",
            "-i", self.source,
            "-c:v", s.recording_video_codec,
            "-preset", s.recording_preset,
            "-c:a", s.recording_audio_codec,
            "-f", "segment",
            "-segment_time", str(s.recording_segment_seconds),
            "-segment_format", s.recording_format,
            "-reset_timestamps", "1",
            "-strftime", "1",
            self._segment_pattern,
        ]

    async def start(self) -> None:
        cmd = self._build_ffmpeg_cmd()
        log.info("recorder.start", camera_id=str(self.camera_id), cmd=" ".join(shlex.quote(c) for c in cmd))
        self._proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )
        self._watcher = asyncio.create_task(self._watch_segments())

    async def stop(self) -> None:
        self._stop.set()
        if self._proc and self._proc.returncode is None:
            self._proc.terminate()
            try:
                await asyncio.wait_for(self._proc.wait(), timeout=10)
            except TimeoutError:
                self._proc.kill()
                await self._proc.wait()
        if self._watcher:
            self._watcher.cancel()
            try:
                await self._watcher
            except asyncio.CancelledError:
                pass
        log.info("recorder.stop", camera_id=str(self.camera_id))

    async def _watch_segments(self) -> None:
        """Poll the output directory and report newly closed segments."""
        seen: set[str] = set()
        async with httpx.AsyncClient(base_url=self.settings.backend_url, timeout=10.0) as client:
            while not self._stop.is_set():
                files = sorted(self.out_dir.glob(f"*.{self.settings.recording_format}"))
                # Skip the most recent file — ffmpeg may still be writing it.
                for path in files[:-1]:
                    if path.name in seen:
                        continue
                    seen.add(path.name)
                    await self._report_segment(client, path)
                await asyncio.sleep(2.0)

    async def _report_segment(self, client: httpx.AsyncClient, path: Path) -> None:
        try:
            stat = path.stat()
        except FileNotFoundError:
            return
        # Filename pattern: 20251225T143000Z.mp4
        try:
            ts = datetime.strptime(path.stem, "%Y%m%dT%H%M%SZ").replace(tzinfo=UTC)
        except ValueError:
            ts = datetime.fromtimestamp(stat.st_mtime, tz=UTC)

        payload = {
            "camera_id": str(self.camera_id),
            "started_at": ts.isoformat(),
            "duration_seconds": float(self.settings.recording_segment_seconds),
            "storage_backend": "local",
            "storage_key": os.path.relpath(path, self.settings.local_storage_path),
            "bytes_size": stat.st_size,
            "codec": self.settings.recording_video_codec,
        }
        try:
            await client.post(
                "/api/v1/_internal/recordings",
                json=payload,
                headers={"Authorization": f"Bearer {self.settings.backend_service_token}"},
            )
            log.info("recorder.segment", camera_id=str(self.camera_id), key=payload["storage_key"])
        except httpx.HTTPError as exc:
            log.warning("recorder.report_failed", error=str(exc))
