"""Recording service settings."""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    recording_host: str = "0.0.0.0"
    recording_port: int = 8200
    backend_url: str = "http://backend:8000"
    backend_service_token: str = "change-me"

    local_storage_path: str = "/data/recordings"
    recording_segment_seconds: int = 300
    recording_format: str = "mp4"
    recording_video_codec: str = "libx264"
    recording_audio_codec: str = "aac"
    recording_preset: str = "veryfast"

    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
