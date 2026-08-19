"""
The .icp file's outer container format (Section 19 of the master
prompt). Structure, all big-endian:

    8 bytes   magic       b"ICPKG001"
    4 bytes   header_len  uint32
    N bytes   header      JSON, always plaintext (see below)
    remaining payload     the ZIP archive bytes, or its AES-256-GCM
                           ciphertext if encryption is enabled

The header must stay plaintext and readable *before* any decryption
happens — it's the only way a caller can know whether a passphrase is
even needed and which KDF parameters to use to derive the key. Nothing
sensitive belongs in it: it carries only the encryption parameters
(salt, KDF cost factors, nonce), never a password or derived key.

Cryptographic primitives are both from well-reviewed libraries, never
hand-rolled (Section 19): AES-256-GCM via the `cryptography` package,
Argon2id via `argon2-cffi`. The derived key is used only in memory and
is never written anywhere, including this header.
"""

import json
import os

from argon2.low_level import Type, hash_secret_raw
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

MAGIC = b"ICPKG001"

# Deliberately conservative-but-usable defaults (RFC 9106's "low-memory"
# recommendation is 64 MiB / t=3; this is comfortably above that) — a
# fixed choice today, not yet exposed as a hardware-profile-tuned
# setting (tracked as an open item alongside the hardware-sizing wizard
# this doesn't exist yet either).
ARGON2_TIME_COST = 3
ARGON2_MEMORY_COST_KIB = 256 * 1024  # 256 MiB
ARGON2_PARALLELISM = 4
ARGON2_SALT_BYTES = 16
AES_KEY_BYTES = 32  # AES-256
AES_NONCE_BYTES = 12  # standard GCM nonce size


class ContainerError(Exception):
    pass


class DecryptionFailed(ContainerError):
    """Wrong passphrase, or the ciphertext was tampered with — AES-GCM's
    authentication tag catches both; there is no way to distinguish
    them, which is the correct, safe behavior (never reveal which)."""


def _derive_key(passphrase: str, salt: bytes) -> bytes:
    return hash_secret_raw(
        secret=passphrase.encode("utf-8"),
        salt=salt,
        time_cost=ARGON2_TIME_COST,
        memory_cost=ARGON2_MEMORY_COST_KIB,
        parallelism=ARGON2_PARALLELISM,
        hash_len=AES_KEY_BYTES,
        type=Type.ID,  # Argon2id specifically (Section 19)
    )


def write_container(zip_bytes: bytes, *, passphrase: str | None = None) -> bytes:
    encryption_meta = None
    payload = zip_bytes

    if passphrase is not None:
        salt = os.urandom(ARGON2_SALT_BYTES)
        nonce = os.urandom(AES_NONCE_BYTES)
        key = _derive_key(passphrase, salt)
        payload = AESGCM(key).encrypt(nonce, zip_bytes, associated_data=None)
        encryption_meta = {
            "algorithm": "AES-256-GCM",
            "kdf": "argon2id",
            "kdf_params": {
                "time_cost": ARGON2_TIME_COST,
                "memory_cost_kib": ARGON2_MEMORY_COST_KIB,
                "parallelism": ARGON2_PARALLELISM,
            },
            "salt": salt.hex(),
            "nonce": nonce.hex(),
        }

    header = json.dumps({"format": "intracloud-portable-container", "encryption": encryption_meta}).encode(
        "utf-8"
    )
    return MAGIC + len(header).to_bytes(4, "big") + header + payload


def read_container_header(data: bytes) -> dict:
    if data[:8] != MAGIC:
        raise ContainerError("not an Intra-Cloud portable package (bad magic bytes)")
    header_len = int.from_bytes(data[8:12], "big")
    try:
        return json.loads(data[12 : 12 + header_len])
    except json.JSONDecodeError as exc:
        raise ContainerError("corrupt package header") from exc


def read_container_payload(data: bytes, *, passphrase: str | None = None) -> bytes:
    """Returns the plain ZIP bytes, decrypting first if the package is
    encrypted. Raises DecryptionFailed if a passphrase is required but
    wrong (or missing), or ContainerError for any other structural
    problem — never silently returns garbage as if it were the real
    payload."""
    header = read_container_header(data)
    header_len = int.from_bytes(data[8:12], "big")
    payload = data[12 + header_len :]

    encryption = header.get("encryption")
    if encryption is None:
        return payload

    if passphrase is None:
        raise DecryptionFailed("this package is encrypted; a passphrase is required")

    try:
        salt = bytes.fromhex(encryption["salt"])
        nonce = bytes.fromhex(encryption["nonce"])
        kdf_params = encryption["kdf_params"]
    except (KeyError, ValueError) as exc:
        raise ContainerError("corrupt encryption metadata in package header") from exc

    key = hash_secret_raw(
        secret=passphrase.encode("utf-8"),
        salt=salt,
        time_cost=kdf_params["time_cost"],
        memory_cost=kdf_params["memory_cost_kib"],
        parallelism=kdf_params["parallelism"],
        hash_len=AES_KEY_BYTES,
        type=Type.ID,
    )
    try:
        return AESGCM(key).decrypt(nonce, payload, associated_data=None)
    except InvalidTag as exc:
        raise DecryptionFailed("wrong passphrase, or the package is corrupted/tampered with") from exc
