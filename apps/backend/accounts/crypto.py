"""
Encryption for MFA (TOTP) secrets at rest — same approach as
`databases/crypto.py` (Fernet, keyed by `CREDENTIAL_ENCRYPTION_KEY`), but
kept as its own small module rather than a shared import: `accounts` is
the most foundational app (every other app depends on it via
`settings.AUTH_USER_MODEL`), and having it import from a later, feature-
specific app like `databases` would invert this codebase's established
dependency direction for the sake of ~15 lines. See
docs/architecture/ROADMAP.md Phase 10.
"""

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings


class SecretDecryptionError(Exception):
    pass


def _fernet() -> Fernet:
    digest = hashlib.sha256(settings.CREDENTIAL_ENCRYPTION_KEY.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_secret(plaintext: str) -> bytes:
    return _fernet().encrypt(plaintext.encode())


def decrypt_secret(token: bytes) -> str:
    try:
        return _fernet().decrypt(token).decode()
    except InvalidToken as exc:
        raise SecretDecryptionError("secret could not be decrypted") from exc
