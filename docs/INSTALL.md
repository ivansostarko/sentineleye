# Installation

Three install paths, in order of "easiest first."

## 1. Docker Compose (recommended for dev & small deployments)

Prerequisites: Docker 24+, Docker Compose plugin, 4 GB RAM, 10 GB disk.

```bash
git clone ivansostarko/sentineleye.git
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
            email='admin@sentineleye.io',
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

- Web app: http://localhost:8080 (built Flutter bundle, served by nginx)
- API docs: http://localhost:8000/docs
- MinIO console: http://localhost:9001 (`minioadmin` / `minioadmin`)

The `frontend` service builds the Flutter web bundle and serves it via
nginx, which also reverse-proxies `/api/*` and `/ws/*` to the backend. That
makes everything same-origin — no CORS, and Web Crypto (used by
`flutter_secure_storage`) works on any host.

For active Flutter development with hot reload, skip the `frontend` container
and run the dev server directly instead:

```bash
cd apps/frontend
flutter pub get
flutter run -d web-server --web-port 8080 --web-hostname 0.0.0.0
```

Then open http://localhost:8080 (use `localhost`, not `0.0.0.0` — browsers
only treat `localhost` as a secure context). Use `-d chrome` if you want
Flutter to auto-launch a browser (non-root user only).

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

## 3. Native Flutter clients

The web bundle works in any browser, but you can also ship native binaries
straight from the same codebase.

### Web bundle (standalone, outside Docker)

The Docker `frontend` service already builds + serves a CanvasKit release
bundle behind nginx (covered in section 1). For one-off builds — or
deploying outside Docker (CDN, static host, GitHub Pages, etc.) — use
[scripts/build/build-web.sh](../scripts/build/build-web.sh).

```bash
# One-shot release bundle (also tarballed into dist/)
./scripts/build/build-web.sh

# Common flags:
./scripts/build/build-web.sh --debug
./scripts/build/build-web.sh --profile
./scripts/build/build-web.sh --renderer=html       # legacy DOM renderer (Flutter < 3.29 only — removed since)
./scripts/build/build-web.sh --wasm                # compile Dart → WASM (modern browsers only)
./scripts/build/build-web.sh --base-href=/app/     # serving under a subpath
./scripts/build/build-web.sh --pwa=none            # disable the offline service worker
./scripts/build/build-web.sh --csp                 # CSP-compatible JS (no eval)
./scripts/build/build-web.sh --no-source-maps
./scripts/build/build-web.sh --clean
./scripts/build/build-web.sh --no-archive
./scripts/build/build-web.sh --dart-define=API_BASE=https://api.acme.com
```

This script works on **any** host Flutter runs on (Linux, macOS, Windows,
WSL) — and unlike the desktop scripts, snap-installed Flutter is fine
here, since the broken-LLVM-linker problem only affects native targets.

Output paths:

| Asset | Location |
|---|---|
| Bundle dir | `apps/frontend/build/web/` |
| Entry point | `<bundle>/index.html` |
| Tarball | `dist/sentineleye-<version>-web-<renderer>-<mode>-<utc>.tar.gz` |

To smoke-test the bundle locally: `python3 -m http.server 8080` from inside
the bundle dir, then open http://localhost:8080. To deploy: drop the
bundle behind any static host (nginx, Caddy, S3+CloudFront, Cloudflare
Pages, GitHub Pages, Netlify…).

### Linux desktop

A wrapper script in [scripts/build/build-linux.sh](../scripts/build/build-linux.sh)
handles everything — system-package check, `flutter create --platforms=linux`
when needed, `flutter build linux --release`, and an optional tarball under
`dist/`.

```bash
# One-shot build (release + tarball in dist/)
./scripts/build/build-linux.sh

# Common flags:
./scripts/build/build-linux.sh --debug          # debug build
./scripts/build/build-linux.sh --profile        # profile build (DevTools-attachable)
./scripts/build/build-linux.sh --clean          # flutter clean first
./scripts/build/build-linux.sh --no-archive     # skip tarball
./scripts/build/build-linux.sh --skip-deps      # don't try to apt-install missing tools
./scripts/build/build-linux.sh --dart-define=API_BASE=https://api.acme.com
```

The first run as root will `apt-get install` the Linux toolchain
(`clang lld cmake ninja-build pkg-config libgtk-3-dev liblzma-dev libstdc++-12-dev`).
Without sudo you'll get instructions to install them manually, then you can
re-run.

**Heads-up: snap-installed Flutter is broken for Linux desktop builds.**
The snap bundles LLVM 10 inside its sandbox without the linker, so
`flutter build linux` fails with `Failed to find any of [ld.lld, ld] in
LocalDirectory: /snap/flutter/.../usr/lib/llvm-10/bin`. System-wide
`apt install lld` does not help — snap can't reach `/usr/bin/`.

The script **auto-detects this and falls back to a Docker build**
(`ghcr.io/cirruslabs/flutter:stable`) that has its own non-snap Flutter,
so you don't have to do anything — as long as Docker is installed, the
build just works. Force the behaviour with `--docker` / `--no-docker`.

If you'd rather fix your host install instead of relying on Docker:

```bash
sudo snap remove flutter
sudo git clone https://github.com/flutter/flutter.git -b stable /opt/flutter
echo 'export PATH="$PATH:/opt/flutter/bin"' >> ~/.bashrc
exec bash
flutter --version    # confirm it's the /opt/flutter one, not /snap/
```

Then re-run `./scripts/build/build-linux.sh` (it'll use the host Flutter).

Output paths:

| Asset | Location |
|---|---|
| Bundle dir | `apps/frontend/build/linux/<arch>/<mode>/bundle/` |
| Executable | `<bundle>/sentineleye` |
| Tarball | `dist/sentineleye-<version>-linux-<arch>-<mode>-<utc>.tar.gz` |

To run after building: `./apps/frontend/build/linux/x64/release/bundle/sentineleye`.

### Windows desktop

A wrapper script in [scripts/build/build-windows.sh](../scripts/build/build-windows.sh)
produces a Windows desktop bundle plus an optional `.zip` in `dist/`.

**Where it runs.** Flutter has no supported Linux→Windows cross-compile,
so the script only runs on a real Windows toolchain:

- ✓ **Windows host** — Git Bash / MSYS2 / Cygwin. Native build path.
- ✓ **WSL2 with Windows interop** — invokes `flutter.bat` so the build
  still runs on the Windows side. Clone the repo under `/mnt/c/...` for
  clean path translation.
- ✗ **Linux / macOS** — the script prints CI/Windows-host instructions
  and exits non-zero. There's no reliable Wine fallback to offer.

```bash
# One-shot release build (also dropped into dist/ as .zip)
./scripts/build/build-windows.sh

# Common flags:
./scripts/build/build-windows.sh --debug
./scripts/build/build-windows.sh --profile
./scripts/build/build-windows.sh --clean
./scripts/build/build-windows.sh --no-archive
./scripts/build/build-windows.sh --dart-define=API_BASE=https://api.acme.com
```

Prerequisites on the Windows side:

- Flutter for Windows (https://docs.flutter.dev/get-started/install/windows)
- Visual Studio 2022 with the **Desktop development with C++** workload
  (msvc, Windows 10/11 SDK, CMake). The script runs `flutter doctor` and
  bails with instructions if the workload is missing.

Output paths:

| Asset | Location |
|---|---|
| Bundle dir | `apps/frontend/build/windows/x64/runner/<Mode>/` |
| Executable | `<bundle>/sentineleye.exe` |
| Zip | `dist/sentineleye-<version>-windows-x64-<mode>-<utc>.zip` |

To run after building: `apps/frontend/build/windows/x64/runner/Release/sentineleye.exe`.
For automated release builds, run the script on a `windows-latest` GitHub
Actions runner (cheapest path — no Windows host required day-to-day).

### Android

A wrapper script in [scripts/build/build-android.sh](../scripts/build/build-android.sh)
mirrors the Linux one — same snap-Flutter / Docker fallback, same `dist/`
versioning. It can produce APKs (direct sideload) or AABs (Play Store).

```bash
# One-shot release APK (also dropped into dist/)
./scripts/build/build-android.sh

# Common flags:
./scripts/build/build-android.sh --aab                       # App Bundle for Play
./scripts/build/build-android.sh --debug                     # debug build
./scripts/build/build-android.sh --profile                   # profile build
./scripts/build/build-android.sh --split-per-abi             # one APK per ABI
./scripts/build/build-android.sh --target-platform=android-arm64
./scripts/build/build-android.sh --clean                     # flutter clean first
./scripts/build/build-android.sh --no-archive                # skip dist/ copy
./scripts/build/build-android.sh --docker                    # force Docker build
./scripts/build/build-android.sh --dart-define=API_BASE=https://api.acme.com
```

Like the Linux script, this auto-falls-back to
`ghcr.io/cirruslabs/flutter:stable` (which bundles Flutter + Android SDK +
JDK) when snap Flutter is detected, so you don't need a host JDK or
`ANDROID_HOME` set up. Force with `--docker` / `--no-docker`.

**Signing release builds for the Play Store.** Drop a `keystore.jks`
somewhere safe (NEVER in git) and create
`apps/frontend/android/key.properties`:

```properties
storeFile=/absolute/path/to/keystore.jks
storePassword=...
keyAlias=...
keyPassword=...
```

The script picks it up automatically; in Docker mode it bind-mounts the
keystore at the same absolute path so Gradle resolves it identically. With
no `key.properties`, `--release` builds are debug-signed and not eligible
for Play Store upload.

Output paths:

| Asset | Location |
|---|---|
| APK (single) | `apps/frontend/build/app/outputs/flutter-apk/app-<mode>.apk` |
| APK (per-ABI) | `apps/frontend/build/app/outputs/flutter-apk/app-<abi>-<mode>.apk` |
| AAB | `apps/frontend/build/app/outputs/bundle/<mode>/app-<mode>.aab` |
| Distributable | `dist/sentineleye-<version>-android-<mode>-<utc>.{apk,aab}` |

To install on a connected device: `adb install <path-to-apk>`.

### iOS

A wrapper script in [scripts/build/build-ios.sh](../scripts/build/build-ios.sh)
produces a signed `.ipa` (default) or unpackaged `.app`, plus an optional
copy in `dist/`.

**Where it runs.** Apple's toolchain is macOS-only, so the script bails
on anything else — there is no Docker image with Xcode and no honest
cross-compile to offer:

- ✓ **macOS** with Xcode + Command Line Tools + CocoaPods. The script
  installs CocoaPods via Homebrew or `gem install` if missing.
- ✗ **Linux / Windows** — exits with CI/macOS-host instructions.
  Use a `macos-latest` GitHub Actions runner, MacStadium, AWS EC2 Mac,
  Codemagic, or Bitrise for hosted builds.

```bash
# One-shot signed IPA for App Store distribution (default)
./scripts/build/build-ios.sh

# Common flags:
./scripts/build/build-ios.sh --export-method=ad-hoc      # for TestFlight-less internal distribution
./scripts/build/build-ios.sh --export-method=development # signed with a development cert
./scripts/build/build-ios.sh --app-bundle                # build .app, no IPA
./scripts/build/build-ios.sh --simulator                 # iOS Simulator .app (debug)
./scripts/build/build-ios.sh --no-codesign               # skip signing (dev/sim only)
./scripts/build/build-ios.sh --debug
./scripts/build/build-ios.sh --profile
./scripts/build/build-ios.sh --clean
./scripts/build/build-ios.sh --no-archive
./scripts/build/build-ios.sh --export-options-plist=path/to/ExportOptions.plist
./scripts/build/build-ios.sh --dart-define=API_BASE=https://api.acme.com
```

**Signing release IPAs.** You need an active Apple Developer Program
membership and Xcode signed in to it (Xcode → Settings → Accounts).
Easiest path: open the workspace once, pick your team, then re-run
the script:

```bash
open apps/frontend/ios/Runner.xcworkspace
# Runner → Signing & Capabilities → Team → <your team>
```

For fully-scripted CI signing, point `--export-options-plist` at a
plist with `signingStyle=manual`, `teamID`, and `provisioningProfiles`
(see Apple's `xcodebuild -h` for the schema).

Output paths:

| Asset | Location |
|---|---|
| IPA | `apps/frontend/build/ios/ipa/*.ipa` |
| App bundle (device) | `apps/frontend/build/ios/iphoneos/Runner.app` |
| App bundle (simulator) | `apps/frontend/build/ios/iphonesimulator/Runner.app` |
| Distributable | `dist/sentineleye-<version>-ios-<method>-<utc>.ipa` |

To install on a booted Simulator: `xcrun simctl install booted <Runner.app>`.
To upload to App Store Connect: use Transporter.app or `xcrun altool --upload-app`.

## 4. Production (Kubernetes)

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
