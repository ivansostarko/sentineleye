"""Pre-populate the Redis cache with the hot read paths.

Run ad-hoc after a deploy or on a schedule to keep the dashboard responsive
even right after `redis-cli FLUSHDB` or a Redis restart. Targets the same
keys the API endpoints would write through ``CameraService`` and
``SystemConfigService``, so the next API hit is a cache hit.

Usage (inside the backend container):
    python -m app.scripts.warm_cache
    python -m app.scripts.warm_cache --pages 3 --page-size 50
    python -m app.scripts.warm_cache --no-cameras --no-system-config
    python -m app.scripts.warm_cache --quiet

Exit codes:
    0 — at least one target succeeded
    1 — all targets failed (Redis or DB unreachable, etc.)
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import time
from dataclasses import dataclass

from app.core.logging import get_logger
from app.db.repositories.camera import CameraRepository
from app.db.repositories.cloud_integration import CloudIntegrationRepository
from app.db.repositories.system_config import SystemConfigRepository
from app.db.session import _SessionLocal
from app.schemas.system_config import SystemConfigPublic
from app.services.cache import get_cache
from app.services.camera_service import CameraService
from app.services.redis_client import close_redis
from app.services.system_config_service import SystemConfigService

log = get_logger(__name__)


@dataclass
class WarmStat:
    target: str
    items: int
    elapsed_ms: float
    ok: bool
    error: str | None = None

    def render(self) -> str:
        status = "OK " if self.ok else "ERR"
        suffix = f" ({self.error})" if self.error else ""
        return (
            f"  [{status}] {self.target:<24} "
            f"items={self.items:<5}  {self.elapsed_ms:6.1f} ms{suffix}"
        )


async def _warm_cameras(*, pages: int, page_size: int) -> list[WarmStat]:
    """Warm the camera-list pages and every individual camera by id.

    For a 12-camera setup with page_size=50 you get 1 list cache + 12
    per-id caches — both shapes the API serves.
    """
    stats: list[WarmStat] = []

    async with _SessionLocal() as session:
        cameras_repo = CameraRepository(session)
        integrations_repo = CloudIntegrationRepository(session)
        service = CameraService(cameras_repo, integrations_repo)

        # ── List pages ─────────────────────────────────────────────
        for page in range(1, pages + 1):
            t0 = time.perf_counter()
            try:
                items, _total = await service.list_public_cached(
                    offset=(page - 1) * page_size, limit=page_size,
                )
                stats.append(WarmStat(
                    target=f"cameras:list page={page}",
                    items=len(items),
                    elapsed_ms=(time.perf_counter() - t0) * 1000,
                    ok=True,
                ))
                if not items:
                    break  # past the end
            except Exception as exc:  # noqa: BLE001
                stats.append(WarmStat(
                    target=f"cameras:list page={page}",
                    items=0,
                    elapsed_ms=(time.perf_counter() - t0) * 1000,
                    ok=False,
                    error=str(exc),
                ))
                break

        # ── Per-id ─────────────────────────────────────────────────
        # Pull all camera IDs in one query, then warm each one.
        try:
            all_cameras = await cameras_repo.list(offset=0, limit=10_000)
        except Exception as exc:  # noqa: BLE001
            stats.append(WarmStat(
                target="cameras:id (enum)", items=0, elapsed_ms=0.0,
                ok=False, error=str(exc),
            ))
            return stats

        t0 = time.perf_counter()
        warmed = 0
        first_err: str | None = None
        for camera in all_cameras:
            try:
                await service.get_public_cached(camera.id)
                warmed += 1
            except Exception as exc:  # noqa: BLE001
                first_err = first_err or str(exc)
        stats.append(WarmStat(
            target="cameras:id (each)",
            items=warmed,
            elapsed_ms=(time.perf_counter() - t0) * 1000,
            ok=warmed == len(all_cameras),
            error=first_err if warmed < len(all_cameras) else None,
        ))

    return stats


async def _warm_system_config() -> WarmStat:
    """Warm the system-config singleton."""
    t0 = time.perf_counter()
    async with _SessionLocal() as session:
        repo = SystemConfigRepository(session)
        service = SystemConfigService(repo)
        try:
            entity = await service.get()
            public = SystemConfigPublic(
                storage_mode=entity.storage_mode,
                local_storage_path=entity.local_storage_path,
                s3_endpoint_url=entity.s3_endpoint_url,
                s3_region=entity.s3_region,
                s3_bucket=entity.s3_bucket,
                s3_access_key=entity.s3_access_key,
                s3_use_ssl=entity.s3_use_ssl,
                s3_signed_url_ttl=entity.s3_signed_url_ttl,
                retention_days=entity.retention_days,
                detection_classes=list(entity.detection_classes or []),
                s3_secret_set=SystemConfigService.secret_is_set(entity),
                created_at=entity.created_at,
                updated_at=entity.updated_at,
            )
            await service.cache_payload(public.model_dump(mode="json"))
            return WarmStat(
                target="system_config",
                items=1,
                elapsed_ms=(time.perf_counter() - t0) * 1000,
                ok=True,
            )
        except Exception as exc:  # noqa: BLE001
            return WarmStat(
                target="system_config",
                items=0,
                elapsed_ms=(time.perf_counter() - t0) * 1000,
                ok=False,
                error=str(exc),
            )


async def warm(
    *,
    cameras: bool = True,
    system_config: bool = True,
    pages: int = 3,
    page_size: int = 50,
    quiet: bool = False,
) -> list[WarmStat]:
    """Run the configured warmers and return a list of stats."""
    stats: list[WarmStat] = []

    if not quiet:
        cache = get_cache()
        print(f"▸ Cache namespace: {cache.namespace}")
        before = await cache.stats()
        print(f"▸ Keys before: {before['keys_in_namespace']}")

    if system_config:
        stats.append(await _warm_system_config())
    if cameras:
        stats.extend(await _warm_cameras(pages=pages, page_size=page_size))

    if not quiet:
        for s in stats:
            print(s.render())
        after = await get_cache().stats()
        ok_count = sum(1 for s in stats if s.ok)
        total_items = sum(s.items for s in stats if s.ok)
        print(
            f"▸ Done: {ok_count}/{len(stats)} targets · "
            f"{total_items} entries warmed · "
            f"keys after: {after['keys_in_namespace']}"
        )

    return stats


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="python -m app.scripts.warm_cache",
        description="Pre-populate the Redis cache for SentinelEye's hot read paths.",
    )
    p.add_argument("--no-cameras", action="store_true",
                   help="Skip warming camera caches.")
    p.add_argument("--no-system-config", action="store_true",
                   help="Skip warming the system_config singleton.")
    p.add_argument("--pages", type=int, default=3,
                   help="How many list-pages to warm (default: 3).")
    p.add_argument("--page-size", type=int, default=50,
                   help="Page size for camera list (default: 50).")
    p.add_argument("--quiet", action="store_true",
                   help="Only print on error; useful for cron.")
    return p.parse_args()


async def _main() -> int:
    args = _parse_args()
    try:
        stats = await warm(
            cameras=not args.no_cameras,
            system_config=not args.no_system_config,
            pages=args.pages,
            page_size=args.page_size,
            quiet=args.quiet,
        )
    finally:
        await close_redis()

    if not stats:
        return 1
    if all(not s.ok for s in stats):
        # Everything failed → exit non-zero so cron / CI surfaces it.
        if args.quiet:
            for s in stats:
                print(s.render(), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(_main()))
