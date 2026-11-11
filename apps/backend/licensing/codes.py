"""Serial numbers, PC codes and activation codes (ADR-0023). Pure Python with `cryptography` only -- no Django
-- so the vendor's licence tool (scripts/licensing/intraforge-license.py) uses exactly the same rules as
IntraForge.

* A **serial number** (SN) is what the vendor sells: ``IFG-XXXX-XXXX-XXXX-XXXX-XXXX`` (the master SN:
  ``IFM-...``). Sixteen random characters and four check characters, so a mistyped SN is caught at once. An SN
  alone unlocks nothing.
* A **PC code** names one computer: ``PC-1A2B-3C4D-5E6F-7A8B``, the first 8 bytes of SHA-256 over the Windows
  machine id and the motherboard's UUID (computed by the kit's start script, IntraForgeShop.Common.ps1
  Write-ShopMachineIdentity, with the same formula as ``pc_code`` below).
* An **activation code** binds one SN to one PC: ``IFA1.<payload>.<signature>``, the payload signed with the
  vendor's Ed25519 private key. IntraForge holds only the public key, so nobody but the vendor can make a
  working code, and a code made for one PC does not work on another.
"""

from __future__ import annotations

import base64
import datetime
import hashlib
import json
import re
import secrets

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no 0/O, 1/I: read aloud and typed without mistakes
STANDARD, MASTER = "standard", "master"
_PREFIX = {STANDARD: "IFG", MASTER: "IFM"}
_KIND = {v: k for k, v in _PREFIX.items()}
_ACTIVATION = "IFA1"


def _check(body: str) -> str:
    digest = hashlib.sha256(("IntraForge-SN:" + body).encode()).digest()
    return "".join(ALPHABET[b % 32] for b in digest[:4])


def new_serial(kind: str = STANDARD) -> str:
    body = "".join(secrets.choice(ALPHABET) for _ in range(16))
    whole = body + _check(body)
    return _PREFIX[kind] + "-" + "-".join(whole[i : i + 4] for i in range(0, 20, 4))


def normalize_serial(text) -> str | None:
    """The SN in its canonical form, or None if it is not a valid SN (wrong shape or a typo)."""
    clean = re.sub(r"[\s\-]", "", str(text or "")).upper()
    if len(clean) != 23 or clean[:3] not in _KIND or any(c not in ALPHABET for c in clean[3:]):
        return None
    body, check = clean[3:19], clean[19:]
    if _check(body) != check:
        return None
    whole = body + check
    return clean[:3] + "-" + "-".join(whole[i : i + 4] for i in range(0, 20, 4))


def serial_kind(serial: str) -> str:
    return _KIND[serial[:3]]


def pc_code(machine_guid: str, board_uuid: str) -> str:
    text = "IntraForge-PC:" + (machine_guid or "").lower() + "|" + (board_uuid or "").lower()
    h = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16].upper()
    return "PC-" + "-".join(h[i : i + 4] for i in range(0, 16, 4))


def normalize_pc(text) -> str | None:
    clean = re.sub(r"[\s\-]", "", str(text or "")).upper()
    if clean.startswith("PC"):
        clean = clean[2:]
    if not re.fullmatch(r"[0-9A-F]{16}", clean):
        return None
    return "PC-" + "-".join(clean[i : i + 4] for i in range(0, 16, 4))


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def sign_activation(
    private_key: Ed25519PrivateKey, *, serial: str, pc: str, issued: datetime.date | None = None
) -> str:
    serial, pc = normalize_serial(serial), normalize_pc(pc)
    if not serial or not pc:
        raise ValueError("A valid serial number and PC code are needed.")
    payload = json.dumps(
        {
            "v": 1,
            "sn": serial,
            "pc": pc,
            "kind": serial_kind(serial),
            "issued": (issued or datetime.date.today()).isoformat(),
        },
        separators=(",", ":"),
        sort_keys=True,
    ).encode()
    return f"{_ACTIVATION}.{_b64(payload)}.{_b64(private_key.sign(payload))}"


def verify_activation(public_key: Ed25519PublicKey, code) -> dict | None:
    """The activation's contents if the vendor signed it, else None."""
    text = re.sub(r"\s", "", str(code or ""))
    parts = text.split(".")
    if len(parts) != 3 or parts[0] != _ACTIVATION or len(text) > 1000:
        return None
    try:
        payload, signature = _unb64(parts[1]), _unb64(parts[2])
        public_key.verify(signature, payload)
        data = json.loads(payload)
    except (InvalidSignature, ValueError, TypeError):
        return None
    if not isinstance(data, dict) or data.get("v") != 1:
        return None
    if normalize_serial(data.get("sn")) != data.get("sn") or normalize_pc(data.get("pc")) != data.get("pc"):
        return None
    return data


def public_key_from_text(text: str) -> Ed25519PublicKey:
    return Ed25519PublicKey.from_public_bytes(base64.b64decode(text))


def public_key_text(private_key: Ed25519PrivateKey) -> str:
    from cryptography.hazmat.primitives import serialization

    raw = private_key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    return base64.b64encode(raw).decode()
