# SentinelEye Flutter Client

Multi-platform client (Web, Linux desktop, Android) for the SentinelEye backend.

## Quickstart

```bash
flutter pub get
flutter run -d web-server --web-port 8080 --web-hostname 0.0.0.0
# then open http://localhost:8080
```

Other targets: `-d chrome` (auto-launches Chrome — requires non-root user),
`-d linux`, or `-d android`.

## Configuration

Edit `assets/config.json` (or build with a different `--dart-define=CONFIG_ASSET=...`):

```json
{
  "apiBaseUrl": "http://localhost:8000",
  "wsBaseUrl": "ws://localhost:8000"
}
```

## Layout

```
lib/
├── core/            # config, networking, theming, routing, secure storage
├── features/        # one folder per feature (data/domain/presentation/providers)
└── shared/          # cross-feature widgets and DTO models
```

See `CLAUDE.md` (this folder) for conventions.
