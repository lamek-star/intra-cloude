"""
Encryption for EnvironmentSecret values and EnvironmentWebhook signing
secrets at rest -- same approach as `accounts/crypto.py`/`databases/
crypto.py` (Fernet, keyed by `CREDENTIAL_ENCRYPTION_KEY`), kept as its
own small module rather than a shared import, matching this codebase's
established per-app convention (see accounts/crypto.py's own docstring
for why: a handful of duplicated lines beats a cross-app dependency for
something this small).
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
        return _fernet().decrypt(bytes(token)).decode()
    except InvalidToken as exc:
        raise SecretDecryptionError("secret could not be decrypted") from exc
