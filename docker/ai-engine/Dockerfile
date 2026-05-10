# NOTE: For GPU support, swap the base image for `nvidia/cuda:12.4.0-runtime-ubuntu22.04`
# and install Python + the CUDA-matched torch wheel.
FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential ffmpeg libgl1 libglib2.0-0 curl \
    && rm -rf /var/lib/apt/lists/*

COPY services/ai-engine/pyproject.toml /app/
RUN pip install --upgrade pip && (pip install -e ".[dev]" \
    || pip install \
        "fastapi>=0.115.0" "uvicorn[standard]>=0.32.0" \
        "pydantic>=2.9.0" "pydantic-settings>=2.5.0" \
        "ultralytics>=8.3.0" "opencv-python-headless>=4.10.0" \
        "numpy>=1.26.0" "torch>=2.4.0" "torchvision>=0.19.0" \
        "lap>=0.5.12" "filterpy>=1.4.5" "scipy>=1.14.0" \
        "httpx>=0.27.2" "redis[hiredis]>=5.1.0" \
        "structlog>=24.4.0" "prometheus-client>=0.21.0" "tenacity>=9.0.0")

COPY services/ai-engine /app

EXPOSE 8100

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -fsS http://localhost:8100/healthz || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8100"]
