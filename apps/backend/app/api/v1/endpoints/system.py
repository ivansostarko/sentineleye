"""System health & info endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from app.core.config import get_settings

router = APIRouter(prefix="/system", tags=["system"])


@router.get("/info")
async def info() -> dict[str, str]:
    s = get_settings()
    return {
        "name": "SentinelEye",
        "version": "0.1.0",
        "environment": s.environment,
        "storage_mode": s.storage_mode,
    }
