"""
Encryption for ConnectedDatabase credentials at rest (Section 15 of the
master prompt; ADR-0009). Uses CREDENTIAL_ENCRYPTION_KEY, a key dedicated
to this purpose and distinct from Django's SECRET_KEY, so rotating one
never silently affects the other.
"""

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings


class CredentialDecryptionError(Exception):
    pass


def _fernet() -> Fernet:
    # CREDENTIAL_ENCRYPTION_KEY is an arbitrary-length operator-supplied
    # secret (.env.example just says "generate a long random value"), not
    # necessarily already a valid Fernet key (32 url-safe base64 bytes) —
    # derive one deterministically via SHA-256 rather than requiring
    # operators to generate keys in a specific format.
    digest = hashlib.sha256(settings.CREDENTIAL_ENCRYPTION_KEY.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_credential(plaintext: str) -> bytes:
    return _fernet().encrypt(plaintext.encode())


def decrypt_credential(token: bytes) -> str:
    try:
        return _fernet().decrypt(token).decode()
    except InvalidToken as exc:
        raise CredentialDecryptionError("credential could not be decrypted") from exc
