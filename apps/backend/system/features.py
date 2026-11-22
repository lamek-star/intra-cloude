"""Feature groups: which parts of IntraForge this installation shows and serves.

Chosen in Setup (INTRAFORGE_FEATURES in the keys file seeds the first value) and changed later by the Super
Administrator (the Features page). A group that is off is hidden in the web app AND refused by the server: its URL
modules answer 403 ``feature_disabled``, its application types cannot be installed, opened or listed, and application
credentials stop working when Developer is off. Switching a group off never deletes anything; switching it back on
brings everything back as it was.

The groups (decided with the shop owner):
  business_apps       Spare Parts, Pharmacy and the business apps built on the App Platform.
  pay_media           IntraForge Pay and the Movie Shop (with its customer portal).
  websites_developer  Hosted websites, the internet gate, and the Developer section (applications, keys,
                      environments, webhooks, OAuth sign-in for other software).
  files_data          Storage, databases and the data tools (import, analytics, dashboards, sharing).
"""

from __future__ import annotations

import functools
import logging
import os
from importlib import import_module

from django.db import transaction
from django.http import JsonResponse
from django.urls import URLPattern, URLResolver

logger = logging.getLogger(__name__)

BUSINESS_APPS = "business_apps"
PAY_MEDIA = "pay_media"
WEBSITES_DEVELOPER = "websites_developer"
FILES_DATA = "files_data"

GROUPS: dict[str, str] = {
    BUSINESS_APPS: "Business apps",
    PAY_MEDIA: "Pay and Movie Shop",
    WEBSITES_DEVELOPER: "Websites and Developer",
    FILES_DATA: "Files, databases, reports",
}

# Which group each installable application type belongs to (service_apps.types keys).
APP_TYPE_GROUP: dict[str, str] = {
    "spare_parts": BUSINESS_APPS,
    "pharmacy": BUSINESS_APPS,
    "intraforge_pay": PAY_MEDIA,
}

ENV_VAR = "INTRAFORGE_FEATURES"
DISABLED_MESSAGE = "This part of IntraForge is switched off on this installation."


class FeatureDisabled(Exception):
    """Raised by service code; the API turns it into 403 feature_disabled (system.exceptions)."""

    def __init__(self, group: str):
        super().__init__(DISABLED_MESSAGE)
        self.group = group


def parse(value: str | None) -> list[str]:
    """INTRAFORGE_FEATURES: comma-separated group keys. Unset means every group (installations from before this
    setting existed keep everything); an empty value means none. Unknown names are ignored, with a warning."""
    if value is None:
        return list(GROUPS)
    chosen: list[str] = []
    for raw in value.split(","):
        key = raw.strip()
        if not key:
            continue
        if key not in GROUPS:
            logger.warning("Ignoring unknown feature group %r in %s", key, ENV_VAR)
            continue
        if key not in chosen:
            chosen.append(key)
    return chosen


def _settings_row():
    from .models import FeatureSettings

    row = FeatureSettings.objects.filter(pk=1).first()
    if row is None:
        # First use: the value Setup wrote to the keys file. get_or_create keeps two workers from both inserting.
        row, _ = FeatureSettings.objects.get_or_create(pk=1, defaults={"enabled": parse(os.environ.get(ENV_VAR))})
    return row


def enabled_groups() -> frozenset[str]:
    return frozenset(g for g in _settings_row().enabled if g in GROUPS)


def is_enabled(group: str) -> bool:
    return group in enabled_groups()


def app_type_enabled(app_type: str) -> bool:
    group = APP_TYPE_GROUP.get(app_type)
    return group is None or is_enabled(group)


def require(group: str) -> None:
    if not is_enabled(group):
        raise FeatureDisabled(group)


def require_app_type(app_type: str) -> None:
    group = APP_TYPE_GROUP.get(app_type)
    if group is not None:
        require(group)


# Who may create an account (ADR-0026).
REGISTRATION_CLOSED = "closed"
REGISTRATION_REQUESTS = "requests"
REGISTRATION_OPEN = "open"
REGISTRATION_CHOICES = {
    REGISTRATION_CLOSED: "Only administrators add people",
    REGISTRATION_REQUESTS: "People ask from an app's Request access page; an administrator approves",
    REGISTRATION_OPEN: "Anyone can create an account",
}


def registration_policy() -> str:
    value = _settings_row().registration
    return value if value in REGISTRATION_CHOICES else REGISTRATION_REQUESTS


