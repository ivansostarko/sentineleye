#!/usr/bin/env bash
# scripts/create-admin.sh — create an admin user via docker exec.
set -euo pipefail

EMAIL="${1:-admin@sentineleye.local}"
PASSWORD="${2:-ChangeMe!1234}"
NAME="${3:-Admin}"

docker compose exec -T backend python - <<PY
import asyncio
from app.db.session import _SessionLocal
from app.db.repositories import UserRepository
from app.services.auth_service import AuthService
from app.schemas.auth import UserCreate
from app.models.user import UserRole

async def main():
    async with _SessionLocal() as session:
        svc = AuthService(UserRepository(session))
        try:
            user = await svc.register(UserCreate(
                email="${EMAIL}",
                password="${PASSWORD}",
                full_name="${NAME}",
                role=UserRole.ADMIN,
            ))
            await session.commit()
            print("created", user.email)
        except Exception as e:
            print("FAILED:", e)
            raise SystemExit(1)

asyncio.run(main())
PY

echo
echo "✓ Admin user ready: ${EMAIL}"
echo "  Password: (the one you passed, or default ChangeMe!1234 — please change it)"
