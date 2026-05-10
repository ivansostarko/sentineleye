# Shared Schemas

Cross-service schemas (Pydantic on the Python side, Dart on the client side) that
need to stay aligned when the wire format changes.

## Why this lives here

Three Python services (backend, ai-engine, recording-service) and one Flutter
client all serialize the same shapes — `DetectionEvent`, `Camera`, `Recording`,
etc. Keeping a single source of truth in this package avoids drift.

## Layout

```
packages/shared-schemas/
├── python/                   # importable as `sentineleye_schemas`
│   └── sentineleye_schemas/
│       ├── __init__.py
│       └── events.py
└── dart/                     # add when ready (mirror Python with freezed models)
```

## Workflow when changing a schema

1. Edit the Python model.
2. Edit the Dart equivalent in `apps/frontend/lib/shared/models/`.
3. Bump versions in both `pyproject.toml` and `pubspec.yaml`.
4. Update `docs/API.md` and Alembic if the DB representation changes.
