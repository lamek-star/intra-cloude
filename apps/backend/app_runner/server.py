"""
The runner's HTTP API (internal network only, every call needs RUNNER_TOKEN):

    POST   /apps/<site>/deploy   X-Deploy: base64(JSON metadata), body: tar of the app's files
    POST   /apps/<site>/stop     the app stops and its route is removed
    POST   /apps/<site>/start    the app starts again with its route
    DELETE /apps/<site>          container, network, images and route removed
    GET    /apps/<site>          {"state": "running" | "stopped" | "missing" | ..., "log": "..."}
    GET    /healthz

Nothing in a request chooses an image, a command, a mount, a capability or a network: recipe.py decides.
"""

from __future__ import annotations

import base64
import hmac
import io
import json
import os
import posixpath
import re
import tarfile
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import recipe
from .docker import Docker, DockerError

MAX_UPLOAD = 1024 * 1024 * 1024  # 1 GiB of app files at most
_PATH = re.compile(r"^/apps/([0-9a-f]{32})(/deploy|/stop|/start|/route)?$")


class Runner:
    def __init__(
        self,
        docker: Docker,
        *,
        project: str,
        routes_dir: str,
        runtime_image: str,
        memory_mb: int,
        nano_cpus: int,
        tunnel_image: str = "",
        edge_network: str = "",
    ):
        self.docker = docker
        self.tunnel_image = tunnel_image
        self.edge_network = edge_network
        self.project = project
        self.routes_dir = routes_dir
        self.runtime_image = runtime_image
        self.memory_mb = memory_mb
        self.nano_cpus = nano_cpus
        self.lock = threading.Lock()

    # ---- the proxy
    def proxy(self) -> str:
        found = self.docker.containers(f"com.docker.compose.project={self.project}")
        for c in found:
            if c.get("Labels", {}).get("com.docker.compose.service") == "proxy":
                return c["Id"]
        raise DockerError(503, "the proxy is not running")

    def _ensure_proxy_on(self, network: str) -> None:
        proxy = self.proxy()
        info = self.docker.network(network)
        if info and proxy not in (info.get("Containers") or {}):
            self.docker.connect(network, proxy, [recipe.API_ALIAS])

    def _put(self, name: str, text: str) -> None:
        path = os.path.join(self.routes_dir, name)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.write(text)
        os.replace(tmp, path)

    def _remove(self, name: str) -> None:
        try:
            os.remove(os.path.join(self.routes_dir, name))
        except FileNotFoundError:
            pass

    def _write_route(self, meta: dict) -> None:
        """The path route, the own-name route (if the site has a name) and what they were made from, so a
        restarted app gets the same routes back."""
        n = recipe.names(meta["site"])
        route = {
            "site": meta["site"],
            "slug": meta["slug"],
            "hostname": meta.get("hostname") or "",
            "internet_hostname": meta.get("internet_hostname") or "",
        }
        self._put(n["route_meta"], json.dumps(route))
        self._put(n["route"], recipe.route(route))
        if route["hostname"]:
            self._put(n["host_route"], recipe.host_route(route))
        else:
            self._remove(n["host_route"])
        if route["internet_hostname"]:
            self._put(n["internet_route"], recipe.host_route(route, route["internet_hostname"]))
        else:
            self._remove(n["internet_route"])

    def _saved_route(self, site: str) -> dict | None:
        try:
            with open(
                os.path.join(self.routes_dir, recipe.names(site)["route_meta"]), encoding="utf-8"
            ) as fh:
                return recipe.check_route(json.load(fh))
        except (FileNotFoundError, ValueError, recipe.RecipeError):
            return None

    def _drop_route(self, site: str, *, forget: bool = False) -> None:
        n = recipe.names(site)
        self._remove(n["route"])
        self._remove(n["host_route"])
        self._remove(n["internet_route"])
        if forget:
            self._remove(n["route_meta"])

    def _reload_proxy(self) -> None:
        code = self.docker.exec(
            self.proxy(), ["caddy", "reload", "--config", "/etc/caddy/Caddyfile", "--adapter", "caddyfile"]
        )
        if code != 0:
            raise DockerError(500, "the proxy refused the new route")

    # ---- operations
    def deploy(self, meta: dict, upload) -> dict:
        n = recipe.names(meta["site"])
        image = f"{n['image']}:{meta['version']}"
        with tempfile.TemporaryFile() as context:
            size = _build_context(context, upload, recipe.dockerfile(self.runtime_image))
            context.seek(0)
            with self.lock:
                self.docker.build(image, context, size)
                if self.docker.network(n["network"]) is None:
                    self.docker.create_network(recipe.network_config(meta, self.project))
                self._ensure_proxy_on(n["network"])
                self.docker.remove(n["container"])
                self.docker.create(
                    n["container"],
                    recipe.container_config(
                        meta,
                        image=image,
                        memory_mb=self.memory_mb,
                        nano_cpus=self.nano_cpus,
                        project=self.project,
                    ),
                )
                self.docker.start(n["container"])
                self._write_route(meta)
                self._reload_proxy()
                self._drop_old_images(meta["site"], keep=image)
        return self.status(meta["site"])

    def stop(self, site: str) -> dict:
        with self.lock:
            self.docker.stop(recipe.names(site)["container"])
            self._drop_route(site)
            self._reload_proxy()
        return self.status(site)

    def start(self, site: str) -> dict:
        n = recipe.names(site)
        with self.lock:
            info = self.docker.inspect(n["container"])
            if info is None:
                return {"state": "missing", "log": ""}
            labels = info["Config"]["Labels"]
            self._ensure_proxy_on(n["network"])
            self.docker.start(n["container"])
            self._write_route(
                self._saved_route(site) or {"site": site, "slug": labels["intraforge.app.slug"]}
            )
            self._reload_proxy()
        return self.status(site)

    def set_route(self, meta: dict) -> dict:
        """The site's own name changed: rewrite its routes (only while the app is running)."""
        with self.lock:
            info = self.docker.inspect(recipe.names(meta["site"])["container"])
            running = bool(info and info["State"].get("Running"))
            if running:
                self._write_route(meta)
            else:
                self._put(recipe.names(meta["site"])["route_meta"], json.dumps(meta))
            self._reload_proxy()
        return self.status(meta["site"])

    def remove(self, site: str) -> dict:
        n = recipe.names(site)
        with self.lock:
            self.docker.remove(n["container"])
            self._drop_route(site, forget=True)
            self._reload_proxy()
            info = self.docker.network(n["network"])
            for container in (info or {}).get("Containers") or {}:
                self.docker._request(
                    "POST",
                    f"/networks/{n['network']}/disconnect",
                    body={"Container": container, "Force": True},
                )
            self.docker.remove_network(n["network"])
            self._drop_old_images(site, keep=None)
        return {"state": "missing", "log": ""}

    def status(self, site: str) -> dict:
        info = self.docker.inspect(recipe.names(site)["container"])
        if info is None:
            return {"state": "missing", "log": ""}
        state = info["State"]
        running = bool(state.get("Running"))
        out = {
            "state": "running" if running else str(state.get("Status") or "stopped"),
            "restarts": int(info.get("RestartCount") or 0),
            "oom": bool(state.get("OOMKilled")),
            "log": "",
        }
        if not running or out["restarts"]:
            out["log"] = self.docker.logs(recipe.names(site)["container"])
        return out

    def reconcile(self) -> None:
        """After a restart of the proxy (an upgrade recreates it), put it back on every app's network and
        make sure it has loaded the routes."""
        with self.lock:
            changed = False
            for c in self.docker.containers(f"intraforge.project={self.project}"):
                site = c.get("Labels", {}).get("intraforge.app")
                if not site or not recipe.ID.match(site):
                    continue
                network = recipe.names(site)["network"]
                info = self.docker.network(network)
                if info is not None and self.proxy() not in (info.get("Containers") or {}):
                    self.docker.connect(network, self.proxy(), [recipe.API_ALIAS])
                    changed = True
            if changed:
                self._reload_proxy()

    # ---- the internet gate's tunnel
    def tunnel_start(self, token: str) -> dict:
        with self.lock:
            self.docker.remove(recipe.TUNNEL_CONTAINER)
            self.docker.create(
                recipe.TUNNEL_CONTAINER,
                recipe.tunnel_config(
                    token, image=self.tunnel_image, network=self.edge_network, project=self.project
                ),
            )
            self.docker.start(recipe.TUNNEL_CONTAINER)
        return self.tunnel_status()

    def tunnel_stop(self) -> dict:
        with self.lock:
            self.docker.remove(recipe.TUNNEL_CONTAINER)
        return {"state": "off", "log": ""}

    def tunnel_status(self) -> dict:
        info = self.docker.inspect(recipe.TUNNEL_CONTAINER)
        if info is None:
            return {"state": "off", "log": ""}
        running = bool(info["State"].get("Running"))
        return {
            "state": "running" if running else str(info["State"].get("Status") or "stopped"),
            "log": self.docker.logs(recipe.TUNNEL_CONTAINER, tail=15) if not running else "",
        }

    def _drop_old_images(self, site: str, keep: str | None) -> None:
        images = self.docker._request(
            "GET", "/images/json", query={"filters": json.dumps({"reference": [f"ifapp-{site}"]})}
        )
        for img in images or []:
            tags = img.get("RepoTags") or []
            if keep in tags:
                continue
            self.docker.remove_image(img["Id"])


