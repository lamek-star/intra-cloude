"""
RFC 6238 TOTP (the algorithm behind Google Authenticator / Authy /
1Password's TOTP support), implemented directly against the standard
library rather than adding a third-party dependency for something this
small and security-critical to get right ourselves: SHA-1/HMAC, base32,
and struct packing are all `hashlib`/`hmac`/`base64`/`struct` — nothing
here needs an external package (Section 24 of the master prompt: avoid
adding dependencies before they're needed).
"""

import base64
import hashlib
import hmac
import secrets
import struct
import time
import urllib.parse

_DIGITS = 6
_PERIOD_SECONDS = 30
# Accept a code from one period before/after the current one, to absorb
# ordinary clock drift between the server and the user's authenticator
# app — the same tolerance window virtually every TOTP implementation
# uses.
_VERIFY_WINDOW = 1


def generate_secret() -> str:
    """A fresh, random base32-encoded secret — 20 bytes (160 bits) of
    entropy, the RFC 4226 recommended HOTP/TOTP key length."""
    return base64.b32encode(secrets.token_bytes(20)).decode("ascii").rstrip("=")


def _hotp(secret_b32: str, counter: int) -> str:
    padding = "=" * ((8 - len(secret_b32) % 8) % 8)
    key = base64.b32decode(secret_b32 + padding)
    msg = struct.pack(">Q", counter)
    digest = hmac.new(key, msg, hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    code_int = (struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF) % (10**_DIGITS)
    return str(code_int).zfill(_DIGITS)


def generate_totp(secret_b32: str, *, for_time: float | None = None) -> str:
    counter = int((for_time if for_time is not None else time.time()) // _PERIOD_SECONDS)
    return _hotp(secret_b32, counter)


def verify_totp(secret_b32: str, code: str, *, for_time: float | None = None) -> bool:
    """Constant-time comparison against each candidate in the tolerance
    window — never a plain `==`, which would leak timing information
    about how many leading digits matched."""
    if not code or not code.isdigit() or len(code) != _DIGITS:
        return False
    now = for_time if for_time is not None else time.time()
    counter = int(now // _PERIOD_SECONDS)
    return any(
        hmac.compare_digest(_hotp(secret_b32, counter + offset), code)
        for offset in range(-_VERIFY_WINDOW, _VERIFY_WINDOW + 1)
    )


def provisioning_uri(secret_b32: str, *, account_name: str, issuer: str = "Private Data Cloud") -> str:
    """`otpauth://` URI an authenticator app can scan as a QR code (the
    caller renders the QR code; this module only produces the URI)."""
    label = urllib.parse.quote(f"{issuer}:{account_name}")
    query = {
        "secret": secret_b32,
        "issuer": issuer,
        "algorithm": "SHA1",
        "digits": _DIGITS,
        "period": _PERIOD_SECONDS,
    }
    return f"otpauth://totp/{label}?{urllib.parse.urlencode(query)}"
