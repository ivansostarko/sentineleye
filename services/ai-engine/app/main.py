"""AI engine HTTP API — start/stop pipelines per camera."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncIterator
from uuid import UUID

from fastapi import FastAPI, HTTPException
from prometheus_client import make_asgi_app
from pydantic import BaseModel

from app.config import get_settings
from app.logging import configure_logging, get_logger
from app.pipelines import CameraPipeline

settings = get_settings()
configure_logging(settings.log_level)
log = get_logger(__name__)

# Active pipelines keyed by camera id.
_pipelines: dict[UUID, tuple[CameraPipeline, asyncio.Task]] = {}


class StartRequest(BaseModel):
    camera_id: UUID
    source: str
    target_fps: int = 15


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    log.info("ai-engine.startup", model=settings.yolo_model)
    yield
    for cid, (pipe, task) in _pipelines.items():
        pipe.stop()
        task.cancel()
        log.info("ai-engine.pipeline.stop", camera_id=str(cid))
    await asyncio.gather(*(t for _, t in _pipelines.values()), return_exceptions=True)


app = FastAPI(title="SentinelEye AI Engine", version="0.1.0", lifespan=lifespan)


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok", "model": settings.yolo_model}


@app.post("/pipelines/start")
async def start_pipeline(req: StartRequest) -> dict[str, str]:
    if req.camera_id in _pipelines:
        raise HTTPException(409, "Pipeline already running for that camera.")
    pipe = CameraPipeline(req.camera_id, req.source, target_fps=req.target_fps)
    task = asyncio.create_task(pipe.run())
    _pipelines[req.camera_id] = (pipe, task)
    return {"status": "started", "camera_id": str(req.camera_id)}


@app.post("/pipelines/{camera_id}/stop")
async def stop_pipeline(camera_id: UUID) -> dict[str, str]:
    entry = _pipelines.pop(camera_id, None)
    if entry is None:
        raise HTTPException(404, "No pipeline running for that camera.")
    pipe, task = entry
    pipe.stop()
    task.cancel()
    return {"status": "stopped", "camera_id": str(camera_id)}


@app.get("/pipelines")
async def list_pipelines() -> list[str]:
    return [str(c) for c in _pipelines.keys()]


if settings.prometheus_enabled:
    app.mount("/metrics", make_asgi_app())