def _build_context(out, upload, dockerfile: bytes) -> int:
    """Re-packs the uploaded files under app/ next to the generated Dockerfile. Only plain files with safe
    relative names are taken; everything else in the upload is refused."""
    total = 0
    with tarfile.open(fileobj=upload, mode="r|") as src, tarfile.open(fileobj=out, mode="w") as dst:
        info = tarfile.TarInfo("Dockerfile")
        info.size = len(dockerfile)
        dst.addfile(info, io.BytesIO(dockerfile))
        for member in src:
            name = member.name
            if not member.isfile():
                raise recipe.RecipeError(f"not a plain file: {name}")
            norm = posixpath.normpath(name)
            if norm.startswith(("/", "../")) or norm == ".." or "\\" in name or norm != name:
                raise recipe.RecipeError(f"unsafe name: {name}")
            total += member.size
            if total > MAX_UPLOAD:
                raise recipe.RecipeError("the app is too large")
            data = src.extractfile(member)
            copy = tarfile.TarInfo("app/" + norm)
            copy.size = member.size
            copy.mode = 0o644
            dst.addfile(copy, data)
    return out.tell()


def make_handler(runner: Runner, token: str):
    class Handler(BaseHTTPRequestHandler):
        server_version = "intraforge-app-runner"

        def log_message(self, fmt, *args):  # noqa: D401 - one line per request, no bodies or headers
            print(
                f"{self.command} {self.path.split('?')[0]} -> {args[1] if len(args) > 1 else ''}", flush=True
            )

        def _reply(self, status: int, body: dict) -> None:
            data = json.dumps(body).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _authorised(self) -> bool:
            given = self.headers.get("Authorization", "")
            return bool(token) and hmac.compare_digest(given.encode(), f"Bearer {token}".encode())

        def _route(self):
            if self.path == "/healthz":
                return "health", None
            if self.path in ("/tunnel", "/tunnel/start", "/tunnel/stop"):
                return self.path, None
            m = _PATH.match(self.path)
            return (m.group(2) or "", m.group(1)) if m else (None, None)

        def _handle(self, method: str):
            action, site = self._route()
            if action == "health" and method == "GET":
                return self._reply(200, {"ok": True})
            if not self._authorised():
                return self._reply(401, {"error": "unauthorised"})
            if action is None:
                return self._reply(404, {"error": "not found"})
            try:
                if method == "POST" and action == "/deploy":
                    meta = recipe.check_deploy(json.loads(base64.b64decode(self.headers.get("X-Deploy", ""))))
                    if meta["site"] != site:
                        raise recipe.RecipeError("site mismatch")
                    length = int(self.headers.get("Content-Length") or 0)
                    if length <= 0 or length > MAX_UPLOAD:
                        raise recipe.RecipeError("bad upload size")
                    return self._reply(200, runner.deploy(meta, _Limited(self.rfile, length)))
                if action == "/tunnel" and method == "GET":
                    return self._reply(200, runner.tunnel_status())
                if action == "/tunnel/start" and method == "POST":
                    if not runner.tunnel_image or not runner.edge_network:
                        raise recipe.RecipeError("the tunnel is not part of this installation")
                    token = base64.b64decode(self.headers.get("X-Tunnel", "")).decode("ascii", "replace")
                    return self._reply(200, runner.tunnel_start(token))
                if action == "/tunnel/stop" and method == "POST":
                    return self._reply(200, runner.tunnel_stop())
                if method == "POST" and action == "/route":
                    meta = recipe.check_route(json.loads(base64.b64decode(self.headers.get("X-Route", ""))))
                    if meta["site"] != site:
                        raise recipe.RecipeError("site mismatch")
                    return self._reply(200, runner.set_route(meta))
                if method == "POST" and action == "/stop":
                    return self._reply(200, runner.stop(site))
                if method == "POST" and action == "/start":
                    return self._reply(200, runner.start(site))
                if method == "DELETE" and action == "":
                    return self._reply(200, runner.remove(site))
                if method == "GET" and action == "":
                    return self._reply(200, runner.status(site))
                return self._reply(405, {"error": "method not allowed"})
            except (recipe.RecipeError, ValueError, tarfile.TarError) as exc:
                return self._reply(400, {"error": str(exc)[:300]})
            except DockerError as exc:
                return self._reply(502, {"error": str(exc)[:500]})

        def do_GET(self):
            self._handle("GET")

        def do_POST(self):
            self._handle("POST")

        def do_DELETE(self):
            self._handle("DELETE")

    return Handler


