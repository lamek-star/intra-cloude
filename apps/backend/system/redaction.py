"""Secret redaction for support diagnostics (Local Edition pilot support).

A diagnostics bundle is what a shop sends to whoever supports it, so it must be safe to hand over: it may
show that a password was configured, never the password. `redact()` is applied to every log line and
status text placed in a bundle (scripts/support/collect-diagnostics.sh pipes everything through
`python -m system.redaction`). It is deliberately conservative -- it prefers redacting a harmless value to
leaking a secret -- and it never needs the secret's name to be known in advance: it recognizes the shapes
secrets take (a value after a secret-looking key, a bearer token, a URL with credentials, a JWT, a Fernet
key, a session or CSRF cookie).
"""

import re
import sys

REDACTED = "[REDACTED]"

# key = value / key: value / "key": "value" -- for any key whose name says it is a secret. The name may be
# prefixed (DJANGO_SECRET_KEY, MINIO_ROOT_PASSWORD, X-Api-Key) and the value may be quoted.
_SECRET_WORDS = (
    r"(?:password|passwd|pwd|passphrase|secret|token|api[_-]?key|apikey|private[_-]?key|credential"
    r"|auth(?:orization)?|signing|encryption[_-]?key|access[_-]?key|session(?:id)?|csrf(?:token)?)"
)
_KEY_VALUE = re.compile(
    rf"""(?ix)
    (?P<key>["']?[A-Za-z0-9_.\-]*{_SECRET_WORDS}[A-Za-z0-9_.\-]*["']?)   # a key that names a secret
    (?P<sep>\s*[:=]\s*)
    (?P<open>["']?)
    (?P<value>[^\s"',;&}}\]]+)
    """
)
_BEARER = re.compile(r"(?i)\b(bearer|basic)\s+[A-Za-z0-9._~+/=\-]{8,}")
_URL_CREDENTIALS = re.compile(
    r"(?P<scheme>[a-z][a-z0-9+.\-]*://)(?P<user>[^\s:/@]+):(?P<password>[^\s@/]+)@", re.I
)
_JWT = re.compile(r"\beyJ[A-Za-z0-9_\-]{5,}\.[A-Za-z0-9_\-]{5,}\.[A-Za-z0-9_\-]{5,}\b")
# A Fernet key is 32 url-safe base64 bytes: 43 characters plus one '='.
_FERNET = re.compile(r"(?<![A-Za-z0-9_\-])[A-Za-z0-9_\-]{43}=(?![A-Za-z0-9_\-=])")
_COOKIE = re.compile(r"(?i)\b(sessionid|csrftoken|csrf_token)=[^;\s]+")
_PRIVATE_KEY_BLOCK = re.compile(
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.S
)


def _key_value(match: re.Match) -> str:
    return f"{match['key']}{match['sep']}{match['open']}{REDACTED}"


def redact(text: str) -> str:
    text = _PRIVATE_KEY_BLOCK.sub(REDACTED, text)
    text = _URL_CREDENTIALS.sub(lambda m: f"{m['scheme']}{m['user']}:{REDACTED}@", text)
    text = _BEARER.sub(lambda m: f"{m[1]} {REDACTED}", text)
    text = _COOKIE.sub(lambda m: f"{m[1]}={REDACTED}", text)
    text = _JWT.sub(REDACTED, text)
    text = _KEY_VALUE.sub(_key_value, text)
    text = _FERNET.sub(REDACTED, text)
    return text


def main() -> None:
    # Whole input, not line by line: a private-key block spans several lines.
    sys.stdout.write(redact(sys.stdin.read()))


if __name__ == "__main__":
    main()
