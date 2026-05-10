"""Authentication endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.v1.deps import auth_service, get_current_user
from app.core.security import decode_token
from app.models.user import User
from app.schemas.auth import LoginRequest, RefreshRequest, TokenPair, UserCreate, UserPublic
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
async def register(
    payload: UserCreate,
    service: Annotated[AuthService, Depends(auth_service)],
) -> UserPublic:
    user = await service.register(payload)
    return UserPublic(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
    )


@router.post("/login", response_model=TokenPair)
async def login(
    payload: LoginRequest,
    service: Annotated[AuthService, Depends(auth_service)],
) -> TokenPair:
    user = await service.authenticate(payload.email, payload.password)
    return service.issue_tokens(user)


@router.post("/refresh", response_model=TokenPair)
async def refresh(
    payload: RefreshRequest,
    service: Annotated[AuthService, Depends(auth_service)],
) -> TokenPair:
    claims = decode_token(payload.refresh_token, expected_type="refresh")
    user = await service.users.get(claims["sub"])  # type: ignore[arg-type]
    if user is None:
        from app.core.exceptions import UnauthorizedError

        raise UnauthorizedError("Unknown user.")
    return service.issue_tokens(user)


@router.get("/me", response_model=UserPublic)
async def me(user: Annotated[User, Depends(get_current_user)]) -> UserPublic:
    return UserPublic(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
    )
