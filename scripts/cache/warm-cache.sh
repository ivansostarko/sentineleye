#!/usr/bin/env bash
# scripts/cache/warm-cache.sh — pre-populate the Redis cache.
#
# Wraps `python -m app.scripts.warm_cache` so you can warm from outside
# the container without remembering the docker compose incantation.
#
# Usage:
#   scripts/cache/warm-cache.sh                       # default: 3 pages, all targets
#   scripts/cache/warm-cache.sh --pages 5 --page-size 100
#   scripts/cache/warm-cache.sh --no-cameras
#   scripts/cache/warm-cache.sh --no-system-config
#   scripts/cache/warm-cache.sh --quiet               # cron-friendly
#   scripts/cache/warm-cache.sh --local               # skip docker compose, run in current venv
#
# Where it runs:
#   By default the script `docker compose exec backend ...` so it uses the
#   container's network/Redis/Postgres. Pass --local if you have an
#   activated venv with the backend installed and want to hit Redis/Postgres
#   directly from the host (the .env values must be reachable).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# ─── Helpers ───────────────────────────────────────────────────────────
log()  { printf "\033[1;34m▸\033[0m %s\n" "$*"; }
ok()   { printf "\033[1;32m✓\033[0m %s\n" "$*"; }
warn() { printf "\033[1;33m!\033[0m %s\n" "$*" >&2; }
die()  { printf "\033[1;31m✗\033[0m %s\n" "$*" >&2; exit 1; }

# ─── Parse mode flags (everything else passes through) ────────────────
MODE="docker"   # docker | local
PASSTHROUGH=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --local) MODE="local"; shift ;;
    --docker) MODE="docker"; shift ;;
    -h|--help)
      awk 'NR==1{next} /^$/{exit} {print}' "${BASH_SOURCE[0]}"
      exit 0
      ;;
    *) PASSTHROUGH+=("$1"); shift ;;
  esac
done

# ─── Run ──────────────────────────────────────────────────────────────
if [[ "$MODE" == "docker" ]]; then
  command -v docker >/dev/null 2>&1 || die "docker not on PATH (use --local to bypass)"
  cd "$REPO_ROOT"

  # Verify the backend service is up before exec'ing — friendlier error.
  if ! docker compose ps --status running --services 2>/dev/null | grep -qx backend; then
    die "backend container is not running. Start it with: docker compose up -d backend"
  fi

  log "Warming cache via 'docker compose exec backend'…"
  docker compose exec -T backend \
    python -m app.scripts.warm_cache "${PASSTHROUGH[@]+"${PASSTHROUGH[@]}"}"
else
  command -v python >/dev/null 2>&1 || die "python not on PATH"
  cd "$REPO_ROOT/apps/backend"

  if [[ -z "${VIRTUAL_ENV:-}" ]]; then
    warn "No venv detected — using system python. If imports fail, activate "\
"apps/backend/.venv first."
  fi

  log "Warming cache locally (python -m app.scripts.warm_cache)…"
  python -m app.scripts.warm_cache "${PASSTHROUGH[@]+"${PASSTHROUGH[@]}"}"
fi

ok "Cache warm complete."
