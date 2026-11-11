"""
The internet gate (ADR-0020 decision 4). Off by default. Only the Super Administrator (the platform-wide
``sites.internet.manage`` capability) can switch it on -- with their password, and only with two-factor
sign-in on their account -- and publish or revoke a site under a public name. The Cloudflare Tunnel
connector runs only while the gate is on and reaches only the proxy's internet listener, which serves
published sites and nothing else: never IntraForge itself. Every change is audited; switching the gate off
revokes every publication.

Auto-publish (optional, also Super Administrator only, with their password): once a domain is set, every
online site is published as <slug>.<domain> -- now, and whenever a site is created or comes back online --
because a wildcard route in Cloudflare (*.<domain>) already sends those names to the tunnel. Taking a site
offline takes its automatic name back; switching auto-publish off takes back every automatic name and keeps
those published by hand.
"""

from __future__ import annotations

import re

from django.db import IntegrityError, transaction
from django.utils import timezone

from audit import services as audit
from environments import crypto
from permissions.services import has_permission

from . import runner
from .models import InternetGateway, Site
from .services import SiteError, validate_hostname

CAPABILITY = "sites.internet.manage"
# A Cloudflare Tunnel token: a long base64/base64url string.
_TOKEN = re.compile(r"^[A-Za-z0-9+/=_-]{60,4000}$")
# A public name has a real top-level domain (letters), e.g. www.myshop.com -- not a name that only
# exists inside a network (myshop.lan) or a reserved one (RFC 2606, RFC 6761, RFC 8375).
_PUBLIC = re.compile(r"\.[a-z]{2,63}$")
_PRIVATE_SUFFIXES = (
    ".lan",
    ".local",
    ".home",
    ".internal",
    ".intranet",
    ".corp",
    ".private",
    ".localhost",
    ".test",
    ".example",
    ".invalid",
    ".home.arpa",
    ".localdomain",
)


class InternetError(SiteError):
    pass


def can_manage(user) -> bool:
    """Platform-wide only: an organization role can never hold the internet gate."""
    return has_permission(user, CAPABILITY, organization_id=None)


def _require(user) -> None:
    if not can_manage(user):
        raise PermissionError("Only the Super Administrator can change internet access.")


def status() -> dict:
    gate = InternetGateway.current()
    published = Site.objects.filter(internet_hostname__isnull=False).select_related("organization")
    tunnel: dict = {"state": "off"}
    if gate.enabled and runner.configured():
        try:
            tunnel = runner.tunnel_status()
        except (runner.RunnerUnavailable, runner.RunnerRefused) as exc:
            tunnel = {"state": "unknown", "log": str(exc)[:300]}
    return {
        "enabled": gate.enabled,
        "changed_at": gate.changed_at,
        "auto_domain": gate.auto_domain,
        "tunnel": tunnel,
        "published": [
            {
                "site": str(s.id),
                "name": s.name,
                "organization": s.organization.name,
                "internet_hostname": s.internet_hostname,
                "published_at": s.internet_published_at,
                "auto": s.internet_auto,
            }
            for s in published
        ],
        # What can be published now: online sites without a public name, from every organization. The Super
        # Administrator publishes platform-wide and is usually not a member of the shop's organization.
        "publishable": [
            {"site": str(s.id), "name": s.name, "organization": s.organization.name}
            for s in Site.objects.filter(status=Site.Status.ACTIVE, internet_hostname__isnull=True)
            .select_related("organization")
            .order_by("organization__name", "name")
        ],
    }


def enable(*, actor, token: str, password: str) -> dict:
    _require(actor)
    if not getattr(actor, "mfa_enabled", False):
        raise InternetError("Turn on two-factor sign-in for your account first; internet access requires it.")
    if not password or not actor.check_password(password):
        raise InternetError("The password is not correct.")
    token = (token or "").strip()
    if not _TOKEN.match(token):
        raise InternetError(
            "Paste the tunnel token from Cloudflare (Zero Trust > Networks > Tunnels > your tunnel)."
        )
    try:
        result = runner.tunnel_start(token)
    except (runner.RunnerUnavailable, runner.RunnerRefused) as exc:
        raise InternetError(f"The tunnel could not be started: {exc}") from exc
    gate = InternetGateway.current()
    gate.enabled = True
    gate.token_encrypted = crypto.encrypt_secret(token)
    gate.changed_by, gate.changed_at = actor, timezone.now()
    gate.save()
    audit.record(
        actor=actor,
        organization_id=None,
        action="internet.gateway.enabled",
        resource_type="internet_gateway",
        context={"tunnel": result.get("state")},
    )
    return status()


