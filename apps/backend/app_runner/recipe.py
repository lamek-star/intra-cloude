"""
The one container recipe for a hosted server app (ADR-0020 decision 1). Everything about how an app runs is
decided here, never by the upload: the image is the bundled runtime plus the app's files, the command is
always `node <entry>`, and the container is locked down (non-root, read-only, no capabilities, resource
limits, its own internal network with no internet).
"""

from __future__ import annotations

import re

ID = re.compile(r"^[0-9a-f]{32}$")
SLUG = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,48}[a-z0-9])?$")
ENTRY = re.compile(r"^[A-Za-z0-9._/-]+\.(js|mjs|cjs)$")
VERSION = re.compile(r"^[0-9a-f]{32}$")
# A site's own name on the shop network (the backend validates it against IntraForge's names first).
HOSTNAME = re.compile(
    r"^(?=.{4,253}$)[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?(\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)+$"
)
# The only environment an app receives; values are checked to be plain strings.
ALLOWED_ENV = {"IF_API_URL", "IF_API_TOKEN", "IF_SITE_NAME"}
APP_PORT = 3000
API_ALIAS = "intraforge"


class RecipeError(ValueError):
    pass


def check_deploy(meta: dict) -> dict:
    """Validates a deploy request's metadata; returns it normalised. Anything unexpected is refused."""
    if not isinstance(meta, dict):
        raise RecipeError("bad request")
    site, slug, version, entry = meta.get("site"), meta.get("slug"), meta.get("version"), meta.get("entry")
    if not (isinstance(site, str) and ID.match(site)):
        raise RecipeError("bad site id")
    if not (isinstance(slug, str) and SLUG.match(slug)):
        raise RecipeError("bad address")
    if not (isinstance(version, str) and VERSION.match(version)):
        raise RecipeError("bad version")
    if not (isinstance(entry, str) and ENTRY.match(entry)) or ".." in entry.split("/"):
        raise RecipeError("bad entry file")
    env = meta.get("env") or {}
    if not isinstance(env, dict) or set(env) - ALLOWED_ENV:
        raise RecipeError("bad environment")
    for key, value in env.items():
        if not isinstance(value, str) or len(value) > 500 or "\n" in value or "\x00" in value:
            raise RecipeError(f"bad value for {key}")
    return {
        "site": site,
        "slug": slug,
        "version": version,
        "entry": entry,
        "hostname": check_hostname(meta.get("hostname")),
        "internet_hostname": check_hostname(meta.get("internet_hostname")),
        "env": dict(env),
    }


def check_hostname(value) -> str:
    if value in (None, ""):
        return ""
    if not (isinstance(value, str) and HOSTNAME.match(value)):
        raise RecipeError("bad site name")
    return value


def check_route(meta: dict) -> dict:
    """Metadata of a route-only change (the site's own name changed)."""
    if not isinstance(meta, dict):
        raise RecipeError("bad request")
    site, slug = meta.get("site"), meta.get("slug")
    if not (isinstance(site, str) and ID.match(site)) or not (isinstance(slug, str) and SLUG.match(slug)):
        raise RecipeError("bad route")
    return {
        "site": site,
        "slug": slug,
        "hostname": check_hostname(meta.get("hostname")),
        "internet_hostname": check_hostname(meta.get("internet_hostname")),
    }


def names(site: str) -> dict:
    return {
        "container": f"ifapp-{site}",
        "network": f"ifapp-{site}",
        "image": f"ifapp-{site}",
        "route": f"{site}.caddy",
        "host_route": f"{site}.host",
        "internet_route": f"{site}.internet",
        "route_meta": f"{site}.json",
    }


def dockerfile(runtime_image: str) -> bytes:
    """Only copies the uploaded files onto the bundled runtime: nothing is downloaded or installed."""
    return (
        f"FROM {runtime_image}\nWORKDIR /app\nCOPY --chown=1000:1000 app/ /app/\nUSER 1000:1000\n"
    ).encode()


