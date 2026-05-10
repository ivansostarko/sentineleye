# Architecture

## Component Map

```
                                    ┌──────────────────┐
                                    │  Flutter client  │
                                    │ (web/linux/and.) │
                                    └────────┬─────────┘
                                             │ HTTPS  REST + WSS
                                             ▼
┌─────────────┐     internal HTTP    ┌──────────────────┐    SQL    ┌──────────┐
│ Cameras     │◀────RTSP/RTMP────┐   │   Backend API    │──────────▶│ Postgres │
│ (RTSP/USB/  │                  │   │  (FastAPI + WS)  │           └──────────┘
│  ONVIF/...) │                  │   │                  │   pubsub  ┌──────────┐
└─────────────┘                  │   │                  │──────────▶│  Redis   │
        │                        │   └────────┬─────────┘           └────┬─────┘
        │                        │            │                          │
        ▼                        │            ▼                          │
┌──────────────────┐             │   ┌──────────────────┐                │
│ recording-svc    │─────POST────┴──▶│ events.detections│◀───subscribe───┘
│ (ffmpeg per cam) │ recordings  │   │ events.alerts    │
└────┬─────────────┘             │   │ events.cam_state │
     │ writes mp4 segments       │   └──────────────────┘
     ▼                           │            │
┌──────────────────┐             │            ▼
│ Local FS / S3    │◀─────signed─┘   ┌──────────────────┐
│ (recordings)     │   URLs          │ notification-svc │
└──────────────────┘                 │ (smtp/tg/webhook)│
                                     └──────────────────┘
                                              ▲
┌──────────────────┐                          │
│ ai-engine        │──POST detection events──┘
│ (YOLO + tracker) │
└──────────────────┘
```

## Service Responsibilities

| Service               | Owns                                       | Talks to                        |
|-----------------------|--------------------------------------------|---------------------------------|
| backend               | API, auth, DB schema, WS fan-out           | Postgres, Redis, S3, all svcs   |
| ai-engine             | Detection, tracking, snapshots             | Backend (POST events)           |
| recording-service     | FFmpeg segmenter, segment metadata         | Backend (POST recordings)       |
| notification-service  | Outbound email/Telegram/webhook            | Backend (HTTP)                  |
| backend-worker        | Retention, archival, camera health checks  | Postgres, Redis, S3             |

## Data Flow — Live Detection

```
camera ──► recording-svc ──► segment.mp4 (local)
   │
   └──► ai-engine ──► YOLO ──► tracker ──► POST /detection-events
                                                 │
                                                 ▼
                                        backend ──► insert into DB
                                                 │
                                                 ├──► publish events.detections (Redis)
                                                 │            │
                                                 │            └──► WS clients receive event
                                                 │
                                                 └──► alert evaluator ──► matching rules?
                                                                              │
                                                                              ▼
                                                              POST notification-service
```

## Storage Modes

- **local**: write to `LOCAL_STORAGE_PATH`, serve via authenticated `/media/<key>`.
- **s3**: write directly to S3/MinIO; serve via short-lived presigned GET URLs.
- **hybrid**: write local first (fast), Celery `archive_to_s3` task moves segments
  older than `ARCHIVE_AFTER_DAYS` to S3 and updates the recording row.

## Auth & RBAC

- JWT (HS256) with separate access (60 min) and refresh (14 day) tokens.
- Roles: `admin`, `operator`, `viewer`.
  - `viewer` — read-only across cameras, events, recordings.
  - `operator` — viewer + create/update cameras and alert rules.
  - `admin` — operator + delete cameras, manage users.
- Service-to-service traffic uses a shared `BACKEND_SERVICE_TOKEN` (rotate regularly).

## Scaling Notes

- backend: stateless, scale horizontally behind a sticky-WS load balancer.
- ai-engine: one replica per N cameras (depends on FPS / model). GPU instance
  per replica is the right primitive for production.
- recording-service: horizontally scalable; partition cameras across replicas
  (e.g., consistent-hash on `camera_id`) so each segment has exactly one writer.
- Postgres: vertical first; read replicas for events/recordings queries.
- Redis: pub/sub fan-out is the bottleneck for very large WS client counts —
  swap for NATS or Kafka if you outgrow it.
