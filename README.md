# SentinelEye

> Open-source AI-powered CCTV & smart video surveillance platform.

SentinelEye is a modular, production-grade surveillance platform that connects to virtually any camera (USB, IP/RTSP/RTMP, ONVIF, MJPEG), records continuously, and runs real-time AI object detection, localization, and tracking with YOLO. Alerts are pushed instantly to Flutter clients on Web, Linux desktop, and Android.

## Highlights

- 🎥 **Universal camera support** — RTSP, RTMP, ONVIF, USB UVC, HTTP/MJPEG
- 🧠 **AI built-in** — YOLOv8+ detection, ByteTrack/DeepSORT tracking, motion & line-crossing
- 💾 **Hybrid storage** — Local disk + S3 / MinIO with retention policies
- 🔔 **Multi-channel alerts** — Email, Telegram, Webhooks, Push, in-app realtime
- 📱 **Flutter clients** — Web, Linux, Android from one codebase
- 🐳 **Container-native** — Docker Compose for dev, scalable for prod
- 🔐 **Secure by default** — JWT auth, RBAC, signed URLs, HTTPS-ready
- 📊 **Observable** — Prometheus metrics, structured logs, health checks

## Repository Layout

```
sentineleye/
├── apps/
│   ├── backend/             # FastAPI API + WebSockets
│   └── frontend/            # Flutter (web / linux / android)
├── services/
│   ├── ai-engine/           # YOLO inference + tracking
│   ├── recording-service/   # Continuous & event-based recording
│   └── notification-service/# Email / Telegram / Webhook dispatcher
├── packages/
│   └── shared-schemas/      # Cross-service Pydantic / Dart schemas
├── docker/                  # Per-service Dockerfiles
├── docs/                    # Architecture, install, API, deployment
├── scripts/                 # Dev helpers, model download, migrations
└── docker-compose.yml       # One-command dev stack
```

## Quick Start

```bash
git clone <your-fork>/sentineleye.git
cd sentineleye
cp .env.example .env

# Bring up the full stack (Postgres, Redis, MinIO, backend, AI, recorder)
docker compose up -d

# Backend API → http://localhost:8000/docs
# MinIO console → http://localhost:9001  (minioadmin / minioadmin)
```

For Flutter:

```bash
cd apps/frontend
flutter pub get
flutter run -d web-server --web-port 8080 --web-hostname 0.0.0.0
# then open http://localhost:8080 — or use -d chrome / -d linux / -d android
```

## Documentation

| Doc                                        | What's inside                          |
|--------------------------------------------|----------------------------------------|
| [INSTALL.md](docs/INSTALL.md)              | Local & production install paths       |
| [ARCHITECTURE.md](docs/ARCHITECTURE.md)    | Service map, data flow, scaling        |
| [API.md](docs/API.md)                      | REST + WebSocket reference             |
| [DEVELOPMENT.md](docs/DEVELOPMENT.md)      | Dev loop, conventions, testing         |
| [DEPLOYMENT.md](docs/DEPLOYMENT.md)        | Compose / k8s / GPU notes              |
| [CAMERA_SUPPORT.md](docs/CAMERA_SUPPORT.md)| Protocols, discovery, troubleshooting  |
| [CLAUDE.md](CLAUDE.md)                     | AI assistant context for contributors  |

## License

Apache-2.0. See [LICENSE](LICENSE).
