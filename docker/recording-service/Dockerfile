FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg curl \
    && rm -rf /var/lib/apt/lists/*

COPY services/recording-service/pyproject.toml /app/
RUN pip install --upgrade pip && (pip install -e ".[dev]" \
    || pip install \
        "fastapi>=0.115.0" "uvicorn[standard]>=0.32.0" \
        "pydantic>=2.9.0" "pydantic-settings>=2.5.0" \
        "httpx>=0.27.2" "boto3>=1.35.0" "structlog>=24.4.0" \
        "prometheus-client>=0.21.0" "tenacity>=9.0.0" "aiofiles>=24.1.0")

COPY services/recording-service /app

EXPOSE 8200

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -fsS http://localhost:8200/healthz || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8200"]
