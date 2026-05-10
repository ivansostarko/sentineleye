"""Recording service control plane."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncIterator
from uuid import UUID

import structlog
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app.config import get_settings
from app.recorder import CameraRecorder

log = structlog.get_logger(__name__)
_recorders: dict[UUID, CameraRecorder] = {}


class StartRequest(BaseModel):
    camera_id: UUID
    source: str


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    log.info("recording-service.startup")
    yield
    await asyncio.gather(*(r.stop() for r in _recorders.values()), return_exceptions=True)


app = FastAPI(title="SentinelEye Recording Service", version="0.1.0", lifespan=lifespan)


@app.get("/healthz")
async def healthz() -> dict[str, object]:
    s = get_settings()
    return {"status": "ok", "active_recorders": len(_recorders), "storage": s.local_storage_path}


@app.post("/recorders/start")
async def start_recorder(req: StartRequest) -> dict[str, str]:
    if req.camera_id in _recorders:
        raise HTTPException(409, "Recorder already running for that camera.")
    rec = CameraRecorder(req.camera_id, req.source)
    await rec.start()
    _recorders[req.camera_id] = rec
    return {"status": "started", "camera_id": str(req.camera_id)}


@app.post("/recorders/{camera_id}/stop")
async def stop_recorder(camera_id: UUID) -> dict[str, str]:
    rec = _recorders.pop(camera_id, None)
    if rec is None:
        raise HTTPException(404, "No recorder running for that camera.")
    await rec.stop()
    return {"status": "stopped", "camera_id": str(camera_id)}


@app.get("/recorders")
async def list_recorders() -> list[str]:
    return [str(c) for c in _recorders.keys()]
