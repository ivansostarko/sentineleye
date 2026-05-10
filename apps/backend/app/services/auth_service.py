"""Authentication & user management."""

from __future__ import annotations

from app.core.exceptions import ConflictError, UnauthorizedError
from app.core.security import create_token, hash_password, verify_password
from app.db.repositories.user import UserRepository
from app.models.user import User
from app.schemas.auth import TokenPair, UserCreate, UserProfileUpdate


class AuthService:
    def __init__(self, users: UserRepository) -> None:
        self.users = users

    async def register(self, payload: UserCreate) -> User:
        if await self.users.get_by_email(payload.email):
            raise ConflictError("A user with that email already exists.")

        user = User(
            email=payload.email.lower(),
            full_name=payload.full_name,
            hashed_password=hash_password(payload.password),
            role=payload.role,
        )
        return await self.users.add(user)

    async def authenticate(self, email: str, password: str) -> User:
        user = await self.users.get_by_email(email)
        if user is None or not verify_password(password, user.hashed_password):
            raise UnauthorizedError("Invalid email or password.")
        if not user.is_active:
            raise UnauthorizedError("Account disabled.")
        return user

    def issue_tokens(self, user: User) -> TokenPair:
        return TokenPair(
            access_token=create_token(user.id, token_type="access", extra_claims={"role": user.role.value}),
            refresh_token=create_token(user.id, token_type="refresh"),
        )

    async def update_profile(self, user: User, payload: UserProfileUpdate) -> User:
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(user, field, value)
        await self.users.session.flush()
        return user

    async def change_password(self, user: User, current: str, new: str) -> None:
        if not verify_password(current, user.hashed_password):
            raise UnauthorizedError("Current password is incorrect.")
        if current == new:
            raise UnauthorizedError("New password must differ from the current one.")
        user.hashed_password = hash_password(new)
        await self.users.session.flush()
