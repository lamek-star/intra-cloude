"""
Passkeys (WebAuthn), ADR-0019. Kept apart from the HTTP layer like accounts/services.py.

Each ceremony is two calls: `begin_*` makes the options (a fresh 32-byte challenge kept in the server-side
session for five minutes) and `finish_*` verifies the browser's answer against that challenge, once.
Verification itself is the `webauthn` library's; this module decides who may do what.
"""

from __future__ import annotations

import ipaddress
import time
from typing import Any

from django.db import transaction
from django.http.request import split_domain_port
from django.utils import timezone
from webauthn import (
    generate_authentication_options,
    generate_registration_options,
    verify_authentication_response,
    verify_registration_response,
)
from webauthn.helpers import base64url_to_bytes, bytes_to_base64url, options_to_json_dict
from webauthn.helpers.exceptions import InvalidAuthenticationResponse, InvalidRegistrationResponse
from webauthn.helpers.structs import (
    AuthenticatorSelectionCriteria,
    AuthenticatorTransport,
    PublicKeyCredentialDescriptor,
    PublicKeyCredentialHint,
    ResidentKeyRequirement,
    UserVerificationRequirement,
)

from audit import services as audit
from audit.models import AuditEvent

from . import services
from .models import Passkey, User

CHALLENGE_SESSION_KEY = "passkey_challenge"
VERIFIED_SESSION_KEY = "passkey_verified_at"
CHALLENGE_SECONDS = 300
# How long a passkey check counts for a sensitive change in the same session (switching passkey-only off).
RECENT_CHECK_SECONDS = 300
RP_NAME = "IntraForge"
# Where the browser should offer to find or make the passkey: the phone (QR code) first, as the owner asked.
HINTS = {
    "phone": [PublicKeyCredentialHint.HYBRID],
    "this_device": [PublicKeyCredentialHint.CLIENT_DEVICE],
    "security_key": [PublicKeyCredentialHint.SECURITY_KEY],
}
KNOWN_TRANSPORTS = {t.value for t in AuthenticatorTransport}


class PasskeyError(Exception):
    pass


def relying_party(request) -> tuple[str, str]:
    """(RP ID, expected origin) for this request: the host the browser used. `get_host()` is already checked
    against ALLOWED_HOSTS, and it is the same value Django's CSRF origin check trusts."""
    host = request.get_host()
    hostname, _port = split_domain_port(host)
    try:
        ipaddress.ip_address(hostname.strip("[]"))
        is_ip = True
    except ValueError:
        is_ip = False
    if not hostname or is_ip:
        raise PasskeyError(
            "Passkeys need IntraForge's name in the address, not a number: open it at https://localhost "
            "on this PC, or at the shop-network name, and try again."
        )
    return hostname, f"{request.scheme}://{host}"


def _hints(where: str | None) -> list[PublicKeyCredentialHint]:
    return HINTS.get(where or "phone", HINTS["phone"])


def _remember_challenge(request, purpose: str, challenge: bytes, rp_id: str, origin: str) -> None:
    request.session[CHALLENGE_SESSION_KEY] = {
        "purpose": purpose,
        "challenge": bytes_to_base64url(challenge),
        "rp_id": rp_id,
        "origin": origin,
        "at": time.time(),
    }


def _take_challenge(request, purpose: str) -> dict:
    """The pending challenge for this ceremony, removed so it can never be answered twice."""
    pending = request.session.pop(CHALLENGE_SESSION_KEY, None)
    if (
        not pending
        or pending.get("purpose") != purpose
        or time.time() - pending.get("at", 0) > CHALLENGE_SECONDS
    ):
        raise PasskeyError("The passkey request expired or was not started here. Try again.")
    rp_id, origin = relying_party(request)
    if pending["rp_id"] != rp_id or pending["origin"] != origin:
        raise PasskeyError("The passkey request was started at another address. Try again.")
    return pending


def _check_password_again(user: User, password: str, code: str | None) -> None:
    if not password or not user.check_password(password):
        raise PasskeyError("The password is not right.")
    if user.mfa_enabled and not services.verify_mfa_code(user=user, code=code or ""):
        raise PasskeyError("The authenticator code is not right.")