def first_run() -> bool:
    """No organization yet: the installation's first account must be creatable, whatever the policy."""
    from organizations.models import Organization

    # Organizations made by IntraForge's own service identities (the built-in catalogue's, created by a migration on
    # every installation) do not count: only one a person made ends the first run.
    return not Organization.objects.exclude(created_by__email__iendswith="@service.internal").exists()


def may_register_freely() -> bool:
    return registration_policy() == REGISTRATION_OPEN or first_run()


def may_request_access() -> bool:
    return registration_policy() in (REGISTRATION_REQUESTS, REGISTRATION_OPEN)


def set_registration(actor, value: str) -> dict:
    """Super Administrator only (checked by the view)."""
    from audit import services as audit

    from .models import FeatureSettings

    if value not in REGISTRATION_CHOICES:
        raise ValueError("Choose closed, requests or open.")
    with transaction.atomic():
        _settings_row()
        row = FeatureSettings.objects.select_for_update().get(pk=1)
        before = row.registration
        row.registration = value
        row.updated_by = actor
        row.save(update_fields=["registration", "updated_by", "updated_at"])
        audit.record(
            actor=actor,
            organization_id=None,
            action="system.registration.update",
            resource_type="system",
            resource_id="registration",
            context={"before": before, "after": value},
        )
    return describe()


def describe() -> dict:
    row = _settings_row()
    on = set(row.enabled)
    return {
        "registration": registration_policy(),
        "registration_choices": [{"key": k, "label": v} for k, v in REGISTRATION_CHOICES.items()],
        "groups": [{"key": k, "label": label, "enabled": k in on} for k, label in GROUPS.items()],
        "app_types": {t: (g in on) for t, g in APP_TYPE_GROUP.items()},
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def set_enabled(actor, enabled: list[str]) -> dict:
    """Super Administrator only (checked by the view). Refuses to hide the internet gate while it is on: the
    tunnel would keep the shop reachable from the internet with nobody able to see or switch it off."""
    from audit import services as audit

    from .models import FeatureSettings

    unknown = [g for g in enabled if g not in GROUPS]
    if unknown:
        raise ValueError(f"Unknown feature group: {', '.join(unknown)}.")
    chosen = [g for g in GROUPS if g in enabled]
    if WEBSITES_DEVELOPER not in chosen:
        from sites.models import InternetGateway

        if InternetGateway.current().enabled:
            raise ValueError(
                "Internet access is on. Switch it off first (Internet access page), then hide Websites and Developer."
            )
    with transaction.atomic():
        _settings_row()
        row = FeatureSettings.objects.select_for_update().get(pk=1)
        before = [g for g in GROUPS if g in row.enabled]
        row.enabled = chosen
        row.updated_by = actor
        row.save(update_fields=["enabled", "updated_by", "updated_at"])
        audit.record(
            actor=actor,
            organization_id=None,
            action="system.features.update",
            resource_type="system",
            resource_id="features",
            context={"before": before, "after": chosen},
        )
    return describe()


def refusal(request=None, group: str = "") -> JsonResponse:
    """The API's error shape (system.exceptions) for a switched-off group."""
    return JsonResponse(
        {
            "error": {
                "code": "feature_disabled",
                "message": DISABLED_MESSAGE,
                "group": group,
                "request_id": getattr(request, "request_id", None),
            }
        },
        status=403,
    )


def gate_view(group: str, view):
    @functools.wraps(view)
    def gated_view(request, *args, **kwargs):
        if not is_enabled(group):
            return refusal(request, group)
        return view(request, *args, **kwargs)

    return gated_view


def _gate(group: str, entry):
    if isinstance(entry, URLResolver):
        return URLResolver(
            entry.pattern,
            [_gate(group, e) for e in entry.url_patterns],
            entry.default_kwargs,
            entry.app_name,
            entry.namespace,
        )
    if isinstance(entry, URLPattern):
        return URLPattern(entry.pattern, gate_view(group, entry.callback), entry.default_args, entry.name)
    raise TypeError(f"Cannot gate {entry!r}")


def gated(group: str, urlconf: str) -> list:
    """Every route of `urlconf` (a module path like "storage.urls"), answering 403 feature_disabled while `group` is
    off. Wrapping at the URL level means a view added to that module later is covered without remembering to."""
    if group not in GROUPS:
        raise ValueError(group)
    return [_gate(group, e) for e in import_module(urlconf).urlpatterns]
