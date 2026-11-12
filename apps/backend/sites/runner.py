"""
The backend's side of the app runner (ADR-0020): a token-authenticated HTTP client for its fixed operations.
The backend never talks to Docker; it hands the runner a server app's files and metadata and reads back state.
"""

from __future__ import annotations

import base64
import http.client
import json
import tarfile
import tempfile
import urllib.parse

from django.conf import settings

from storage.backends import get_client

TIMEOUT_SECONDS = 600


class RunnerUnavailable(Exception):
    """The runner is not configured or did not answer."""


class RunnerRefused(Exception):
    """The runner answered with an error (a bad upload, a build or start failure)."""


def configured() -> bool:
    return bool(settings.SITES_RUNNER_URL and settings.SITES_RUNNER_TOKEN)


def _call(method: str, path: str, *, body=None, size: int = 0, headers: dict | None = None) -> dict:
    if not configured():
        raise RunnerUnavailable("Server apps are not available on this installation (no app runner).")
    url = urllib.parse.urlsplit(settings.SITES_RUNNER_URL)
    conn = http.client.HTTPConnection(url.hostname, url.port or 80, timeout=TIMEOUT_SECONDS)
    hdrs = {"Authorization": f"Bearer {settings.SITES_RUNNER_TOKEN}", **(headers or {})}
    if body is not None:
        hdrs["Content-Length"] = str(size)
    try:
        conn.request(method, path, body=body, headers=hdrs)
        resp = conn.getresponse()
        payload = resp.read(1_000_000)
    except OSError as exc:
        raise RunnerUnavailable("The app runner is not answering. Try again in a minute.") from exc
    finally:
        conn.close()
    try:
        data = json.loads(payload or b"{}")
    except ValueError:
        data = {}
    if resp.status >= 400:
        raise RunnerRefused(str(data.get("error") or f"The app runner answered {resp.status}.")[:500])
    return data


def deploy(*, site, version, env: dict) -> dict:
    """Builds and starts the version's container. The files go to the runner as a tar, straight from object
    storage; the metadata travels in a header."""
    meta = {
        "site": site.id.hex,
        "slug": site.slug,
        "version": version.id.hex,
        "entry": version.manifest["entry"],
        "hostname": site.hostname or "",
        "internet_hostname": site.internet_hostname or "",
        "env": env,
    }
    client = get_client()
    with tempfile.TemporaryFile() as bundle:
        with tarfile.open(fileobj=bundle, mode="w") as tar:
            for path, entry in sorted(version.files.items()):
                info = tarfile.TarInfo(path)
                info.size = int(entry["size"])
                info.mode = 0o644
                tar.addfile(info, client.get_stream(version.storage_prefix + path))
        size = bundle.tell()
        bundle.seek(0)
        return _call(
            "POST",
            f"/apps/{site.id.hex}/deploy",
            body=bundle,
            size=size,
            headers={
                "Content-Type": "application/x-tar",
                "X-Deploy": base64.b64encode(json.dumps(meta).encode()).decode(),
            },
        )


def route(site) -> dict:
    """Rewrites the app's proxy routes after its own name changed."""
    meta = {
        "site": site.id.hex,
        "slug": site.slug,
        "hostname": site.hostname or "",
        "internet_hostname": site.internet_hostname or "",
    }
    return _call(
        "POST",
        f"/apps/{site.id.hex}/route",
        headers={"X-Route": base64.b64encode(json.dumps(meta).encode()).decode()},
    )


def stop(site) -> dict:
    return _call("POST", f"/apps/{site.id.hex}/stop")


def start(site) -> dict:
    return _call("POST", f"/apps/{site.id.hex}/start")


def remove(site) -> dict:
    return _call("DELETE", f"/apps/{site.id.hex}")


def status(site) -> dict:
    return _call("GET", f"/apps/{site.id.hex}")


def logs(site) -> dict:
    return _call("GET", f"/apps/{site.id.hex}/logs")


# ---- the internet gate's tunnel (ADR-0020 decision 4)


def tunnel_start(token: str) -> dict:
    return _call("POST", "/tunnel/start", headers={"X-Tunnel": base64.b64encode(token.encode()).decode()})


def tunnel_stop() -> dict:
    return _call("POST", "/tunnel/stop")


def tunnel_status() -> dict:
    return _call("GET", "/tunnel")
