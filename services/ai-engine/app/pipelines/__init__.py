"""Per-camera inference pipeline.

A pipeline:
  1. Pulls frames from the source (RTSP/USB/etc) via OpenCV
  2. Runs the detector
  3. Runs the tracker
  4. POSTs detection events to the backend
  5. Optionally publishes preview frames to Redis for live WS clients
"""

from __future__ import annotations

import asyncio
import base64
import time
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import cv2
import httpx
import numpy as np

from app.config import get_settings
from app.detectors import Detection
from app.detectors.registry import get_detector
from app.logging import get_logger
from app.trackers.iou_tracker import IoUTracker

log = get_logger(__name__)


class CameraPipeline:
    def __init__(self, camera_id: UUID, source: str, *, target_fps: int = 15) -> None:
        self.camera_id = camera_id
        self.source = source
        self.target_fps = target_fps
        self._stop = asyncio.Event()
        self._tracker = IoUTracker()
        self._detector = get_detector()

    async def run(self) -> None:
        settings = get_settings()
        cap = cv2.VideoCapture(self.source)
        if not cap.isOpened():
            log.error("pipeline.open_failed", source=self.source)
            return

        log.info("pipeline.start", camera_id=str(self.camera_id), source=self.source)
        frame_idx = 0
        period = 1.0 / max(1, self.target_fps)
        async with httpx.AsyncClient(base_url=settings.backend_url, timeout=10.0) as client:
            try:
                while not self._stop.is_set():
                    t0 = time.monotonic()
                    ok, frame = cap.read()
                    if not ok:
                        log.warning("pipeline.frame_drop", camera_id=str(self.camera_id))
                        await asyncio.sleep(0.5)
                        continue

                    detections = self._detector.infer(frame)
                    tracks = self._tracker.update(detections, frame_idx)

                    if detections:
                        await self._dispatch(client, frame, detections, tracks)

                    frame_idx += 1
                    elapsed = time.monotonic() - t0
                    if elapsed < period:
                        await asyncio.sleep(period - elapsed)
            finally:
                cap.release()
                log.info("pipeline.stopped", camera_id=str(self.camera_id))

    def stop(self) -> None:
        self._stop.set()

    async def _dispatch(
        self,
        client: httpx.AsyncClient,
        frame: np.ndarray,
        detections: list[Detection],
        tracks: list[Any],
    ) -> None:
        h, w = frame.shape[:2]
        now = datetime.now(UTC).isoformat()

        # Snapshot only the highest-confidence detection per dispatch to control IO.
        best = max(detections, key=lambda d: d.confidence)
        snapshot_b64 = _encode_jpeg(frame)

        for track in tracks:
            d = track.detection
            payload = {
                "camera_id": str(self.camera_id),
                "occurred_at": now,
                "object_class": d.class_name,
                "confidence": d.confidence,
                "track_id": track.track_id,
                "bbox": d.normalized(w, h),
                "snapshot_key": None,  # backend will assign once stored
            }
            try:
                await client.post(
                    "/api/v1/detection-events",
                    json=payload,
                    headers={"Authorization": f"Bearer {get_settings().backend_service_token}"},
                )
            except httpx.HTTPError as exc:
                log.warning("pipeline.dispatch_failed", error=str(exc))

        log.debug(
            "pipeline.detections",
            camera_id=str(self.camera_id),
            count=len(detections),
            best_class=best.class_name,
            snapshot_bytes=len(snapshot_b64),
        )


def _encode_jpeg(frame: np.ndarray, quality: int = 70) -> str:
    ok, buf = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
    if not ok:
        return ""
    return base64.b64encode(buf.tobytes()).decode("ascii")