def disable(*, actor) -> dict:
    """Switches the gate off: the tunnel stops and every site loses its public name."""
    _require(actor)
    if runner.configured():
        try:
            runner.tunnel_stop()
        except (runner.RunnerUnavailable, runner.RunnerRefused) as exc:
            raise InternetError(f"The tunnel could not be stopped: {exc}") from exc
    with transaction.atomic():
        gate = InternetGateway.current()
        gate.enabled, gate.token_encrypted, gate.auto_domain = False, None, ""
        gate.changed_by, gate.changed_at = actor, timezone.now()
        gate.save()
        revoked = list(Site.objects.filter(internet_hostname__isnull=False))
        for site in revoked:
            _clear(site)
    for site in revoked:
        _follow_route(site)
    audit.record(
        actor=actor,
        organization_id=None,
        action="internet.gateway.disabled",
        resource_type="internet_gateway",
        context={"revoked_sites": [str(s.id) for s in revoked]},
    )
    return status()


def validate_public_name(name: str) -> str:
    hostname = validate_hostname(name)
    if not hostname or not _PUBLIC.search(hostname) or hostname.endswith(_PRIVATE_SUFFIXES):
        raise InternetError("Enter the public name set up in Cloudflare, e.g. www.myshop.com.")
    return hostname


def publish(*, actor, site: Site, hostname: str) -> Site:
    _require(actor)
    if not InternetGateway.current().enabled:
        raise InternetError("Internet access is switched off. The Super Administrator switches it on first.")
    if site.status != Site.Status.ACTIVE:
        raise InternetError("Bring the site online first.")
    name = validate_public_name(hostname)
    if Site.objects.filter(internet_hostname=name).exclude(pk=site.pk).exists():
        raise InternetError(f"'{name}' is already published for another site.")
    site.internet_hostname, site.internet_published_by, site.internet_published_at = (
        name,
        actor,
        timezone.now(),
    )
    site.internet_auto = False
    try:
        site.save(
            update_fields=[
                "internet_hostname",
                "internet_published_by",
                "internet_published_at",
                "internet_auto",
                "updated_at",
            ]
        )
    except IntegrityError as exc:
        raise InternetError(f"'{name}' is already published for another site.") from exc
    _follow_route(site)
    audit.record(
        actor=actor,
        organization_id=site.organization_id,
        action="site.internet.published",
        resource_type="site",
        resource_id=site.id,
        context={"slug": site.slug, "internet_hostname": name},
    )
    return site


def revoke(*, actor, site: Site) -> Site:
    _require(actor)
    previous = site.internet_hostname
    if not previous:
        return site
    _clear(site)
    _follow_route(site)
    audit.record(
        actor=actor,
        organization_id=site.organization_id,
        action="site.internet.revoked",
        resource_type="site",
        resource_id=site.id,
        context={"slug": site.slug, "internet_hostname": previous},
    )
    return site


def _clear(site: Site) -> None:
    site.internet_hostname, site.internet_published_by, site.internet_published_at = None, None, None
    site.internet_auto = False
    site.save(
        update_fields=[
            "internet_hostname",
            "internet_published_by",
            "internet_published_at",
            "internet_auto",
            "updated_at",
        ]
    )


