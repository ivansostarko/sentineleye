# Installation

Three install paths, in order of "easiest first."

## 1. Docker Compose (recommended for dev & small deployments)

Prerequisites: Docker 24+, Docker Compose plugin, 4 GB RAM, 10 GB disk.

```bash
git clone <your-fork>/sentineleye.git
cd sentineleye
cp .env.example .env
# Edit .env — at minimum set SECRET_KEY to a long random string.

docker compose up -d --build
docker compose exec backend alembic upgrade head
docker compose exec backend python -c "
from app.services.auth_service import AuthService
from app.db.repositories import UserRepository
from app.schemas.auth import UserCreate
from app.models.user import UserRole
from app.db.session import _SessionLocal
import asyncio

async def main():
    async with _SessionLocal() as s:
        svc = AuthService(UserRepository(s))
        user = await svc.register(UserCreate(
            email='admin@sentineleye.local',
            password='ChangeMe!1234',
            full_name='Admin',
            role=UserRole.ADMIN,
        ))
        await s.commit()
        print('created', user.email)

asyncio.run(main())
"
```

Now visit:

- API docs: http://localhost:8000/docs
- MinIO console: http://localhost:9001 (`minioadmin` / `minioadmin`)

Then run the Flutter client:

```bash
cd apps/frontend
flutter pub get
flutter run -d chrome
```

## 2. Local dev (no Docker)

Prerequisites: Python 3.12+, Node only if you build docs, Postgres 16, Redis 7,
optional MinIO, FFmpeg.

### Backend

```bash
cd apps/backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
export $(grep -v '^#' ../../.env | xargs)
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

### AI engine

```bash
cd services/ai-engine
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8100
```

### Recording service

```bash
cd services/recording-service
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8200
```

### Notification service

```bash
cd services/notification-service
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8300
```

## 3. Production (Kubernetes)

Treat the compose file as the contract: each service is independently scalable.
A first-cut Helm chart is on the roadmap. See [DEPLOYMENT.md](DEPLOYMENT.md) for
constraints (GPU scheduling, persistent volumes, network policies).

## Troubleshooting

| Symptom                                     | Likely cause / fix                                                |
|---------------------------------------------|-------------------------------------------------------------------|
| `connection refused: postgres`              | Postgres not healthy yet → `docker compose logs postgres`         |
| `Invalid SECRET_KEY` on startup             | `.env` missing `SECRET_KEY` ≥ 32 chars                            |
| AI engine OOM on first inference            | Model too big for available RAM → switch to `yolov8n.pt`          |
| `Permission denied` on `/data/recordings`   | Bind-mount permissions → `chown -R 1000:1000 ./.docker-data/...`  |
| Camera "unknown" status                     | Health check task hasn't run yet (1 min) or RTSP creds wrong      |
