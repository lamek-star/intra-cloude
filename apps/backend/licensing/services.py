"""The licence (ADR-0023): a 30-day trial, then a serial number and an activation code for this PC.

Without a valid licence after the trial IntraForge is **read-only**: people still sign in, see and export
their data, and backups keep running, but nothing can be added or changed (middleware.py) until the licence is
activated. The PC code comes from the kit's start script (a file in LICENSE_MACHINE_DIR); the activation code
is checked with the vendor's public key (codes.py). Licensing is enforced only where LICENSE_ENFORCED is on
(the shop kit).
"""

import datetime
import logging
from pathlib import Path

from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from audit import services as audit

from . import codes
from .models import LicenseState

log = logging.getLogger(__name__)
CACHE_KEY = "licensing:read-only"
CACHE_SECONDS = 60
CLOCK_SLACK = datetime.timedelta(days=1)


def _machine_file(name: str) -> str:
    try:
        return (Path(settings.LICENSE_MACHINE_DIR) / name).read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def current_pc() -> str | None:
    return codes.normalize_pc(_machine_file("pc-code"))


def _first_start() -> datetime.datetime | None:
    text = _machine_file("first-start")
    try:
        day = datetime.date.fromisoformat(text[:10])
    except ValueError:
        return None
    return datetime.datetime.combine(day, datetime.time.min, tzinfo=datetime.UTC)


def _state() -> LicenseState:
    now = timezone.now()
    first = _first_start()
    with transaction.atomic():
        state = LicenseState.objects.select_for_update().filter(pk=1).first()
        if state is None:
            start = min(now, first) if first else now
            state = LicenseState.objects.create(pk=1, trial_started_at=start, last_seen_at=now)
        else:
            changed = []
            if first and first < state.trial_started_at:
                state.trial_started_at = first  # a reinstall does not start a new trial
                changed.append("trial_started_at")
            if now > state.last_seen_at:
                state.last_seen_at = now
                changed.append("last_seen_at")
            if changed:
                state.save(update_fields=changed)
    return state


def _activation(state: LicenseState, pc: str | None) -> dict | None:
    if not state.activation_code or not pc:
        return None
    data = codes.verify_activation(
        codes.public_key_from_text(settings.LICENSE_PUBLIC_KEY), state.activation_code
    )
    if data is None or data["pc"] != pc or data["sn"] != state.serial:
        return None
    return data


def status() -> dict:
    state = _state()
    pc = current_pc()
    now = timezone.now()
    trial_ends = state.trial_started_at + datetime.timedelta(days=settings.LICENSE_TRIAL_DAYS)
    clock_back = now < state.last_seen_at - CLOCK_SLACK
    active = _activation(state, pc)
    if active:
        name = "active"
    elif not settings.LICENSE_ENFORCED:
        name = "not_enforced"
    elif now < trial_ends and not clock_back:
        name = "trial"
    else:
        name = "expired"
    left = max(0, (trial_ends - now).days + (1 if (trial_ends - now).seconds else 0))
    return {
        "state": name,
        "enforced": settings.LICENSE_ENFORCED,
        "trial_days": settings.LICENSE_TRIAL_DAYS,
        "trial_ends": trial_ends.isoformat(),
        "days_left": left if name == "trial" else 0,
        "clock_back": clock_back,
        "pc_code": pc,
        "serial": _masked(state.serial) if active else None,
        "kind": active["kind"] if active else None,
        "activated_at": state.activated_at.isoformat() if active and state.activated_at else None,
    }


def _masked(serial: str) -> str:
    return serial[:8] + "-****-****-" + serial[-4:] if serial else ""


def read_only() -> bool:
    """Whether changes are refused now (enforced, and neither a trial day left nor a valid licence)."""
    if not settings.LICENSE_ENFORCED:
        return False
    cached = cache.get(CACHE_KEY)
    if cached is None:
        cached = status()["state"] == "expired"
        cache.set(CACHE_KEY, cached, CACHE_SECONDS)
    return bool(cached)


def activate(*, actor, serial, activation_code) -> dict:
    sn = codes.normalize_serial(serial)
    if not sn:
        raise ValidationError({"serial": "That serial number is not valid. Check it for a typo."})
    pc = current_pc()
    if not pc:
        raise ValidationError(
            {"detail": "This PC's code is not available yet. Restart IntraForge from the Control Center."}
        )
    data = codes.verify_activation(codes.public_key_from_text(settings.LICENSE_PUBLIC_KEY), activation_code)
    if data is None:
        raise ValidationError(
            {"activation_code": "That activation code is not valid. Copy it again, all of it."}
        )
    if data["sn"] != sn:
        raise ValidationError({"activation_code": "That activation code is for another serial number."})
    if data["pc"] != pc:
        raise ValidationError(
            {"activation_code": f"That activation code is for another PC. This PC's code is {pc}."}
        )
    state = _state()
    state.serial = sn
    state.activation_code = activation_code.strip()
    state.activated_at = timezone.now()
    state.activated_by = actor
    state.save(update_fields=["serial", "activation_code", "activated_at", "activated_by"])
    cache.delete(CACHE_KEY)
    audit.record(
        actor=actor,
        organization_id=None,
        action="licence.activate",
        resource_type="licence",
        resource_id="1",
        context={"serial": _masked(sn), "pc": pc, "kind": data["kind"]},
    )
    return status()
