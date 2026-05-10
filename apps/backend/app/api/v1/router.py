"""Aggregate router for API v1."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.endpoints import (
    alert_events,
    alerts,
    auth,
    cameras,
    cloud_integrations,
    detection_events,
    notification_settings,
    recordings,
    system,
    system_admin,
    websockets,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(cameras.router)
api_router.include_router(cloud_integrations.router)
api_router.include_router(detection_events.router)
api_router.include_router(recordings.router)
api_router.include_router(alerts.router)
api_router.include_router(alert_events.router)
api_router.include_router(notification_settings.router)
api_router.include_router(system.router)
api_router.include_router(system_admin.router)
api_router.include_router(websockets.router)
