#!/usr/bin/env bash
# scripts/seed-recordings.sh — populate demo recordings across the seeded
# cameras for the past N days. Useful for poking at the playback UI.
#
# Idempotent: matches by (camera_id, started_at) and skips dupes.

set -euo pipefail

DAYS="${1:-3}"

docker compose exec -T backend python - <<PY
import asyncio
import random
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select

from app.db.session import _SessionLocal
from app.models.camera import Camera
from app.models.recording import Recording, StorageBackend


DAYS = $DAYS

# Realistic CCTV settings: 5-minute MP4 segments, ~30 MB each, h264.
SEGMENT_SECONDS = 300
SEGMENT_BYTES_MIN = 18_000_000
SEGMENT_BYTES_MAX = 42_000_000
CODECS = ["h264", "h264", "h264", "h265"]


async def main():
    created, skipped = 0, 0
    async with _SessionLocal() as session:
        cams = (await session.execute(select(Camera).order_by(Camera.created_at))).scalars().all()
        if not cams:
            print("no cameras — run scripts/seed-demo.sh first")
            return

        rng = random.Random(42)
        now = datetime.now(timezone.utc)
        # Generate one segment every 15-25 minutes (gaps simulate motion-only
        # recording). Spread across all cameras over the last DAYS days.
        for cam in cams:
            t = now - timedelta(days=DAYS)
            while t < now:
                t += timedelta(minutes=rng.randint(15, 25))
                if t >= now:
                    break

                # Skip if we already seeded this exact (camera, started_at).
                exists = (
                    await session.execute(
                        select(Recording.id).where(
                            Recording.camera_id == cam.id,
                            Recording.started_at == t,
                        )
                    )
                ).first()
                if exists is not None:
                    skipped += 1
                    continue

                ended = t + timedelta(seconds=SEGMENT_SECONDS)
                key = (
                    f"recordings/{cam.id}/"
                    f"{t.strftime('%Y/%m/%d/%H%M%S')}.mp4"
                )
                rec = Recording(
                    camera_id=cam.id,
                    started_at=t,
                    ended_at=ended,
                    duration_seconds=float(SEGMENT_SECONDS),
                    storage_backend=StorageBackend.LOCAL,
                    storage_key=key,
                    bytes_size=rng.randint(SEGMENT_BYTES_MIN, SEGMENT_BYTES_MAX),
                    codec=rng.choice(CODECS),
                )
                session.add(rec)
                created += 1

        await session.commit()
    print(f"seed-recordings: created={created} skipped={skipped} cameras={len(cams)} days={DAYS}")


asyncio.run(main())
PY

echo
echo "✓ Recording seed complete."
