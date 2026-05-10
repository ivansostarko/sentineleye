# CLAUDE.md — AI Engine

> Read the root [CLAUDE.md](../../CLAUDE.md) first.

## Responsibilities

- Pull frames from each enabled camera
- Run object detection (YOLOv8+) at the configured FPS
- Track objects across frames (ByteTrack / IoU fallback)
- POST detection events to the backend
- Optionally publish low-FPS preview frames to Redis for live WS clients

This service is **stateless**. All persistence happens through the backend.

## Layout

```
app/
├── main.py              # FastAPI control plane (start/stop pipelines)
├── config.py            # settings (model, device, thresholds)
├── logging.py
├── detectors/
│   ├── __init__.py      # Detector ABC + Detection dataclass
│   ├── yolo.py          # Ultralytics YOLO adapter
│   └── registry.py      # singleton factory
├── trackers/
│   ├── __init__.py      # Tracker ABC + Track dataclass
│   └── iou_tracker.py   # default IoU-based tracker
└── pipelines/
    └── __init__.py      # CameraPipeline orchestrator
```

## Adding a New Model

1. Drop weights into `services/ai-engine/models/`.
2. Subclass `Detector` (see `app/detectors/yolo.py` as a reference).
3. Wire it in `app/detectors/registry.py` (read `YOLO_MODEL` env var to pick).
4. Update `services/ai-engine/CLAUDE.md` and the `docs/` AI section.

## GPU Notes

- Set `ENABLE_GPU=true` and `YOLO_DEVICE=cuda:0`.
- The base Docker image is CPU-only; for CUDA, use `nvidia/cuda:12.4.0-runtime-ubuntu22.04`
  and install `torch` with the matching CUDA wheel.
- For TensorRT, export with `yolo export model=yolov8n.pt format=engine` and
  set `YOLO_MODEL=yolov8n.engine`.

## Performance Rules

- Don't `cv2.imshow` anywhere — headless.
- Frames flow detector → tracker → dispatch in **one** asyncio task per camera.
  Don't spawn threads for inference.
- Snapshot encoding is JPEG q=70 by default. Bumping quality is rarely worth it.
- POST to backend is fire-and-forget; never block the inference loop on it.
