"""Browser sessions for service applications (ADR-0018 §3).

"Open" in IntraForge mints a random token, stores its SHA-256, and sets the raw token as an
HttpOnly cookie scoped to the application's path. On every request the service presents the token
to the internal introspection endpoint; this module decides whether it still stands for a signed-in
user who may open the application, and with which capabilities. Nothing the browser sends is
trusted beyond the token itself.
"""

import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import HASH_SESSION_KEY, SESSION_KEY
from django.contrib.sessions.backends.base import SessionBase
from django.db.models import Q
from django.utils import timezone
from django.utils.module_loading import import_string

from organizations.models import Membership
from permissions.models import ResourceGrant, RoleAssignment

from .models import ServiceApp, ServiceAppSession

COOKIE_PREFIX = "ifapp_"
# Absolute lifetime of one application session; it also ends with the IntraForge session.
_MAX_AGE = timedelta(hours=getattr(settings, "SERVICE_APP_SESSION_HOURS", 12))
# Writing last_used_at on every request would turn reads into writes; once a minute is plenty.
_TOUCH_EVERY = timedelta(seconds=60)


def cookie_name(app: ServiceApp) -> str:
    return COOKIE_PREFIX + app.deployment.replace("-", "_")


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def csrf_token_for(token_hash: str) -> str:
    """Per-session CSRF token the service requires on state-changing requests. Derived, not
    stored: it changes with every session and cannot be computed without SECRET_KEY."""
    return hmac.new(
        settings.SECRET_KEY.encode(), b"service-app-csrf:" + token_hash.encode(), hashlib.sha256
    ).hexdigest()


def mint(app: ServiceApp, user, django_session_key: str) -> str:
    token = secrets.token_urlsafe(32)
    ServiceAppSession.objects.create(
        token_hash=_hash(token),
        service_app=app,
        user=user,
        django_session_key=django_session_key,
        expires_at=timezone.now() + _MAX_AGE,
    )
    return token


def _django_session(key: str) -> SessionBase | None:
    engine = import_string(settings.SESSION_ENGINE + ".SessionStore")
    store = engine(session_key=key)
    if not store.exists(key):
        return None
    return store


def capabilities_for(user, app: ServiceApp) -> list[str]:
    """The application's capabilities this user holds: organization-wide through a role, or on
    this one instance through a non-expired resource grant (ADR-0008)."""
    wanted = set(app_type_capabilities(app))
    by_role = RoleAssignment.objects.filter(
        Q(organization_id=app.organization_id) | Q(organization__isnull=True), user=user
    ).values_list("role__permissions__code", flat=True)
    by_grant = ResourceGrant.objects.filter(
        Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now()),
        user=user,
        organization_id=app.organization_id,
        resource_type="service_app",
        resource_id=app.id,
    ).values_list("permission_id", flat=True)
    return sorted(wanted & ({c for c in by_role if c} | set(by_grant)))


def app_type_capabilities(app: ServiceApp) -> tuple[str, ...]:
    from .types import get_type

    return get_type(app.app_type).capabilities


@dataclass
class Introspection:
    user_id: str
    email: str
    display_name: str
    capabilities: list[str]
    csrf_token: str
    expires_at: str
    session_id: int


def introspect(app: ServiceApp, token: str) -> Introspection | None:
    """The live view of an application session, or None when it no longer grants anything."""
    if not token or len(token) > 200:
        return None
    try:
        session = ServiceAppSession.objects.select_related("user").get(
            token_hash=_hash(token), service_app=app
        )
    except ServiceAppSession.DoesNotExist:
        return None
    now = timezone.now()
    user = session.user
    if session.revoked_at or session.expires_at <= now or not app.enabled or not user.is_active:
        return None
    # Bound to the IntraForge login it came from: logout, session expiry, or a password change
    # (which changes the session auth hash) ends it, exactly as it ends the IntraForge session.
    store = _django_session(session.django_session_key)
    if store is None:
        return None
    if str(store.get(SESSION_KEY)) != str(user.pk):
        return None
    stored_hash = store.get(HASH_SESSION_KEY) or ""
    if not hmac.compare_digest(str(stored_hash), user.get_session_auth_hash()):
        return None
    if not Membership.objects.filter(
        organization_id=app.organization_id, user=user, status=Membership.Status.ACTIVE
    ).exists():
        return None
    capabilities = capabilities_for(user, app)
    from .types import get_type

    if get_type(app.app_type).open_capability not in capabilities:
        return None
    if session.last_used_at is None or now - session.last_used_at > _TOUCH_EVERY:
        ServiceAppSession.objects.filter(pk=session.pk).update(last_used_at=now)
    return Introspection(
        user_id=str(user.pk),
        email=user.email,
        display_name=display_name(user),
        capabilities=capabilities,
        csrf_token=csrf_token_for(session.token_hash),
        expires_at=session.expires_at.isoformat(),
        session_id=session.pk,
    )


def revoke(app: ServiceApp, token: str) -> bool:
    return bool(
        ServiceAppSession.objects.filter(
            token_hash=_hash(token), service_app=app, revoked_at__isnull=True
        ).update(revoked_at=timezone.now())
    )


def revoke_for_django_session(session_key: str) -> int:
    return ServiceAppSession.objects.filter(django_session_key=session_key, revoked_at__isnull=True).update(
        revoked_at=timezone.now()
    )


def display_name(user) -> str:
    full = " ".join(p for p in [getattr(user, "first_name", ""), getattr(user, "last_name", "")] if p)
    return full or getattr(user, "display_name", "") or user.email
