# Development Guide

## Prereqs

- Python 3.12+
- Flutter 3.24+
- Docker 24+
- `ruff`, `mypy`, `pytest` (installed via `pip install -e ".[dev]"` in each Python project)

## The dev loop

```bash
# Bring up infra only (postgres, redis, minio) — run apps natively for fast reload.
docker compose up -d postgres redis minio minio-init

# Backend
cd apps/backend
source .venv/bin/activate
alembic upgrade head
uvicorn app.main:app --reload --port 8000

# AI engine (separate terminal)
cd services/ai-engine
source .venv/bin/activate
uvicorn app.main:app --reload --port 8100

# Recording service (separate terminal)
cd services/recording-service
source .venv/bin/activate
uvicorn app.main:app --reload --port 8200

# Notification service (separate terminal)
cd services/notification-service
source .venv/bin/activate
uvicorn app.main:app --reload --port 8300

# Flutter
cd apps/frontend
flutter run -d chrome
```

## Testing

```bash
# Backend tests
cd apps/backend && pytest -q

# AI engine tests
cd services/ai-engine && pytest -q

# Flutter tests
cd apps/frontend && flutter test
```

## Linting / formatting

```bash
ruff check .
ruff format .
mypy app  # strict on new modules
```

```bash
cd apps/frontend
dart format .
flutter analyze
```

## Migrations

```bash
cd apps/backend
alembic revision --autogenerate -m "add my new column"
# inspect the generated file, edit if needed
alembic upgrade head
```

## Branch / commit conventions

- Branches: `feat/<scope>-<short>`, `fix/<scope>-<short>`, `chore/...`, `docs/...`
- Commits: [Conventional Commits](https://www.conventionalcommits.org/)
  - `feat(backend): add camera search by location`
  - `fix(ai-engine): handle 0-detection frames without crash`
  - `chore(deps): bump ultralytics to 8.3.0`

## Adding a new service or env var

1. Add it to `.env.example`.
2. Add it to `docker-compose.yml`.
3. Add it to `app/core/config.py` (or the equivalent in the service).
4. Document it in `docs/ARCHITECTURE.md` if it's a new component.
5. Update the root `CLAUDE.md` if it changes a project-wide convention.

## Local CCTV simulator

If you don't have a real RTSP camera handy, use ffmpeg to push a sample file:

```bash
# Endless looped MP4 over RTSP, served by mediamtx (formerly rtsp-simple-server)
docker run --rm -p 8554:8554 bluenviron/mediamtx
ffmpeg -re -stream_loop -1 -i sample.mp4 \
  -c copy -f rtsp rtsp://localhost:8554/stream1
```

Then create a camera with URL `rtsp://host.docker.internal:8554/stream1`.
