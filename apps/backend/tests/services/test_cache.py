"""Tests for the Redis cache abstraction.

Uses an in-process fake Redis to keep the test hermetic — no Redis container
required. The fake implements the small subset of commands the Cache class
touches: GET, SET (with EX), DELETE, SCAN_ITER, INFO.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

import pytest

from app.services.cache import TTL_SHORT, Cache, Keys


# ─── Minimal fake Redis (only what Cache touches) ──────────────────────
class FakeRedis:
    def __init__(self) -> None:
        self._data: dict[str, str] = {}
        self.hits = 0
        self.misses = 0

    async def get(self, key: str) -> str | None:
        if key in self._data:
            self.hits += 1
            return self._data[key]
        self.misses += 1
        return None

    async def set(self, key: str, value: str, ex: int | None = None) -> bool:  # noqa: ARG002
        self._data[key] = value
        return True

    async def delete(self, *keys: str) -> int:
        n = 0
        for k in keys:
            if k in self._data:
                del self._data[k]
                n += 1
        return n

    async def scan_iter(self, match: str, count: int = 100):  # noqa: ARG002
        rx = re.compile("^" + re.escape(match).replace(r"\*", ".*") + "$")
        for k in list(self._data):
            if rx.match(k):
                yield k

    async def info(self, section: str) -> dict[str, Any]:
        if section == "stats":
            return {"keyspace_hits": self.hits, "keyspace_misses": self.misses}
        if section == "memory":
            return {"used_memory": 4096, "used_memory_human": "4.00K"}
        return {}


@pytest.fixture
def cache() -> Cache:
    return Cache(FakeRedis(), namespace="cache:test")


# ─── Round-trip ───────────────────────────────────────────────────────
async def test_set_get_roundtrip(cache: Cache) -> None:
    await cache.set("foo", {"a": 1, "b": "two"}, ttl_seconds=60)
    assert await cache.get("foo") == {"a": 1, "b": "two"}


async def test_miss_returns_none(cache: Cache) -> None:
    assert await cache.get("missing") is None


# ─── JSON encoding for project types ──────────────────────────────────
async def test_handles_uuid_and_datetime(cache: Cache) -> None:
    cid = uuid4()
    when = datetime(2026, 5, 10, 12, 34, 56, tzinfo=timezone.utc)
    await cache.set("event", {"id": cid, "at": when}, ttl_seconds=60)

    got = await cache.get("event")
    assert got["id"] == str(cid)
    assert got["at"].startswith("2026-05-10T12:34:56")


async def test_handles_pydantic_models(cache: Cache) -> None:
    from pydantic import BaseModel

    class M(BaseModel):
        x: int
        y: str

    await cache.set("m", M(x=7, y="hi"), ttl_seconds=60)
    assert await cache.get("m") == {"x": 7, "y": "hi"}


# ─── Invalidation ─────────────────────────────────────────────────────
async def test_delete_specific_keys(cache: Cache) -> None:
    await cache.set("a", 1)
    await cache.set("b", 2)
    deleted = await cache.delete("a", "missing")
    assert deleted == 1
    assert await cache.get("a") is None
    assert await cache.get("b") == 2


async def test_invalidate_pattern_matches_glob(cache: Cache) -> None:
    await cache.set("cameras:id:abc", {"n": 1})
    await cache.set("cameras:id:xyz", {"n": 2})
    await cache.set("cameras:list:offset=0:limit=50", {"items": []})
    await cache.set("system_config", {"k": "v"})

    deleted = await cache.invalidate("cameras:*")
    assert deleted == 3
    assert await cache.get("cameras:id:abc") is None
    assert await cache.get("system_config") == {"k": "v"}  # untouched


# ─── get_or_set read-through ──────────────────────────────────────────
async def test_get_or_set_caches_factory_result(cache: Cache) -> None:
    calls = 0

    async def factory() -> dict[str, int]:
        nonlocal calls
        calls += 1
        return {"computed": 42}

    a = await cache.get_or_set("derived", factory, ttl_seconds=TTL_SHORT)
    b = await cache.get_or_set("derived", factory, ttl_seconds=TTL_SHORT)

    assert a == b == {"computed": 42}
    assert calls == 1, "factory should only run on miss"


async def test_get_or_set_skips_caching_when_factory_returns_none(
    cache: Cache,
) -> None:
    async def factory() -> None:
        return None

    assert await cache.get_or_set("nope", factory) is None
    # Was nothing stored — still missing.
    assert await cache.get("nope") is None


# ─── Stats ────────────────────────────────────────────────────────────
async def test_stats_counts_namespace_keys(cache: Cache) -> None:
    await cache.set("a", 1)
    await cache.set("b", 2)
    stats = await cache.stats()
    assert stats["namespace"] == "cache:test"
    assert stats["keys_in_namespace"] == 2
    assert "memory_used_human" in stats
    assert 0.0 <= stats["hit_rate"] <= 1.0


# ─── Key builders are stable ──────────────────────────────────────────
def test_camera_key_includes_id() -> None:
    cid = UUID("00000000-0000-0000-0000-000000000001")
    assert Keys.camera(cid) == f"cameras:id:{cid}"


def test_camera_list_key_includes_pagination() -> None:
    assert Keys.camera_list(0, 50) == "cameras:list:offset=0:limit=50"


def test_system_config_key_is_singleton() -> None:
    assert Keys.system_config() == "system_config"


def test_invalidation_patterns_match_their_keys() -> None:
    cid = uuid4()
    rx = re.compile(
        "^" + re.escape(Keys.CAMERAS_ALL).replace(r"\*", ".*") + "$"
    )
    assert rx.match(Keys.camera(cid))
    assert rx.match(Keys.camera_list(0, 50))
    assert rx.match(Keys.camera_count())
