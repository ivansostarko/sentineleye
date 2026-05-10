"""Per-camera recorder that segments output via FFmpeg."""

from __future__ import annotations

import asyncio
import os
import re
import shlex
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

import httpx
import structlog

from app.config import get_settings

log = structlog.get_logger(__name__)

# Sources matching this look like a V4L2 device path (USB camera). A bare
# integer like "0" is also accepted and normalised to "/dev/video0".
_V4L2_PATH_RE = re.compile(r"^/dev/video\d+$")


def _is_v4l2_source(source: str) -> bool:
    return bool(_V4L2_PATH_RE.match(source) or source.isdigit())


def _normalise_v4l2(source: str) -> str:
    """Turn `0` / `1` into `/dev/video0` / `/dev/video1`.

    Anything that already looks like a path passes through unchanged.
    """
    return f"/dev/video{source}" if source.isdigit() else source


class CameraRecorder:
    """Continuous segment recorder.

    Spawns one ffmpeg process per camera that splits output into N-second
    fragments using `-f segment`. After each segment is closed on disk,
    the recorder POSTs metadata to the backend.
    """

    def __init__(
        self,
        camera_id: UUID,
        source: str,
        *,
        config: dict[str, Any] | None = None,
    ) -> None:
        self.camera_id = camera_id
        self.source = source
        # Camera.config blob from the backend — lets USB cameras pin the
        # v4l2 input_format / video_size / framerate that ffmpeg should
        # request. Optional; sensible defaults if absent.
        self.config: dict[str, Any] = config or {}
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
        cmd = ["ffmpeg", "-hide_banner", "-loglevel", "warning"]

        if _is_v4l2_source(self.source):
            # ── USB / V4L2 input ────────────────────────────────────────
            # Order matters here: input-format/video-size/framerate must
            # appear BEFORE `-i` so ffmpeg applies them when probing the
            # device, not as output options.
            cfg = self.config
            input_format = cfg.get("v4l2_input_format", "mjpeg")
            video_size   = cfg.get("v4l2_video_size",   "1280x720")
            framerate    = cfg.get("v4l2_framerate",    15)

            cmd += [
                "-f", "v4l2",
                "-input_format", str(input_format),
                "-video_size", str(video_size),
                "-framerate", str(framerate),
                "-i", _normalise_v4l2(self.source),
                # V4L2 webcams have no audio track — telling ffmpeg up
                # front avoids a failed audio-encoder init.
                "-an",
                "-c:v", s.recording_video_codec,
                "-preset", s.recording_preset,
            ]
        else:
            # ── RTSP / RTMP / HTTP / MJPEG ──────────────────────────────
            cmd += [
                "-rtsp_transport", "tcp",  # ignored by non-RTSP, harmless
                "-i", self.source,
                "-c:v", s.recording_video_codec,
                "-preset", s.recording_preset,
                "-c:a", s.recording_audio_codec,
            ]

        # Common segmenter tail.
        cmd += [
            "-f", "segment",
            "-segment_time", str(s.recording_segment_seconds),
            "-segment_format", s.recording_format,
            "-reset_timestamps", "1",
            "-strftime", "1",
            self._segment_pattern,
        ]
        return cmd

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
