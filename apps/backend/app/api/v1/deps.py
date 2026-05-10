"""Reusable FastAPI dependencies (DI)."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.security import decode_token
from app.db.repositories import (
    AlertEventRepository,
    AlertRuleRepository,
    CameraRepository,
    CloudIntegrationRepository,
    DetectionEventRepository,
    RecordingRepository,
    SystemConfigRepository,
    UserRepository,
)
from app.db.session import get_session
from app.models.user import User, UserRole
from app.services.alert_service import AlertService
from app.services.auth_service import AuthService
from app.services.camera_service import CameraService
from app.services.cloud_integration_service import CloudIntegrationService
from app.services.system_config_service import SystemConfigService

DbSession = Annotated[AsyncSession, Depends(get_session)]


# ─── Repositories ──────────────────────────────────────────────────────
def user_repo(session: DbSession) -> UserRepository:
    return UserRepository(session)


def camera_repo(session: DbSession) -> CameraRepository:
    return CameraRepository(session)


def detection_repo(session: DbSession) -> DetectionEventRepository:
    return DetectionEventRepository(session)


def recording_repo(session: DbSession) -> RecordingRepository:
    return RecordingRepository(session)


def alert_repo(session: DbSession) -> AlertRuleRepository:
    return AlertRuleRepository(session)


def alert_event_repo(session: DbSession) -> AlertEventRepository:
    return AlertEventRepository(session)


def cloud_integration_repo(session: DbSession) -> CloudIntegrationRepository:
    return CloudIntegrationRepository(session)


def system_config_repo(session: DbSession) -> SystemConfigRepository:
    return SystemConfigRepository(session)


# ─── Services ──────────────────────────────────────────────────────────
def auth_service(users: Annotated[UserRepository, Depends(user_repo)]) -> AuthService:
    return AuthService(users)


def camera_service(
    cameras: Annotated[CameraRepository, Depends(camera_repo)],
    integrations: Annotated[CloudIntegrationRepository, Depends(cloud_integration_repo)],
) -> CameraService:
    return CameraService(cameras, integrations)


def cloud_integration_service(
    integrations: Annotated[CloudIntegrationRepository, Depends(cloud_integration_repo)],
) -> CloudIntegrationService:
    return CloudIntegrationService(integrations)


def system_config_service(
    repo: Annotated[SystemConfigRepository, Depends(system_config_repo)],
) -> SystemConfigService:
    return SystemConfigService(repo)


def alert_service(
    rules: Annotated[AlertRuleRepository, Depends(alert_repo)],
    events: Annotated[AlertEventRepository, Depends(alert_event_repo)],
) -> AlertService:
    return AlertService(rules, events)


# ─── Auth dependencies ────────────────────────────────────────────────
async def get_current_user(
    users: Annotated[UserRepository, Depends(user_repo)],
    authorization: Annotated[str | None, Header()] = None,
) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise UnauthorizedError("Missing bearer token.")
    token = authorization.split(" ", 1)[1]
    payload = decode_token(token, expected_type="access")
    user = await users.get(UUID(payload["sub"]))
    if user is None or not user.is_active:
        raise UnauthorizedError("User not found or inactive.")
    return user


def require_role(*allowed: UserRole):
    async def _checker(user: Annotated[User, Depends(get_current_user)]) -> User:
        if user.role not in allowed:
            raise ForbiddenError(
                f"Requires one of: {', '.join(r.value for r in allowed)}"
            )
        return user

    return _checker
