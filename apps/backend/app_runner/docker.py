"""
A minimal Docker Engine API client over the Unix socket, standard library only. It exposes just the calls the
runner's recipe needs.
"""

from __future__ import annotations

import http.client
import json
import socket
import urllib.parse

API = "/v1.43"


class DockerError(RuntimeError):
    def __init__(self, status: int, message: str):
        super().__init__(f"Docker {status}: {message}")
        self.status = status


class _UnixConnection(http.client.HTTPConnection):
    def __init__(self, path: str, timeout: float):
        super().__init__("localhost", timeout=timeout)
        self._path = path

    def connect(self):
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(self.timeout)
        sock.connect(self._path)
        self.sock = sock


class Docker:
    def __init__(self, socket_path: str = "/var/run/docker.sock", timeout: float = 600.0):
        self._socket = socket_path
        self._timeout = timeout

    def _request(self, method: str, path: str, *, query=None, body=None, headers=None, raw=False):
        url = API + path + ("?" + urllib.parse.urlencode(query) if query else "")
        conn = _UnixConnection(self._socket, self._timeout)
        try:
            data = body
            hdrs = dict(headers or {})
            if body is not None and not isinstance(body, (bytes, bytearray)) and not hasattr(body, "read"):
                data = json.dumps(body).encode()
                hdrs.setdefault("Content-Type", "application/json")
            conn.request(method, url, body=data, headers=hdrs)
            resp = conn.getresponse()
            payload = resp.read()
        finally:
            conn.close()
        if resp.status >= 400:
            try:
                message = json.loads(payload or b"{}").get("message", "")
            except ValueError:
                message = payload[:300].decode("utf-8", "replace")
            raise DockerError(resp.status, message)
        if raw:
            return payload
        return json.loads(payload) if payload else None

    # ---- images
    def build(self, tag: str, context_file, size: int) -> None:
        """Builds from a tar context (Dockerfile at its top). The build log is read to the end; an error in it
        fails the build."""
        payload = self._request(
            "POST",
            "/build",
            query={"t": tag, "rm": "1", "forcerm": "1", "pull": "0", "q": "1"},
            body=context_file,
            headers={"Content-Type": "application/x-tar", "Content-Length": str(size)},
            raw=True,
        )
        for line in payload.splitlines():
            try:
                item = json.loads(line)
            except ValueError:
                continue
            if "error" in item:
                raise DockerError(500, str(item.get("error"))[:500])

    def remove_image(self, name: str) -> None:
        try:
            self._request("DELETE", f"/images/{urllib.parse.quote(name)}", query={"force": "1"})
        except DockerError as exc:
            if exc.status != 404:
                raise

    # ---- networks
    def network(self, name: str):
        try:
            return self._request("GET", f"/networks/{urllib.parse.quote(name)}")
        except DockerError as exc:
            if exc.status == 404:
                return None
            raise

    def create_network(self, config: dict) -> None:
        self._request("POST", "/networks/create", body=config)

    def connect(self, network: str, container: str, aliases: list[str]) -> None:
        self._request(
            "POST",
            f"/networks/{urllib.parse.quote(network)}/connect",
            body={"Container": container, "EndpointConfig": {"Aliases": aliases}},
        )

    def remove_network(self, name: str) -> None:
        try:
            self._request("DELETE", f"/networks/{urllib.parse.quote(name)}")
        except DockerError as exc:
            if exc.status != 404:
                raise

    # ---- containers
    def containers(self, label: str) -> list[dict]:
        return self._request(
            "GET", "/containers/json", query={"all": "1", "filters": json.dumps({"label": [label]})}
        )

    def inspect(self, name: str):
        try:
            return self._request("GET", f"/containers/{urllib.parse.quote(name)}/json")
        except DockerError as exc:
            if exc.status == 404:
                return None
            raise

    def create(self, name: str, config: dict) -> str:
        return self._request("POST", "/containers/create", query={"name": name}, body=config)["Id"]

    def start(self, name: str) -> None:
        self._request("POST", f"/containers/{urllib.parse.quote(name)}/start")

    def stop(self, name: str) -> None:
        try:
            self._request("POST", f"/containers/{urllib.parse.quote(name)}/stop", query={"t": "10"})
        except DockerError as exc:
            if exc.status not in (304, 404):
                raise

    def remove(self, name: str) -> None:
        try:
            self._request("DELETE", f"/containers/{urllib.parse.quote(name)}", query={"force": "1"})
        except DockerError as exc:
            if exc.status != 404:
                raise

    def logs(self, name: str, tail: int = 40) -> str:
        raw = self._request(
            "GET",
            f"/containers/{urllib.parse.quote(name)}/logs",
            query={"stdout": "1", "stderr": "1", "tail": str(tail)},
            raw=True,
        )
        # Multiplexed stream: 8-byte frame headers before each chunk.
        out, i = [], 0
        while i + 8 <= len(raw):
            size = int.from_bytes(raw[i + 4 : i + 8], "big")
            out.append(raw[i + 8 : i + 8 + size])
            i += 8 + size
        return b"".join(out).decode("utf-8", "replace")[-4000:]

    def exec(self, container: str, cmd: list[str]) -> int:
        created = self._request(
            "POST",
            f"/containers/{urllib.parse.quote(container)}/exec",
            body={"Cmd": cmd, "AttachStdout": True, "AttachStderr": True},
        )
        self._request("POST", f"/exec/{created['Id']}/start", body={"Detach": False, "Tty": False}, raw=True)
        return int(self._request("GET", f"/exec/{created['Id']}/json").get("ExitCode") or 0)