def _credential_id(credential: dict) -> bytes:
    raw = credential.get("rawId") or credential.get("id")
    if not isinstance(raw, str) or not raw:
        raise PasskeyError("That is not a passkey answer.")
    try:
        return base64url_to_bytes(raw)
    except (ValueError, TypeError) as exc:
        raise PasskeyError("That is not a passkey answer.") from exc


# ----------------------------------------------------------------------------------------- adding a passkey
def begin_registration(request, *, user: User, password: str, code: str | None, where: str | None) -> dict:
    _check_password_again(user, password, code)
    rp_id, origin = relying_party(request)
    existing = [
        PublicKeyCredentialDescriptor(id=bytes(p.credential_id)) for p in user.passkeys.filter(rp_id=rp_id)
    ]
    options = generate_registration_options(
        rp_id=rp_id,
        rp_name=RP_NAME,
        user_id=user.id.bytes,
        user_name=user.email,
        user_display_name=user.get_full_name(),
        exclude_credentials=existing,
        authenticator_selection=AuthenticatorSelectionCriteria(
            resident_key=ResidentKeyRequirement.REQUIRED,
            user_verification=UserVerificationRequirement.REQUIRED,
        ),
        hints=_hints(where),
    )
    _remember_challenge(request, "register", options.challenge, rp_id, origin)
    return options_to_json_dict(options)


def finish_registration(request, *, user: User, credential: dict, name: str) -> Passkey:
    pending = _take_challenge(request, "register")
    try:
        verified = verify_registration_response(
            credential=credential,
            expected_challenge=base64url_to_bytes(pending["challenge"]),
            expected_rp_id=pending["rp_id"],
            expected_origin=pending["origin"],
            require_user_verification=True,
        )
    except (InvalidRegistrationResponse, ValueError, KeyError, TypeError) as exc:
        audit.record(
            actor=user,
            organization_id=None,
            action="passkey.add",
            result=AuditEvent.Result.DENIED,
            context={"reason": str(exc)[:200]},
        )
        raise PasskeyError("The passkey could not be checked. Try again.") from exc
    if Passkey.objects.filter(credential_id=verified.credential_id).exists():
        raise PasskeyError("This passkey is already added.")
    transports = credential.get("response", {}).get("transports") or []
    passkey = Passkey.objects.create(
        user=user,
        name=(name or "").strip()[:80] or "Passkey",
        rp_id=pending["rp_id"],
        credential_id=verified.credential_id,
        public_key=verified.credential_public_key,
        sign_count=verified.sign_count,
        transports=[t for t in transports if isinstance(t, str) and t in KNOWN_TRANSPORTS],
        backed_up=bool(verified.credential_backed_up),
    )
    audit.record(
        actor=user,
        organization_id=None,
        action="passkey.add",
        resource_type="passkey",
        resource_id=passkey.id,
        context={"name": passkey.name, "rp_id": passkey.rp_id},
    )
    return passkey


# ------------------------------------------------------------------------------- signing in / checking again
def begin_check(request, *, user: User | None, where: str | None) -> dict:
    """Sign-in (user None: any passkey made at this address, the browser lists them; no account is revealed)
    or a fresh check by the signed-in user (only their own passkeys)."""
    rp_id, origin = relying_party(request)
    allow = []
    if user is not None:
        allow = [
            PublicKeyCredentialDescriptor(id=bytes(p.credential_id))
            for p in user.passkeys.filter(rp_id=rp_id)
        ]
        if not allow:
            raise PasskeyError("You have no passkey for this address yet.")
    options = generate_authentication_options(
        rp_id=rp_id,
        allow_credentials=allow,
        user_verification=UserVerificationRequirement.REQUIRED,
    )
    data = options_to_json_dict(options)
    # Not a parameter of generate_authentication_options in this library version; a WebAuthn option.
    data["hints"] = [h.value for h in _hints(where)]
    _remember_challenge(request, "check" if user else "login", options.challenge, rp_id, origin)
    return data


