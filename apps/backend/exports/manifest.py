"""
The .icp manifest: a versioned, machine-readable description of a
portable export package's contents (Section 13 of the master prompt).
Kept as a plain dict (not a Django model) — it lives inside the package
itself, travels to other installations, and must be readable by a
future version of this code that may not share this version's models.
"""

from pathlib import Path

FORMAT_NAME = "intracloud-portable"

# Bumped whenever the *container/manifest structure* changes in a way
# that isn't backward-readable — independent of PRODUCT_VERSION, which
# tracks the source installation's own release (Section 18 of the
# master prompt: these are deliberately two different numbers).
FORMAT_VERSION = 1


def _read_product_version() -> str:
    """Reads the repo-root VERSION file — the same single source of
    truth control-center/IntraCloud.ControlCenter.csproj and
    installer/wix/Package.wixproj already use for the Windows side.
    Checked in order: the read-only /VERSION mount docker-compose.yml
    provides for backend/worker (the build context is ./apps/backend,
    which can't COPY a file from outside itself), then walking up from
    this file's own location looking for a VERSION file. That walk is
    deliberately open-ended, not a fixed parent count: this module's
    real on-disk depth differs between the Docker image (Dockerfile's
    WORKDIR /app copies apps/backend's *contents* to /app, so this file
    lands at /app/exports/manifest.py, two levels shallower than the
    repo root) and running outside Docker (local dev, pytest --
    apps/backend/exports/manifest.py, three levels below repo root).
    Confirmed the hard way: a hardcoded parents[3] worked in one
    context and threw IndexError in the other. Falls back to a
    placeholder only if nothing is found, rather than raising -- a
    missing version string must never block producing an export."""
    mounted = Path("/VERSION")
    if mounted.is_file():
        try:
            return mounted.read_text().strip()
        except OSError:
            pass

    for directory in Path(__file__).resolve().parents:
        candidate = directory / "VERSION"
        if candidate.is_file():
            try:
                return candidate.read_text().strip()
            except OSError:
                continue
    return "0.0.0-unreleased"


PRODUCT_VERSION = _read_product_version()

# What Section 12 lists as things a full export *could* contain, that
# this first implementation deliberately does not. Recorded in every
# manifest's "excluded" list rather than silently omitted — no export
# should ever look "complete" when it isn't (no-silent-caps discipline).
EXCLUDED_SCOPE = [
    # Applications and their Environments (environments app) ARE
    # included below (manifest["applications"]) -- what's specifically
    # excluded is the credential/secret *material* itself: a bearer
    # token's plaintext exists nowhere after issuance (not even this
    # server keeps it -- only its hash), and an EnvironmentSecret's
    # value is never exported even though its ciphertext could
    # technically travel (Section 17: "do not create an export format
    # that exposes plaintext secrets" -- and a decryptable ciphertext
    # under this installation's own CREDENTIAL_ENCRYPTION_KEY would be
    # exactly that, once restored on the same key). Restoring an
    # Environment's *secret keys* (names only, no values) is exactly
    # how the operator knows what to re-create -- see
    # exports/restorer.py's applications restore warnings.
    "application_credentials",  # bearer tokens -- never existed as recoverable plaintext
    "environment_secret_values",  # keys are restored; values are not
    "environment_webhook_signing_secrets",  # regenerated fresh on restore, never copied
    "connected_databases",  # external DB connector definitions
    "sharing",  # internal ShareGrants
    "analytics",  # not implemented anywhere in the product yet
    "user_password_hashes",  # opt-in only, never included by default
]


class ManifestError(Exception):
    pass


def new_manifest(*, export_id: str, export_type: str = "organization") -> dict:
    return {
        "format": FORMAT_NAME,
        "format_version": FORMAT_VERSION,
        "product_version": PRODUCT_VERSION,
        "export_id": export_id,
        "export_type": export_type,
        "organization": None,  # filled in by builder.py — workspaces/projects/buckets/files nested inside
        "databases": {},  # filled in by builder.py
        "applications": [],  # filled in by builder.py — each with its environments nested inside
        "checksums": {},  # filled in as files are added to the archive
        "encryption": None,  # filled in if the caller requests encryption
        "excluded": EXCLUDED_SCOPE,
    }


def validate_manifest_shape(manifest: dict) -> None:
    """Structural validation only — checksum/content validation happens
    in restorer.py, which needs the actual archive bytes to check
    against, not just the manifest."""
    if not isinstance(manifest, dict):
        raise ManifestError("manifest is not a JSON object")
    if manifest.get("format") != FORMAT_NAME:
        raise ManifestError(f"not an {FORMAT_NAME} package")
    if not isinstance(manifest.get("format_version"), int):
        raise ManifestError("manifest is missing a valid format_version")
    if manifest["format_version"] > FORMAT_VERSION:
        raise ManifestError(
            f"this package's format_version ({manifest['format_version']}) is newer than this "
            f"installation understands ({FORMAT_VERSION}) — upgrade before importing it"
        )
    if manifest.get("export_type") != "organization":
        raise ManifestError(f"unsupported export_type: {manifest.get('export_type')!r}")
    if not isinstance(manifest.get("organization"), dict):
        raise ManifestError("manifest is missing organization data")
