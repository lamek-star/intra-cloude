"""
The .icp manifest: a versioned, machine-readable description of a
portable export package's contents (Section 13 of the master prompt).
Kept as a plain dict (not a Django model) — it lives inside the package
itself, travels to other installations, and must be readable by a
future version of this code that may not share this version's models.
"""

FORMAT_NAME = "intracloud-portable"

# Bumped whenever the *container/manifest structure* changes in a way
# that isn't backward-readable — independent of PRODUCT_VERSION, which
# tracks the source installation's own release (Section 18 of the
# master prompt: these are deliberately two different numbers). There
# is no formal product release-versioning scheme yet (tracked as an
# open item), so PRODUCT_VERSION is currently a fixed placeholder.
FORMAT_VERSION = 1
PRODUCT_VERSION = "0.0.0-unreleased"

# What Section 12 lists as things a full export *could* contain, that
# this first implementation deliberately does not. Recorded in every
# manifest's "excluded" list rather than silently omitted — no export
# should ever look "complete" when it isn't (no-silent-caps discipline).
EXCLUDED_SCOPE = [
    "applications",  # service accounts / API credentials
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
