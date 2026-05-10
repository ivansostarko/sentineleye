# CLAUDE.md — Flutter Client

> Read the root [CLAUDE.md](../../CLAUDE.md) first.

## Stack

- Flutter 3.24+, Dart 3.5+
- State: **Riverpod 2** (`flutter_riverpod`)
- Routing: **go_router**
- Networking: **dio** (auth + refresh interceptors in `core/network/api_client.dart`)
- Models: hand-written for now; can graduate to **freezed** + `json_serializable`
- Secure storage: **flutter_secure_storage** for JWTs

## Folder Convention

```
lib/features/<feature>/
├── data/         # repositories (HTTP / WS)
├── domain/       # entities, value objects (no Flutter imports)
├── presentation/ # widgets / screens
└── providers/    # Riverpod controllers + provider declarations
```

`lib/shared/` is for genuinely cross-feature code only (avoid the temptation).

## Rules

- Widgets stay dumb; controllers own state and side effects.
- One Riverpod provider per use case. Don't build "god providers".
- Keep `BuildContext` out of `data/` and `domain/`.
- Never store JWTs in `SharedPreferences` — always `TokenStorage`.
- Use `MediaQuery.sizeOf(context)` for responsive logic, not deprecated `.of`.
- Use `const` constructors and final locals everywhere; the lints will yell.
- Don't add a new state-management library or HTTP client without an issue first.

## Adding a Feature

1. Create the four subfolders under `lib/features/<feature>/`.
2. Define the DTO in `domain/` (or `shared/models/` if it crosses features).
3. Build a `*Repository` in `data/` that uses the shared `apiClientProvider`.
4. Wire a controller in `providers/` (Riverpod `StateNotifier` or `AsyncNotifier`).
5. Build the screen in `presentation/`, register a route in `core/router.dart`,
   add a destination in `shared/widgets/app_shell.dart`.
6. Add a `*_test.dart` covering the controller and a widget golden if it makes sense.
