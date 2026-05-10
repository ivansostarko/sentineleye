"""FastAPI application entrypoint for the SentinelEye backend."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging, get_logger
from app.db.session import close_engine, ping_database
from app.services.redis_client import close_redis, get_redis

settings = get_settings()
configure_logging(settings.log_level)
log = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Startup / shutdown hooks."""
    log.info("backend.startup", env=settings.environment)
    await ping_database()
    await get_redis().ping()
    yield
    log.info("backend.shutdown")
    await close_redis()
    await close_engine()


def create_app() -> FastAPI:
    app = FastAPI(
        title="SentinelEye API",
        version="0.1.0",
        description="Open-source AI CCTV surveillance platform.",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)

    app.include_router(api_router, prefix="/api/v1")

    if settings.prometheus_enabled:
        app.mount("/metrics", make_asgi_app())

    @app.get("/healthz", tags=["health"])
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/readyz", tags=["health"])
    async def readyz() -> dict[str, str]:
        await ping_database()
        await get_redis().ping()
        return {"status": "ready"}

    return app


app = create_app()
