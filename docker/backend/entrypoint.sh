#!/usr/bin/env bash
# Container entrypoint: bring the schema up to date, then start uvicorn.
#
# Why migrations live here:
#   Bugs like "pin/reorder/disable returns 500" trace back to a column
#   added by an alembic revision that nobody remembered to apply against
#   the running database. Running `alembic upgrade head` on every container
#   start is idempotent (no-op when already current) and removes a class
#   of regressions for good.
#
# Override behaviour:
#   SKIP_MIGRATIONS=1  → don't run alembic (useful when seeding from a backup)

set -euo pipefail

if [[ "${SKIP_MIGRATIONS:-}" == "1" ]]; then
  echo "[entrypoint] SKIP_MIGRATIONS=1 — leaving schema as-is."
else
  echo "[entrypoint] Running alembic upgrade head…"
  # Tolerate transient DB unavailability for a few seconds — postgres
  # depends_on/healthcheck normally covers this, but `alembic` can race
  # the very first connection on a cold start.
  attempts=0
  until alembic upgrade head; do
    attempts=$((attempts + 1))
    if (( attempts >= 5 )); then
      echo "[entrypoint] alembic failed after ${attempts} attempts — aborting."
      exit 1
    fi
    echo "[entrypoint] alembic failed (attempt ${attempts}/5) — retrying in 2s…"
    sleep 2
  done
  echo "[entrypoint] Schema is up to date."
fi

# Hand off to whatever CMD/argv was passed (uvicorn, by default).
exec "$@"
