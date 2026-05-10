"""Lightweight IoU-distance tracker.

This is a stand-in for ByteTrack/DeepSORT — it works without external weights and
is fine for low-density scenes. To swap in ByteTrack proper, install the
`yolox`/`bytetrack` package and replace `update()` with their stream tracker.
"""

from __future__ import annotations

from app.detectors import Detection
from app.trackers import Track, Tracker


def _iou(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> float:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    inter_x1 = max(ax1, bx1)
    inter_y1 = max(ay1, by1)
    inter_x2 = min(ax2, bx2)
    inter_y2 = min(ay2, by2)
    iw = max(0.0, inter_x2 - inter_x1)
    ih = max(0.0, inter_y2 - inter_y1)
    inter = iw * ih
    if inter <= 0:
        return 0.0
    a_area = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
    b_area = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
    union = a_area + b_area - inter
    return inter / union if union > 0 else 0.0


class IoUTracker(Tracker):
    def __init__(self, *, iou_threshold: float = 0.3, max_age: int = 30) -> None:
        self.iou_threshold = iou_threshold
        self.max_age = max_age
        self._next_id = 1
        self._active: dict[int, dict] = {}  # id → {bbox, last_seen, class_id}

    def update(self, detections: list[Detection], frame_idx: int) -> list[Track]:
        # Greedy IoU matching by descending detection confidence.
        unmatched_dets = sorted(range(len(detections)), key=lambda i: -detections[i].confidence)
        matched: dict[int, int] = {}  # det_idx → track_id

        for det_idx in unmatched_dets:
            det = detections[det_idx]
            best_id = -1
            best_iou = self.iou_threshold
            for tid, t in self._active.items():
                if tid in matched.values():
                    continue
                if t["class_id"] != det.class_id:
                    continue
                iou = _iou(t["bbox"], det.xyxy)
                if iou > best_iou:
                    best_iou = iou
                    best_id = tid
            if best_id != -1:
                matched[det_idx] = best_id
                self._active[best_id] = {
                    "bbox": det.xyxy,
                    "class_id": det.class_id,
                    "last_seen": frame_idx,
                }

        # Spawn new tracks for unmatched detections.
        for det_idx, det in enumerate(detections):
            if det_idx in matched:
                continue
            tid = self._next_id
            self._next_id += 1
            matched[det_idx] = tid
            self._active[tid] = {
                "bbox": det.xyxy,
                "class_id": det.class_id,
                "last_seen": frame_idx,
            }

        # Reap stale tracks.
        for tid in list(self._active.keys()):
            if frame_idx - self._active[tid]["last_seen"] > self.max_age:
                self._active.pop(tid, None)

        return [Track(track_id=matched[i], detection=detections[i]) for i in range(len(detections))]
