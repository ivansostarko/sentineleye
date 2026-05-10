"""Tracker unit tests."""

from __future__ import annotations

from app.detectors import Detection
from app.trackers.iou_tracker import IoUTracker


def _det(x: float, y: float, w: float, h: float, *, cls_id: int = 0) -> Detection:
    return Detection(
        class_id=cls_id,
        class_name="person",
        confidence=0.9,
        xyxy=(x, y, x + w, y + h),
    )


def test_tracker_assigns_stable_ids_across_frames() -> None:
    t = IoUTracker(iou_threshold=0.3, max_age=5)
    f0 = t.update([_det(0, 0, 100, 100), _det(200, 200, 100, 100)], frame_idx=0)
    f1 = t.update([_det(5, 5, 100, 100), _det(205, 205, 100, 100)], frame_idx=1)
    assert {tr.track_id for tr in f0} == {tr.track_id for tr in f1}


def test_tracker_spawns_new_id_for_new_object() -> None:
    t = IoUTracker()
    f0 = t.update([_det(0, 0, 50, 50)], frame_idx=0)
    f1 = t.update([_det(0, 0, 50, 50), _det(500, 500, 50, 50)], frame_idx=1)
    assert len({tr.track_id for tr in f0} | {tr.track_id for tr in f1}) == 2
