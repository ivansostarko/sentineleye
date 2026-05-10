# CLAUDE.md — SentinelEye Project Context for AI Assistants

This file gives Claude (and other AI coding assistants) the context they need
to contribute productively to SentinelEye. **Read this before generating
non-trivial changes.**

---

## What SentinelEye Is

A modular, open-source CCTV surveillance platform with real-time AI detection,
multi-camera recording, hybrid local + S3 storage, and Flutter clients on web,
Linux, and Android.

## Architecture in One Picture

```
┌──────────┐     ┌──────────────┐     ┌──────────────────┐
│ Cameras  │────▶│ recording-   │────▶│ Local FS / S3    │
│ (RTSP/   │     │ service      │     └──────────────────┘
│  ONVIF/  │     │ (FFmpeg)     │              ▲
│  USB...) │     └──────┬───────┘              │
└──────────┘            │ frames               │ playback URLs
                        ▼                      │
                 ┌──────────────┐       ┌──────┴───────┐
                 │ ai-engine    │──────▶│ backend      │──── REST/WS ──▶ Flutter
                 │ (YOLO+track) │ events│ (FastAPI)    │
                 └──────────────┘       └──────┬───────┘
                                               │
                                ┌──────────────┼──────────────┐
                                ▼              ▼              ▼
                          ┌──────────┐  ┌──────────┐  ┌────────────────┐
                          │ Postgres │  │ Redis    │  │ notification-  │
                          │ (meta)   │  │ (queue/  │  │ service        │
                          └──────────┘  │  pubsub) │  │ (email/tg/web) │
                                        └──────────┘  └────────────────┘
```

## Repository Layout (and where to put things)

| Path                              | Purpose                                              |
|-----------------------------------|------------------------------------------------------|
| `apps/backend/`                   | FastAPI app, REST + WS, auth, RBAC, DB models        |
| `apps/frontend/`                  | Flutter (web/linux/android) client                   |
| `services/ai-engine/`             | YOLO inference, tracking, motion, line-crossing      |
| `services/recording-service/`     | FFmpeg-driven continuous & event recording           |
| `services/notification-service/`  | Email / Telegram / Webhook dispatcher                |
| `packages/shared-schemas/`        | Cross-service Pydantic models + Dart equivalents     |
| `docker/`                         | Per-service Dockerfiles                              |
| `docs/`                           | Architecture / API / install / deployment docs       |

Each service has its own `CLAUDE.md` with service-specific guidance — read that too.

## Conventions

### Python (backend + services)

- **Python 3.12+** required. Always use type hints (PEP 604 unions: `str | None`).
- **Async-first**. Use `async def` for IO. Sync DB calls are forbidden in API handlers.
- **Pydantic v2** for schemas. Keep request/response models in `app/schemas/`.
- **SQLAlchemy 2.0** declarative + async session. Migrations via Alembic.
- **Repository pattern**: domain code talks to repositories (`app/db/repositories/`),
  not the ORM session directly.
- **Clean architecture layering**: `api → services → repositories → models`.
  Never let a model leak into an API response — convert to a schema.
- **Settings** come from `app/core/config.py` (pydantic-settings, reads `.env`).
  Never `os.getenv` inline in business code.
- **Logging** via `structlog` (configured in `app/core/logging.py`). No `print`.
- **Errors**: raise typed exceptions from `app/core/exceptions.py`; the global
  handler converts to RFC 7807 problem+json.
- **Tests**: `pytest`, `pytest-asyncio`. Place under `tests/` mirroring the
  source tree. Aim for unit tests on services + integration tests on endpoints.
- **Lint/format**: `ruff` (lint + format) + `mypy --strict` for new modules.

### Dart / Flutter (frontend)

- **Flutter 3.24+**, Dart 3.5+.
- **State**: Riverpod 2 (`flutter_riverpod`). One provider per use case; keep
  widgets dumb.
- **Routing**: `go_router` with auth-guarded routes.
- **Networking**: `dio` with interceptors for JWT refresh + retries.
- **Models**: `freezed` + `json_serializable`. Run `build_runner` after edits.
- **Folder pattern**: `lib/features/<feature>/{data,domain,presentation}`.
- **Theming**: Material 3, dark + light, tokens in `core/theme/`.

### Naming

- **Branches**: `feat/<scope>-<short-desc>`, `fix/...`, `chore/...`, `docs/...`.
- **Commits**: Conventional Commits (`feat(backend): …`, `fix(ai-engine): …`).
- **Python**: `snake_case` modules, `PascalCase` classes, `SCREAMING_SNAKE` consts.
- **Dart**: `lower_snake_case.dart` files, `PascalCase` types, `camelCase` members.
- **REST**: plural nouns, kebab-case (`/api/v1/cameras`, `/api/v1/detection-events`).
- **WebSocket channels**: `ws/v1/cameras/{id}/live`, `ws/v1/events/stream`.
- **DB tables**: plural snake_case (`cameras`, `detection_events`, `recordings`).

### Security Rules (do not violate)

1. **No secrets in git.** Use `.env` (gitignored). `SECRET_KEY` must be ≥ 32 chars.
2. **JWT** with short-lived access tokens + refresh tokens. Verify on every
   protected endpoint via the `get_current_user` dependency.
3. **RBAC**: roles `admin | operator | viewer`. Guard routes with
   `Depends(require_role("admin"))`.
4. **Input validation** is non-negotiable. Every external input goes through a
   Pydantic schema or a parameterized query.
5. **Signed URLs** for all S3 media access. Never expose raw bucket URLs.
6. **CORS** allowlist only — no `*` in production.
7. **Rate-limit** auth endpoints (`/auth/login`, `/auth/refresh`) with Redis.
8. **Never log credentials, tokens, or full frame payloads.**

### Performance

- Decode frames once in the recording-service; share via shared memory or a
  Redis stream — don't re-decode in the AI engine.
- Use `cv2.VideoCapture` with `CAP_FFMPEG` and explicit `OPENCV_FFMPEG_CAPTURE_OPTIONS`.
- Batch YOLO inference where latency permits (default batch=1 for live).
- Prefer ONNX/TensorRT exports for production GPU inference.

## How to Add a New Feature

1. Open / find the relevant `CLAUDE.md` in the service you're modifying.
2. Add or update the schema in `packages/shared-schemas/` if it's cross-service.
3. Backend: schema → repository → service → endpoint → test.
4. Frontend: model → repository → controller (Riverpod) → screen → widget test.
5. Update the matching doc in `docs/` (API.md for endpoints, ARCHITECTURE.md
   for new components).
6. Add or update Docker config if a new service or env var is introduced.

## How to Add a New AI Model

See `services/ai-engine/CLAUDE.md`. TL;DR: drop weights in
`services/ai-engine/models/`, register a `Detector` subclass in
`app/detectors/registry.py`, expose via `YOLO_MODEL` env var.

## What Not To Do

- ❌ Don't add a new top-level service without updating `docker-compose.yml`,
  this file, and `docs/ARCHITECTURE.md`.
- ❌ Don't bypass the repository layer with raw SQL outside `app/db/`.
- ❌ Don't put business logic in API handlers — they orchestrate, services decide.
- ❌ Don't ship code without tests for new public functions.
- ❌ Don't use `requirements.txt` for new deps — use `pyproject.toml`
  (we use `uv` / `pip-tools`).
- ❌ Don't introduce a new HTTP client, ORM, or state-management lib without
  raising it in an issue first.
