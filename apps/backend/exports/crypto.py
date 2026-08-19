"""
Encrypts an export/restore passphrase for the short hop through Celery
(Valkey broker + task-received/task-succeeded log lines, both of which
would otherwise carry it in plaintext — Celery logs task args at INFO
by default). Reuses CREDENTIAL_ENCRYPTION_KEY, the same key
`databases/crypto.py` uses for ConnectedDatabase credentials, since it's
already the designated "encrypt an operator-facing secret at rest/in
transit, distinct from SECRET_KEY" key for this deployment — this
module doesn't duplicate its own key-derivation scheme for the same
purpose.
"""

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings


class PassphraseTransitError(Exception):
    pass


def _fernet() -> Fernet:
    digest = hashlib.sha256(settings.CREDENTIAL_ENCRYPTION_KEY.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def wrap_passphrase(passphrase: str | None) -> str | None:
    if passphrase is None:
        return None
    return _fernet().encrypt(passphrase.encode()).decode()


def unwrap_passphrase(wrapped: str | None) -> str | None:
    if wrapped is None:
        return None
    try:
        return _fernet().decrypt(wrapped.encode()).decode()
    except InvalidToken as exc:
        raise PassphraseTransitError("could not unwrap passphrase for this job") from exc
