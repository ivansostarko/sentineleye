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

To produce a **shippable Linux desktop binary** (handles toolchain + tarball):

```bash
./scripts/build/build-linux.sh
# → apps/frontend/build/linux/x64/release/bundle/sentineleye
# → dist/sentineleye-<ver>-linux-x64-release-<utc>.tar.gz
```

To produce a **shippable Android APK or AAB** (snap-Flutter-safe, signs with
`apps/frontend/android/key.properties` if present):

```bash
./scripts/build/build-android.sh         # release APK
./scripts/build/build-android.sh --aab   # App Bundle for Play Store
# → apps/frontend/build/app/outputs/{flutter-apk,bundle/release}/...
# → dist/sentineleye-<ver>-android-release-<utc>.{apk,aab}
```

To produce a **shippable Windows desktop bundle** (must run on Windows /
WSL — Flutter has no Linux→Windows cross-compile):

```bash
./scripts/build/build-windows.sh         # release .exe + .zip
# → apps/frontend/build/windows/x64/runner/Release/sentineleye.exe
# → dist/sentineleye-<ver>-windows-x64-release-<utc>.zip
```

To produce a **signed iOS .ipa** for the App Store (must run on macOS
with Xcode — Apple's toolchain is macOS-only):

```bash
./scripts/build/build-ios.sh             # signed app-store IPA
./scripts/build/build-ios.sh --simulator # iOS Simulator .app for dev
# → apps/frontend/build/ios/ipa/*.ipa
# → dist/sentineleye-<ver>-ios-app-store-<utc>.ipa
```

To produce a **standalone web bundle** for any static host (CDN, S3,
GitHub Pages — outside the bundled `frontend` Docker container):

```bash
./scripts/build/build-web.sh             # release CanvasKit bundle
./scripts/build/build-web.sh --wasm      # WASM build for modern browsers
# → apps/frontend/build/web/
# → dist/sentineleye-<ver>-web-canvaskit-release-<utc>.tar.gz
```

See [INSTALL.md → Native Flutter clients](docs/INSTALL.md#3-native-flutter-clients)
for all build flags.

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