def finish_check(request, *, credential: dict, user: User | None) -> User:
    """Verifies the answer and returns the passkey's owner. With `user`, the passkey must be theirs."""
    pending = _take_challenge(request, "check" if user else "login")
    try:
        passkey = Passkey.objects.select_related("user").get(
            credential_id=_credential_id(credential), rp_id=pending["rp_id"]
        )
    except Passkey.DoesNotExist:
        audit.record(
            actor=user,
            organization_id=None,
            action="auth.passkey",
            result=AuditEvent.Result.DENIED,
            context={"reason": "unknown passkey", "rp_id": pending["rp_id"]},
        )
        raise PasskeyError("This passkey is not known here.") from None
    owner = passkey.user
    if (user is not None and owner.id != user.id) or not owner.is_active:
        audit.record(
            actor=user,
            organization_id=None,
            action="auth.passkey",
            result=AuditEvent.Result.DENIED,
            context={"reason": "not this account" if owner.is_active else "inactive account"},
        )
        raise PasskeyError("This passkey is not known here.")
    handle = credential.get("response", {}).get("userHandle")
    if handle:
        try:
            if base64url_to_bytes(handle) != owner.id.bytes:
                raise PasskeyError("This passkey is not known here.")
        except (ValueError, TypeError) as exc:
            raise PasskeyError("That is not a passkey answer.") from exc
    try:
        verified = verify_authentication_response(
            credential=credential,
            expected_challenge=base64url_to_bytes(pending["challenge"]),
            expected_rp_id=pending["rp_id"],
            expected_origin=pending["origin"],
            credential_public_key=bytes(passkey.public_key),
            credential_current_sign_count=passkey.sign_count,
            require_user_verification=True,
        )
    except (InvalidAuthenticationResponse, ValueError, KeyError, TypeError) as exc:
        audit.record(
            actor=owner,
            organization_id=None,
            action="auth.passkey",
            result=AuditEvent.Result.DENIED,
            resource_type="passkey",
            resource_id=passkey.id,
            context={"reason": str(exc)[:200]},
        )
        raise PasskeyError("The passkey could not be checked. Try again.") from exc
    passkey.sign_count = verified.new_sign_count
    passkey.backed_up = bool(verified.credential_backed_up)
    passkey.last_used_at = timezone.now()
    passkey.save(update_fields=["sign_count", "backed_up", "last_used_at"])
    return owner


def mark_checked(request) -> None:
    request.session[VERIFIED_SESSION_KEY] = time.time()


def recently_checked(request) -> bool:
    at = request.session.get(VERIFIED_SESSION_KEY)
    return isinstance(at, (int, float)) and time.time() - at <= RECENT_CHECK_SECONDS


# --------------------------------------------------------------------------------- managing one's passkeys
def remove_passkey(*, user: User, passkey_id, password: str, code: str | None) -> None:
    _check_password_again(user, password, code)
    with transaction.atomic():
        locked = User.objects.select_for_update().get(pk=user.pk)
        try:
            passkey = locked.passkeys.get(id=passkey_id)
        except (Passkey.DoesNotExist, ValueError):
            raise PasskeyError("No such passkey.") from None
        if locked.passkey_only and locked.passkeys.count() == 1:
            raise PasskeyError(
                "This is your last passkey and your account signs in with passkeys only. "
                "Allow password sign-in first, or add another passkey."
            )
        passkey.delete()
    audit.record(
        actor=user,
        organization_id=None,
        action="passkey.remove",
        resource_type="passkey",
        resource_id=passkey_id,
        context={"name": passkey.name, "rp_id": passkey.rp_id},
    )


def set_passkey_only(request, *, user: User, on: bool, password: str | None, code: str | None) -> None:
    if on:
        _check_password_again(user, password or "", code)
        if not user.passkeys.exists():
            raise PasskeyError("Add a passkey first.")
    elif not recently_checked(request):
        raise PasskeyError("Confirm with your passkey first.")
    user.passkey_only = on
    user.save(update_fields=["passkey_only"])
    audit.record(
        actor=user,
        organization_id=None,
        action="passkey.only_on" if on else "passkey.only_off",
        resource_type="user",
        resource_id=user.id,
    )


def describe(passkey: Passkey) -> dict[str, Any]:
    return {
        "id": str(passkey.id),
        "name": passkey.name,
        "rp_id": passkey.rp_id,
        "backed_up": passkey.backed_up,
        "transports": passkey.transports,
        "created_at": passkey.created_at,
        "last_used_at": passkey.last_used_at,
    }
