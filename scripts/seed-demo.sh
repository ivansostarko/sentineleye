#!/usr/bin/env bash
# scripts/seed-demo.sh — insert a handful of demo cameras for the map.
#
# Idempotent: re-running won't duplicate rows (matches by name).
# Coordinates are around Zagreb, HR — adjust to your actual locale by editing
# the CAMERAS list below.

set -euo pipefail

docker compose exec -T backend python - <<'PY'
import asyncio
from app.db.session import _SessionLocal
from app.db.repositories.camera import CameraRepository
from app.db.repositories.cloud_integration import CloudIntegrationRepository
from app.services.camera_service import CameraService
from app.schemas.camera import CameraCreate
from app.models.camera import CameraProtocol
from sqlalchemy import select
from app.models.camera import Camera

CAMERAS = [
    {
        "name": "Front Gate",
        "location": "Trg bana Josipa Jelačića, Zagreb",
        "latitude": 45.8131,
        "longitude": 15.9775,
        "protocol": CameraProtocol.RTSP,
        "url": "rtsp://demo.local:554/front_gate",
        "pinned_to_dashboard": True,
    },
    {
        "name": "Parking Lot",
        "location": "Cvjetni trg, Zagreb",
        "latitude": 45.8121,
        "longitude": 15.9760,
        "protocol": CameraProtocol.ONVIF,
        "url": "http://demo.local:8080/onvif/device_service",
        "pinned_to_dashboard": True,
    },
    {
        "name": "Loading Dock",
        "location": "Zrinjevac, Zagreb",
        "latitude": 45.8108,
        "longitude": 15.9785,
        "protocol": CameraProtocol.RTSP,
        "url": "rtsp://demo.local:554/loading_dock",
        "pinned_to_dashboard": False,
    },
    {
        "name": "Reception",
        "location": "Britanski trg, Zagreb",
        "latitude": 45.8136,
        "longitude": 15.9682,
        "protocol": CameraProtocol.RTSP,
        "url": "rtsp://demo.local:554/reception",
        "pinned_to_dashboard": False,
    },
]


async def main():
    created, skipped = 0, 0
    async with _SessionLocal() as session:
        cameras = CameraRepository(session)
        integrations = CloudIntegrationRepository(session)
        # Bypass the orchestration during seed — we don't need to call out to
        # recording-service or ai-engine for demo rows.
        from unittest.mock import AsyncMock
        svc = CameraService(
            cameras, integrations,
            recording=AsyncMock(),
            ai_engine=AsyncMock(),
        )
        for c in CAMERAS:
            existing = (
                await session.execute(select(Camera).where(Camera.name == c["name"]))
            ).scalar_one_or_none()
            if existing is not None:
                skipped += 1
                continue
            await svc.create(CameraCreate(
                name=c["name"],
                location=c["location"],
                latitude=c["latitude"],
                longitude=c["longitude"],
                protocol=c["protocol"],
                url=c["url"],
                enabled=True,
                record_continuous=False,
                detection_enabled=False,
                target_fps=10,
                pinned_to_dashboard=c.get("pinned_to_dashboard", False),
            ))
            created += 1
        await session.commit()
    print(f"seed: created={created} skipped={skipped}")


asyncio.run(main())
PY

echo
echo "✓ Demo seed complete."
