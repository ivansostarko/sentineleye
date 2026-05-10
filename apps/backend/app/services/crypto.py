"""Fernet symmetric encryption for secrets stored at rest.

The Fernet key is derived from `SECRET_KEY` so we don't need a separate
secrets manager for self-hosted deployments. This protects against casual
DB dumps but is not a substitute for a KMS in regulated environments —
swap `_key()` for a KMS lookup when you need stronger separation.
"""

from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import get_settings
from app.core.exceptions import AppError


class CryptoError(AppError):
    code = "crypto_error"


def _fernet() -> Fernet:
    secret = get_settings().secret_key.encode()
    # Fernet wants 32 raw bytes, base64url-encoded. SHA-256 gives us 32 bytes.
    return Fernet(base64.urlsafe_b64encode(hashlib.sha256(secret).digest()))


def encrypt(plain: str) -> str:
    """Encrypt a string. Output is URL-safe base64 (safe for VARCHAR/Text)."""
    return _fernet().encrypt(plain.encode()).decode()


def decrypt(token: str) -> str:
    """Decrypt a previously-encrypted string. Raises CryptoError on failure."""
    try:
        return _fernet().decrypt(token.encode()).decode()
    except InvalidToken as exc:
        raise CryptoError("Failed to decrypt value (wrong SECRET_KEY?).") from exc
