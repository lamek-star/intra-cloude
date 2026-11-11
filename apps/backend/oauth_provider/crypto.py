"""
Encryption for the OIDC signing key's private half — same approach as
accounts/crypto.py (Fernet, keyed by CREDENTIAL_ENCRYPTION_KEY), kept as
its own small module for the same reason accounts/crypto.py gives:
avoiding a cross-app import for ~10 lines. Hashing helpers here mirror
ApplicationCredential's convention (SHA-256 hex of a high-entropy,
server-generated secret — not a slow password hasher; see models.py).
"""

import base64
import hashlib
import secrets

from cryptography.fernet import Fernet
from django.conf import settings


def _fernet() -> Fernet:
    digest = hashlib.sha256(settings.CREDENTIAL_ENCRYPTION_KEY.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_secret(plaintext: bytes) -> bytes:
    return _fernet().encrypt(plaintext)


def decrypt_secret(token: bytes) -> bytes:
    return _fernet().decrypt(token)


def generate_token(nbytes: int = 32) -> str:
    """A URL-safe, high-entropy random string — used for client_id
    (public), client_secret/authorization codes/access tokens (secret,
    only ever returned once and stored here as a hash)."""
    return secrets.token_urlsafe(nbytes)


def hash_token(plaintext: str) -> str:
    return hashlib.sha256(plaintext.encode()).hexdigest()