def container_config(meta: dict, *, image: str, memory_mb: int, nano_cpus: int, project: str) -> dict:
    """The Docker Engine API body for creating the app's container."""
    n = names(meta["site"])
    env = {
        "NODE_ENV": "production",
        "PORT": str(APP_PORT),
        "HOME": "/tmp",
        "IF_BASE_PATH": f"/{meta['slug']}",
        **meta["env"],
    }
    return {
        "Image": image,
        "Cmd": ["node", meta["entry"]],
        "WorkingDir": "/app",
        "User": "1000:1000",
        "Env": [f"{k}={v}" for k, v in sorted(env.items())],
        "ExposedPorts": {f"{APP_PORT}/tcp": {}},
        "Labels": {
            "intraforge.app": meta["site"],
            "intraforge.app.slug": meta["slug"],
            "intraforge.app.version": meta["version"],
            "intraforge.project": project,
        },
        "HostConfig": {
            "NetworkMode": n["network"],
            "ReadonlyRootfs": True,
            "Tmpfs": {"/tmp": "rw,noexec,nosuid,size=64m"},
            "CapDrop": ["ALL"],
            "SecurityOpt": ["no-new-privileges:true"],
            "Memory": memory_mb * 1024 * 1024,
            "MemorySwap": memory_mb * 1024 * 1024,
            "NanoCpus": nano_cpus,
            "PidsLimit": 128,
            "RestartPolicy": {"Name": "unless-stopped"},
            "LogConfig": {"Type": "json-file", "Config": {"max-size": "5m", "max-file": "2"}},
            "Privileged": False,
            "PortBindings": {},
        },
    }


def network_config(meta: dict, project: str) -> dict:
    """An internal network per app: no internet, nothing on it but the app and the proxy."""
    return {
        "Name": names(meta["site"])["network"],
        "Internal": True,
        "Labels": {"intraforge.app": meta["site"], "intraforge.project": project},
    }


def route(meta: dict) -> str:
    """The proxy route for the app on the sites port: its address prefix is stripped, IntraForge's cookies
    never reach it and it may set none (a browser shares cookies across ports of one host)."""
    slug, upstream = meta["slug"], f"{names(meta['site'])['container']}:{APP_PORT}"
    return (
        f"# hosted server app {meta['site']} (generated by the app runner; do not edit)\n"
        f"@app_{meta['site']} path /{slug} /{slug}/*\n"
        f"handle @app_{meta['site']} {{\n"
        f"\tredir /{slug} /{slug}/ 308\n"
        f"\turi strip_prefix /{slug}\n"
        f"\treverse_proxy {upstream} {{\n"
        f"\t\theader_up X-Forwarded-Prefix /{slug}\n"
        "\t}\n"
        "}\n"
    )


def host_route(meta: dict, host: str | None = None) -> str:
    """The route for the app's own name (https://<name>:<sites port>/): served at its root, and -- a separate
    host from IntraForge -- allowed to keep cookies for that name only (a Domain attribute is removed, so it
    can never set a cookie for another name)."""
    upstream = f"{names(meta['site'])['container']}:{APP_PORT}"
    return (
        f"# hosted server app {meta['site']} under its own name (generated by the app runner; do not edit)\n"
        f"@apphost_{meta['site']} host {host or meta['hostname']}\n"
        f"handle @apphost_{meta['site']} {{\n"
        f"\treverse_proxy {upstream} {{\n"
        '\t\theader_down Set-Cookie "(?i);\\s*domain=[^;]*" ""\n'
        "\t}\n"
        "}\n"
    )


TUNNEL_CONTAINER = "intraforge-tunnel"
TOKEN = re.compile(r"^[A-Za-z0-9+/=_-]{60,4000}$")


def tunnel_config(token: str, *, image: str, network: str, project: str) -> dict:
    """The Cloudflare Tunnel connector: only on the edge network (it needs the internet and reaches
    the proxy's internet listener there), never on IntraForge's internal network; locked down like an
    app."""
    if not TOKEN.match(token):
        raise RecipeError("bad tunnel token")
    return {
        "Image": image,
        "Cmd": ["tunnel", "--no-autoupdate", "run"],
        "Env": [f"TUNNEL_TOKEN={token}"],
        "Labels": {"intraforge.project": project, "intraforge.tunnel": "1"},
        "HostConfig": {
            "NetworkMode": network,
            "ReadonlyRootfs": True,
            "CapDrop": ["ALL"],
            "SecurityOpt": ["no-new-privileges:true"],
            "Memory": 128 * 1024 * 1024,
            "PidsLimit": 64,
            "RestartPolicy": {"Name": "unless-stopped"},
            "LogConfig": {"Type": "json-file", "Config": {"max-size": "5m", "max-file": "2"}},
            "Privileged": False,
            "PortBindings": {},
        },
    }
