FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
    && rm -rf /var/lib/apt/lists/*

COPY services/notification-service/pyproject.toml /app/
RUN pip install --upgrade pip && (pip install -e ".[dev]" \
    || pip install \
        "fastapi>=0.115.0" "uvicorn[standard]>=0.32.0" \
        "pydantic>=2.9.0" "pydantic-settings>=2.5.0" \
        "httpx>=0.27.2" "aiosmtplib>=3.0.2" "redis[hiredis]>=5.1.0" \
        "structlog>=24.4.0" "tenacity>=9.0.0" "jinja2>=3.1.4")

COPY services/notification-service /app

EXPOSE 8300

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -fsS http://localhost:8300/healthz || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8300"]