def set_auto_publish(*, actor, domain: str, password: str) -> dict:
    """Switches auto-publish on for a domain (publishing every online site now) or, with an empty domain, off
    (taking back every automatic name; names published by hand stay)."""
    _require(actor)
    if not password or not actor.check_password(password):
        raise InternetError("The password is not correct.")
    domain = (domain or "").strip().lower().rstrip(".")
    gate = InternetGateway.current()
    if domain:
        if not gate.enabled:
            raise InternetError("Switch internet access on first.")
        validate_public_name(domain)
        gate.auto_domain = domain
        gate.save(update_fields=["auto_domain"])
        published = [
            s.internet_hostname for s in Site.objects.filter(status=Site.Status.ACTIVE) if auto_publish(s)
        ]
        audit.record(
            actor=actor,
            organization_id=None,
            action="internet.auto_publish.enabled",
            resource_type="internet_gateway",
            context={"domain": domain, "published": published},
        )
    else:
        previous = gate.auto_domain
        gate.auto_domain = ""
        gate.save(update_fields=["auto_domain"])
        taken_back = []
        for site in Site.objects.filter(internet_auto=True):
            taken_back.append(site.internet_hostname)
            withdraw_auto(site)
        audit.record(
            actor=actor,
            organization_id=None,
            action="internet.auto_publish.disabled",
            resource_type="internet_gateway",
            context={"domain": previous, "revoked": taken_back},
        )
    return status()


def auto_publish(site: Site) -> bool:
    """Publishes an online site as <slug>.<domain> when auto-publish is on and it has no public name yet.
    Never raises: a site that cannot be published (its name already taken by hand, its app route not updated)
    stays unpublished or published without its route, and the audit log says why. Returns whether it was
    published."""
    gate = InternetGateway.current()
    if not (gate.enabled and gate.auto_domain) or site.status != Site.Status.ACTIVE or site.internet_hostname:
        return False
    name = f"{site.slug}.{gate.auto_domain}"
    if Site.objects.filter(internet_hostname=name).exclude(pk=site.pk).exists():
        _auto_failed(site, name, "the name is already published for another site")
        return False
    site.internet_hostname, site.internet_published_by, site.internet_published_at = (
        name,
        None,
        timezone.now(),
    )
    site.internet_auto = True
    try:
        with transaction.atomic():
            site.save(
                update_fields=[
                    "internet_hostname",
                    "internet_published_by",
                    "internet_published_at",
                    "internet_auto",
                    "updated_at",
                ]
            )
    except IntegrityError:
        site.refresh_from_db()
        _auto_failed(site, name, "the name is already published for another site")
        return False
    try:
        _follow_route(site)
    except InternetError as exc:
        _auto_failed(site, name, str(exc))
    audit.record(
        actor=None,
        organization_id=site.organization_id,
        action="site.internet.published",
        resource_type="site",
        resource_id=site.id,
        context={"slug": site.slug, "internet_hostname": name, "auto": True},
    )
    return True


def withdraw_auto(site: Site) -> None:
    """Takes back an automatic public name (a name published by hand is left alone). Never raises."""
    if not site.internet_auto or not site.internet_hostname:
        return
    previous = site.internet_hostname
    _clear(site)
    try:
        _follow_route(site)
    except InternetError as exc:
        _auto_failed(site, previous, str(exc))
    audit.record(
        actor=None,
        organization_id=site.organization_id,
        action="site.internet.revoked",
        resource_type="site",
        resource_id=site.id,
        context={"slug": site.slug, "internet_hostname": previous, "auto": True},
    )


def _auto_failed(site: Site, name: str, reason: str) -> None:
    audit.record(
        actor=None,
        organization_id=site.organization_id,
        action="site.internet.auto_failed",
        resource_type="site",
        resource_id=site.id,
        result="error",
        context={"slug": site.slug, "internet_hostname": name, "reason": reason[:300]},
    )


def _follow_route(site: Site) -> None:
    """A Node.js app's internet route follows its publication (a website is served by the backend view)."""
    if site.kind == Site.Kind.NODE and runner.configured():
        try:
            runner.route(site)
        except (runner.RunnerUnavailable, runner.RunnerRefused) as exc:
            raise InternetError(f"Saved, but the app's route could not be updated: {exc}") from exc


def published_site(host: str) -> Site | None:
    """The site published under this public name, only while the gate is on."""
    if not host or not InternetGateway.current().enabled:
        return None
    return (
        Site.objects.select_related("active_version")
        .filter(internet_hostname=host, status=Site.Status.ACTIVE)
        .first()
    )
