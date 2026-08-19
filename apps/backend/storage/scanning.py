"""
Malware-scan integration for uploaded files (Section 33 of the master
prompt). Talks to a ClamAV daemon (`clamd`) over its network socket —
never a bundled/vendored scan engine, and never a check that can be
satisfied without actually reaching the daemon.

Deliberately fails closed: `scan_stream` raising `ScanUnavailable` (the
daemon is unreachable, misconfigured, or returns something we don't
recognize) must never be interpreted by a caller as "clean" — see
`storage/services.py::_scan_for_malware`.
"""

import logging

import clamd
from django.conf import settings

logger = logging.getLogger(__name__)


class ScanUnavailable(Exception):
    """The scanner could not be reached or returned an unrecognized
    response. Callers must treat this as "not known to be clean", not
    as a pass-through success."""


class ScanResult:
    def __init__(self, clean: bool, signature: str = ""):
        self.clean = clean
        self.signature = signature


def get_scanner() -> "clamd.ClamdNetworkSocket":
    return clamd.ClamdNetworkSocket(
        host=settings.CLAMAV_HOST,
        port=settings.CLAMAV_PORT,
        timeout=settings.CLAMAV_TIMEOUT_SECONDS,
    )


def scan_stream(fileobj, *, scanner=None) -> ScanResult:
    """Streams `fileobj` to ClamAV's INSTREAM command. Caller is
    responsible for `seek(0)` before and after — this never buffers the
    whole file itself beyond what clamd's own client does."""
    scanner = scanner or get_scanner()
    try:
        result = scanner.instream(fileobj)
    except (clamd.ConnectionError, OSError) as exc:
        raise ScanUnavailable("malware scanner unreachable") from exc

    outcome = result.get("stream")
    if outcome is None:
        raise ScanUnavailable(f"malware scanner returned an unrecognized response: {result!r}")

    scan_status, signature = outcome
    if scan_status == "OK":
        return ScanResult(clean=True)
    if scan_status == "FOUND":
        return ScanResult(clean=False, signature=signature or "")
    raise ScanUnavailable(f"malware scanner returned unexpected status: {scan_status!r}")