class _Limited(io.RawIOBase):
    """Reads at most `length` bytes of the request body."""

    def __init__(self, raw, length: int):
        self._raw, self._left = raw, length

    def readable(self):
        return True

    def readinto(self, buffer):
        if self._left <= 0:
            return 0
        chunk = self._raw.read(min(len(buffer), self._left))
        n = len(chunk)
        buffer[:n] = chunk
        self._left -= n
        return n


def serve() -> None:
    token = os.environ.get("RUNNER_TOKEN", "")
    if len(token) < 24:
        raise SystemExit("RUNNER_TOKEN must be set (at least 24 characters).")
    runner = Runner(
        Docker(os.environ.get("RUNNER_DOCKER_SOCKET", "/var/run/docker.sock")),
        project=os.environ.get("RUNNER_PROJECT", "intraforge-shop"),
        routes_dir=os.environ.get("RUNNER_ROUTES_DIR", "/routes"),
        runtime_image=os.environ["RUNNER_RUNTIME_IMAGE"],
        memory_mb=int(os.environ.get("RUNNER_APP_MEMORY_MB", "256")),
        nano_cpus=int(float(os.environ.get("RUNNER_APP_CPUS", "0.5")) * 1_000_000_000),
        tunnel_image=os.environ.get("RUNNER_TUNNEL_IMAGE", ""),
        edge_network=os.environ.get("RUNNER_EDGE_NETWORK", ""),
    )

    def keep_reconciled():
        while True:
            try:
                runner.reconcile()
            except Exception as exc:  # noqa: BLE001 - keep trying; report what failed
                print(f"reconcile: {exc}", flush=True)
            time.sleep(60)

    threading.Thread(target=keep_reconciled, daemon=True).start()
    server = ThreadingHTTPServer(
        ("0.0.0.0", int(os.environ.get("RUNNER_PORT", "8700"))), make_handler(runner, token)
    )
    print("app runner listening", flush=True)
    server.serve_forever()
