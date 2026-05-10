"""YOLOv8/v9/v10/11 detector via Ultralytics."""

from __future__ import annotations

import numpy as np

from app.config import get_settings
from app.detectors import Detection, Detector
from app.logging import get_logger

log = get_logger(__name__)


class YOLODetector(Detector):
    def __init__(self) -> None:
        from ultralytics import YOLO  # local import; keeps cold start small for tests

        s = get_settings()
        self._device = self._resolve_device(s.yolo_device, s.enable_gpu)
        log.info("yolo.load", model=s.yolo_model, device=self._device)
        self._model = YOLO(s.yolo_model)
        self._conf = s.yolo_confidence
        self._iou = s.yolo_iou
        self._imgsz = s.yolo_img_size
        self._names: dict[int, str] = self._model.names  # type: ignore[assignment]

    @staticmethod
    def _resolve_device(device: str, enable_gpu: bool) -> str:
        if device != "auto":
            return device
        try:
            import torch

            if enable_gpu and torch.cuda.is_available():
                return "cuda:0"
        except Exception:
            pass
        return "cpu"

    @property
    def class_names(self) -> dict[int, str]:
        return self._names

    def infer(self, frame: np.ndarray) -> list[Detection]:
        results = self._model.predict(
            frame,
            conf=self._conf,
            iou=self._iou,
            imgsz=self._imgsz,
            device=self._device,
            verbose=False,
        )
        if not results:
            return []
        r = results[0]
        if r.boxes is None or len(r.boxes) == 0:
            return []

        out: list[Detection] = []
        xyxy = r.boxes.xyxy.cpu().numpy()
        confs = r.boxes.conf.cpu().numpy()
        cls = r.boxes.cls.cpu().numpy().astype(int)
        for i in range(len(xyxy)):
            cid = int(cls[i])
            out.append(
                Detection(
                    class_id=cid,
                    class_name=self._names.get(cid, str(cid)),
                    confidence=float(confs[i]),
                    xyxy=(float(xyxy[i, 0]), float(xyxy[i, 1]), float(xyxy[i, 2]), float(xyxy[i, 3])),
                )
            )
        return out
