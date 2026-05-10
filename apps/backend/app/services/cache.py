"""Redis-backed read-through cache.

Use this for expensive idempotent reads — paginated lists, singletons, lookup
tables. Mutations should call ``invalidate(pattern)`` against the keys they
touch so the next read repopulates fresh.

Conventions:
  * All keys are prefixed with ``cache:v<schema>:``. Bumping the schema
    integer invalidates every key in one go (handy after a model change).
  * Values are JSON-serialised. Pydantic models, UUIDs and datetimes are
    handled by ``_json_default``; anything else must already be JSON-safe.
  * TTL is mandatory — no infinite caches. Pick from ``TTL_*`` constants
    so tuning happens in one place.
"""

from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal
from functools import lru_cache
from typing import Any, Awaitable, Callable
from uuid import UUID

from redis.asyncio import Redis

from app.core.logging import get_logger
from app.services.redis_client import get_redis

log = get_logger(__name__)

# ─── Schema version ────────────────────────────────────────────────────
# Bump this when the cached *shape* of any value changes incompatibly.
# Old keys remain in Redis but are unreachable; they expire on TTL.
CACHE_SCHEMA_VERSION = 1

# ─── TTL presets (seconds) ─────────────────────────────────────────────
TTL_SHORT = 30           # Hot list views (dashboard, paginated camera list)
TTL_MEDIUM = 5 * 60      # Single-entity lookups (camera by id, settings)
TTL_LONG = 30 * 60       # Slow-changing reference data (model registry)


def _json_default(obj: Any) -> Any:
    """JSON serialiser for the few types Pydantic schemas produce."""
    if hasattr(obj, "model_dump"):
        return obj.model_dump(mode="json")
    if isinstance(obj, (UUID, Decimal)):
        return str(obj)
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError(f"Cannot JSON-serialize {type(obj).__name__}")


class Cache:
    """Thin wrapper around Redis with namespaced keys and JSON values.

    Designed to be cheap to construct (per request) and safe under
    concurrent access — the underlying Redis client is the shared
    pool from :func:`app.services.redis_client.get_redis`.
    """

    def __init__(self, redis: Redis, namespace: str | None = None) -> None:
        self._redis = redis
        self._ns = namespace or f"cache:v{CACHE_SCHEMA_VERSION}"

    # ── Key handling ────────────────────────────────────────────────
    def _k(self, key: str) -> str:
        return f"{self._ns}:{key}"

    @property
    def namespace(self) -> str:
        return self._ns

    # ── Basic ops ───────────────────────────────────────────────────
    async def get(self, key: str) -> Any | None:
        try:
            raw = await self._redis.get(self._k(key))
        except Exception as exc:  # noqa: BLE001 — never let cache break the call
            log.warning("cache.get_failed", key=key, error=str(exc))
            return None
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except (TypeError, json.JSONDecodeError) as exc:
            log.warning("cache.decode_failed", key=key, error=str(exc))
            return None

    async def set(
        self, key: str, value: Any, ttl_seconds: int = TTL_MEDIUM,
    ) -> None:
        try:
            payload = json.dumps(value, default=_json_default)
        except TypeError as exc:
            # Bad value — log loudly. We don't want silent cache misses to
            # mask serialisation bugs.
            log.error("cache.encode_failed", key=key, error=str(exc))
            return
        try:
            await self._redis.set(self._k(key), payload, ex=ttl_seconds)
        except Exception as exc:  # noqa: BLE001
            log.warning("cache.set_failed", key=key, error=str(exc))

    async def delete(self, *keys: str) -> int:
        if not keys:
            return 0
        try:
            return int(await self._redis.delete(*[self._k(k) for k in keys]))
        except Exception as exc:  # noqa: BLE001
            log.warning("cache.delete_failed", keys=list(keys), error=str(exc))
            return 0

    async def invalidate(self, pattern: str) -> int:
        """Delete every key matching ``<ns>:<pattern>`` (SCAN-based, non-blocking).

        ``pattern`` is a Redis glob — usually ``"<entity>:*"``. Returns the
        number of keys deleted.
        """
        full = self._k(pattern)
        deleted = 0
        try:
            async for k in self._redis.scan_iter(match=full, count=200):
                deleted += int(await self._redis.delete(k))
        except Exception as exc:  # noqa: BLE001
            log.warning("cache.invalidate_failed", pattern=pattern, error=str(exc))
        if deleted:
            log.info("cache.invalidated", pattern=pattern, count=deleted)
        return deleted

    async def get_or_set(
        self,
        key: str,
        factory: Callable[[], Awaitable[Any]],
        ttl_seconds: int = TTL_MEDIUM,
    ) -> Any:
        """Read-through helper: return cached value or compute + cache it."""
        cached = await self.get(key)
        if cached is not None:
            return cached
        value = await factory()
        if value is not None:
            await self.set(key, value, ttl_seconds=ttl_seconds)
        return value

    # ── Introspection ───────────────────────────────────────────────
    async def stats(self) -> dict[str, Any]:
        """Return cache hit/miss counters and namespace key count.

        Hit/miss numbers come from the Redis server (``INFO stats``) and
        cover the *whole* DB, not just our namespace — Redis doesn't track
        per-prefix hit rates. Use the namespace key count to reason about
        what *we* contributed.
        """
        info_stats: dict[str, Any] = {}
        info_memory: dict[str, Any] = {}
        try:
            info_stats = await self._redis.info("stats")
            info_memory = await self._redis.info("memory")
        except Exception as exc:  # noqa: BLE001
            log.warning("cache.stats_failed", error=str(exc))

        keys = 0
        try:
            async for _ in self._redis.scan_iter(match=self._k("*"), count=500):
                keys += 1
        except Exception as exc:  # noqa: BLE001
            log.warning("cache.scan_failed", error=str(exc))

        hits = int(info_stats.get("keyspace_hits", 0))
        misses = int(info_stats.get("keyspace_misses", 0))
        total = hits + misses
        hit_rate = (hits / total) if total else 0.0

        return {
            "namespace": self._ns,
            "keys_in_namespace": keys,
            "hits": hits,
            "misses": misses,
            "hit_rate": round(hit_rate, 4),
            "memory_used_human": info_memory.get("used_memory_human"),
            "memory_used_bytes": int(info_memory.get("used_memory", 0)),
        }


# ─── Module-level accessor (singleton) ─────────────────────────────────
@lru_cache
def get_cache() -> Cache:
    """Return the process-wide Cache instance (cheap; backed by shared pool)."""
    return Cache(get_redis())


# ─── Key builders (one place per entity) ───────────────────────────────
# Putting these here means producers (services) and the cache warmer agree
# on the exact key shape. Don't inline f-strings at call sites.
class Keys:
    @staticmethod
    def camera(camera_id: Any) -> str:
        return f"cameras:id:{camera_id}"

    @staticmethod
    def camera_list(offset: int, limit: int) -> str:
        return f"cameras:list:offset={offset}:limit={limit}"

    @staticmethod
    def camera_count() -> str:
        return "cameras:count"

    @staticmethod
    def system_config() -> str:
        return "system_config"

    # Patterns (use with `Cache.invalidate`)
    CAMERAS_ALL = "cameras:*"
    SYSTEM_CONFIG_ALL = "system_config*"
