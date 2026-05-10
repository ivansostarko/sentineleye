#!/usr/bin/env bash
# scripts/bootstrap.sh — one-shot dev environment setup.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ ! -f .env ]]; then
  echo "→ Creating .env from .env.example"
  cp .env.example .env
  # Generate a SECRET_KEY if openssl is available
  if command -v openssl >/dev/null 2>&1; then
    KEY="$(openssl rand -hex 32)"
    if sed --version >/dev/null 2>&1; then
      sed -i "s|^SECRET_KEY=.*|SECRET_KEY=${KEY}|" .env
    else
      sed -i '' "s|^SECRET_KEY=.*|SECRET_KEY=${KEY}|" .env
    fi
    echo "→ Generated random SECRET_KEY"
  fi
fi

echo "→ Building & starting stack…"
docker compose up -d --build

echo "→ Waiting for backend to be healthy…"
for _ in $(seq 1 30); do
  if curl -fsS http://localhost:8000/healthz >/dev/null; then
    echo "✓ Backend up."
    break
  fi
  sleep 2
done

echo "→ Applying migrations…"
docker compose exec -T backend alembic upgrade head

echo
echo "✓ SentinelEye is up."
echo "  • API     → http://localhost:8000/docs"
echo "  • MinIO   → http://localhost:9001  (minioadmin / minioadmin)"
echo
echo "Next: create an admin user and run the Flutter client."
echo "  See docs/INSTALL.md."
