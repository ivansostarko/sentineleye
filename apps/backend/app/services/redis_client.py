"""Shared Redis client (async)."""

from __future__ import annotations

from functools import lru_cache

from redis.asyncio import Redis, from_url

from app.core.config import get_settings


@lru_cache
def get_redis() -> Redis:
    return from_url(str(get_settings().redis_url), decode_responses=True)


async def close_redis() -> None:
    redis = get_redis()
    await redis.close()
