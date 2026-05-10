"""Application settings — sourced from environment / .env."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, PostgresDsn, RedisDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Strongly-typed application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ─── Environment ───────────────────────────────────────────
    environment: Literal["development", "staging", "production"] = "development"
    log_level: str = "INFO"

    # ─── HTTP ──────────────────────────────────────────────────
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    backend_public_url: str = "http://localhost:8000"
    cors_origins: str = ""

    # ─── Auth ──────────────────────────────────────────────────
    secret_key: str = Field(min_length=32)
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 14
    jwt_algorithm: str = "HS256"

    # ─── Database ──────────────────────────────────────────────
    database_url: PostgresDsn

    # ─── Redis ─────────────────────────────────────────────────
    redis_url: RedisDsn
    celery_broker_url: str
    celery_result_backend: str

    # ─── Storage ───────────────────────────────────────────────
    storage_mode: Literal["local", "s3", "hybrid"] = "hybrid"
    local_storage_path: str = "/data/recordings"
    retention_days: int = 14
    archive_after_days: int = 2

    # ─── S3 / MinIO ────────────────────────────────────────────
    s3_endpoint_url: str | None = None
    s3_region: str = "us-east-1"
    s3_bucket: str = "sentineleye-recordings"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_use_ssl: bool = False
    s3_signed_url_ttl: int = 3600

    # ─── Service URLs ──────────────────────────────────────────
    ai_engine_url: str = "http://ai-engine:8100"
    recording_service_url: str = "http://recording-service:8200"
    notification_service_url: str = "http://notification-service:8300"

    # ─── Observability ─────────────────────────────────────────
    prometheus_enabled: bool = True
    sentry_dsn: str | None = None

    @property
    def cors_origins_list(self) -> list[str]:
        if not self.cors_origins:
            return []
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()  # type: ignore[call-arg]
