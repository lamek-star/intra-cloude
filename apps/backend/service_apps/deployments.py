"""The service deployments that exist in this installation (settings.SERVICE_APP_DEPLOYMENTS).

A deployment slot is infrastructure: a running container with its own service token and its own
database login role. It is enabled only when its token is configured, so an installation without
the service simply has no slot to install into.
"""

import hashlib
import hmac
import re
from dataclasses import dataclass, field

from django.conf import settings

from .types import APP_TYPES, AppType

_KEY = re.compile(r"^[a-z][a-z0-9-]{0,62}$")
_ROLE = re.compile(r"^[a-z_][a-z0-9_]{0,62}$")
_PATH = re.compile(r"^/apps/[a-z0-9-]+/$")


@dataclass(frozen=True)
class Deployment:
    key: str
    app_type: AppType
    token_sha256: str
    db_role: str
    db_password: str
    internal_url: str
    launch_path: str
    # The token itself, used only when IntraForge calls this service on another application's behalf
    # (pay_bridge.py). Never logged, printed or returned: excluded from repr and comparisons.
    token: str = field(default="", repr=False, compare=False)

    def token_matches(self, presented: str) -> bool:
        digest = hashlib.sha256(presented.encode()).hexdigest()
        return hmac.compare_digest(digest, self.token_sha256)


def _load() -> dict[str, Deployment]:
    out = {}
    for key, spec in (getattr(settings, "SERVICE_APP_DEPLOYMENTS", None) or {}).items():
        token = spec.get("token") or ""
        if not token:
            continue
        if not _KEY.match(key) or spec["app_type"] not in APP_TYPES:
            raise ValueError(f"Invalid service deployment {key!r}.")
        if len(token) < 32:
            raise ValueError(f"The service token for {key!r} is too short (at least 32 characters).")
        if not _ROLE.match(spec["db_role"]) or not spec.get("db_password"):
            raise ValueError(f"Invalid database role settings for {key!r}.")
        if not _PATH.match(spec["launch_path"]):
            raise ValueError(f"Invalid launch path for {key!r}.")
        out[key] = Deployment(
            key=key,
            app_type=APP_TYPES[spec["app_type"]],
            token_sha256=hashlib.sha256(token.encode()).hexdigest(),
            db_role=spec["db_role"],
            db_password=spec["db_password"],
            internal_url=spec["internal_url"].rstrip("/"),
            launch_path=spec["launch_path"],
            token=token,
        )
    return out


def all_deployments() -> dict[str, Deployment]:
    return _load()


def get_deployment(key: str) -> Deployment | None:
    return _load().get(key)


def deployment_for_token(presented: str) -> Deployment | None:
    """The deployment whose service token was presented. Every configured token is compared
    (constant time), so timing does not reveal which slot exists."""
    found = None
    for deployment in _load().values():
        if deployment.token_matches(presented):
            found = deployment
    return found
