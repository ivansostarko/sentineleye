#!/usr/bin/env bash
# scripts/seed-detections.sh — populate fake detection events across cameras
# over the past N days. Each detection also runs through AlertService so the
# /events Alerts tab gets meaningful history.
#
# Idempotent: matches on (camera_id, occurred_at, object_class, track_id) so
# re-running doesn't double-up. Use a different DAYS arg to widen the window.

set -euo pipefail

DAYS="${1:-3}"

docker compose exec -T backend python - <<PY
import asyncio
import random
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.db.repositories.alert import AlertRuleRepository
from app.db.repositories.alert_event import AlertEventRepository
from app.db.session import _SessionLocal
from app.models.camera import Camera
from app.models.detection_event import DetectionEvent
from app.services.alert_service import AlertService

DAYS = $DAYS

# Realistic class mix for an outdoor surveillance scene. Higher weights = more
# common detections. Confidence skews high for vehicles + person, lower for
# small/distant classes.
CLASS_WEIGHTS = [
    ("person", 35, (0.62, 0.96)),
    ("car", 22, (0.70, 0.97)),
    ("truck", 7, (0.65, 0.93)),
    ("motorcycle", 5, (0.55, 0.90)),
    ("bus", 3, (0.55, 0.92)),
    ("bicycle", 8, (0.45, 0.88)),
    ("dog", 6, (0.55, 0.92)),
    ("cat", 4, (0.50, 0.85)),
    ("bird", 5, (0.40, 0.78)),
    ("backpack", 3, (0.45, 0.75)),
    ("handbag", 2, (0.45, 0.72)),
]


def _pick_class(rng):
    weights = [w for _, w, _ in CLASS_WEIGHTS]
    label, _, conf_range = rng.choices(CLASS_WEIGHTS, weights=weights, k=1)[0]
    confidence = rng.uniform(*conf_range)
    return label, confidence


async def main():
    created = 0
    skipped = 0
    fired = 0
    async with _SessionLocal() as session:
        cams = (await session.execute(select(Camera).order_by(Camera.created_at))).scalars().all()
        if not cams:
            print("no cameras — run scripts/seed-demo.sh first")
            return

        rng = random.Random(2026)
        now = datetime.now(timezone.utc)

        # Build the alert service so seeded detections also get evaluated
        # against existing rules — populates the Alerts tab.
        rules_repo = AlertRuleRepository(session)
        events_repo = AlertEventRepository(session)
        alerts = AlertService(rules_repo, events_repo)

        # Generate ~20 detections per camera per day, time-clustered so they
        # look like real activity bursts.
        per_day = 20
        for cam in cams:
            for d in range(DAYS):
                day_start = now - timedelta(days=DAYS - d)
                for _ in range(per_day):
                    when = day_start + timedelta(
                        hours=rng.uniform(0, 24),
                        seconds=rng.randint(0, 59),
                    )
                    if when >= now:
                        continue
                    cls, conf = _pick_class(rng)
                    track_id = rng.randint(1, 9999)

                    # Match key for idempotence.
                    exists = (
                        await session.execute(
                            select(DetectionEvent.id).where(
                                DetectionEvent.camera_id == cam.id,
                                DetectionEvent.occurred_at == when,
                                DetectionEvent.object_class == cls,
                                DetectionEvent.track_id == track_id,
                            )
                        )
                    ).first()
                    if exists is not None:
                        skipped += 1
                        continue

                    bbox = {
                        "x": rng.uniform(0.05, 0.6),
                        "y": rng.uniform(0.05, 0.6),
                        "w": rng.uniform(0.1, 0.3),
                        "h": rng.uniform(0.1, 0.3),
                    }
                    ev = DetectionEvent(
                        camera_id=cam.id,
                        occurred_at=when,
                        object_class=cls,
                        confidence=conf,
                        track_id=track_id,
                        bbox=bbox,
                        snapshot_key=None,
                        recording_id=None,
                    )
                    session.add(ev)
                    await session.flush()  # so ev.id is populated
                    created += 1

                    # Run rule evaluation (best-effort — AlertService swallows
                    # downstream notification failures).
                    try:
                        produced = await alerts.evaluate_detection(ev)
                        fired += len(produced)
                    except Exception as exc:
                        # Don't let alert eval break the seed.
                        print("alert-eval skipped:", exc)

        await session.commit()

    print(
        f"seed-detections: created={created} skipped={skipped} "
        f"alert_events_fired={fired} cameras={len(cams)} days={DAYS}",
    )


asyncio.run(main())
PY

echo
echo "✓ Detection seed complete."
