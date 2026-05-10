FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

COPY apps/backend/pyproject.toml /app/
RUN pip install --upgrade pip && pip install -e ".[dev]" \
    || pip install \
        "fastapi>=0.115.0" "uvicorn[standard]>=0.32.0" \
        "pydantic>=2.9.0" "pydantic-settings>=2.5.0" \
        "sqlalchemy[asyncio]>=2.0.35" "asyncpg>=0.29.0" "alembic>=1.13.3" \
        "redis[hiredis]>=5.1.0" "celery>=5.4.0" \
        "passlib[bcrypt]>=1.7.4" "python-jose[cryptography]>=3.3.0" \
        "python-multipart>=0.0.12" "httpx>=0.27.2" "boto3>=1.35.0" \
        "structlog>=24.4.0" "prometheus-client>=0.21.0" \
        "websockets>=13.1" "tenacity>=9.0.0" "email-validator>=2.2.0" \
        "aiofiles>=24.1.0"

COPY apps/backend /app
COPY docker/backend/entrypoint.sh /usr/local/bin/sentineleye-entrypoint
RUN chmod +x /usr/local/bin/sentineleye-entrypoint

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -fsS http://localhost:8000/healthz || exit 1

ENTRYPOINT ["sentineleye-entrypoint"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
