"""Unit tests for password hashing & JWT round-trip."""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.core.exceptions import UnauthorizedError
from app.core.security import (
    create_token,
    decode_token,
    hash_password,
    verify_password,
)


def test_password_round_trip() -> None:
    h = hash_password("correct horse battery staple")
    assert verify_password("correct horse battery staple", h)
    assert not verify_password("wrong", h)


def test_jwt_round_trip() -> None:
    sub = uuid4()
    token = create_token(sub, token_type="access", extra_claims={"role": "admin"})
    payload = decode_token(token, expected_type="access")
    assert payload["sub"] == str(sub)
    assert payload["role"] == "admin"


def test_jwt_wrong_type_rejected() -> None:
    token = create_token(uuid4(), token_type="refresh")
    with pytest.raises(UnauthorizedError):
        decode_token(token, expected_type="access")
