"""AI engine settings."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    ai_engine_host: str = "0.0.0.0"
    ai_engine_port: int = 8100

    backend_url: str = "http://backend:8000"
    backend_service_token: str = "change-me"  # service-to-service token

    redis_url: str = "redis://redis:6379/0"

    yolo_model: str = "yolov8n.pt"
    yolo_device: Literal["auto", "cpu"] | str = "auto"
    yolo_confidence: float = 0.45
    yolo_iou: float = 0.50
    yolo_img_size: int = 640
    tracker: Literal["bytetrack", "deepsort"] = "bytetrack"
    enable_gpu: bool = False

    log_level: str = "INFO"
    prometheus_enabled: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
