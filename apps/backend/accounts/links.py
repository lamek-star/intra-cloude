"""
Single-use confirmation links (ADR-0026, step 3).

Approving an access request from a new account issues a link: 32 random bytes, of which only the SHA-256 is stored,
valid for 72 hours. Opening it confirms the email and activates the account. An account made by the system (no
password yet, e.g. the owner's phone approver) sets its own sign-in on the link page: a password, or a passkey kept
on the phone. A temporary password is never shown. Issuing a new link ends the previous one; every step is audited.
"""

from __future__ import annotations

import hashlib
import secrets
import time
from datetime import timedelta

from django.contrib.auth import password_validation
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from audit import services as audit
from audit.models import AuditEvent

from . import passkeys
from .models import AccountLink, User

TOKEN_BYTES = 32
LINK_HOURS = 72
SESSION_KEY = "account_link"
SESSION_SECONDS = 600
INVALID = (
    "This link does not work any more: it was already used, replaced by a newer one, or it expired. "
    "Ask the shop's administrator for a new link."
)


class LinkError(Exception):
    pass


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode("ascii", "ignore")).hexdigest()


def issue(*, user: User, created_by: User | None, organization_id=None) -> str:
    """A new link for `user` (any earlier open one ends). Returns the token: shown once, never stored."""
    token = secrets.token_urlsafe(TOKEN_BYTES)
    now = timezone.now()
    with transaction.atomic():
        AccountLink.objects.filter(user=user, used_at__isnull=True, revoked_at__isnull=True).update(revoked_at=now)
        link = AccountLink.objects.create(
            user=user,
            token_hash=_hash(token),
            created_by=created_by,
            expires_at=now + timedelta(hours=LINK_HOURS),
        )
        audit.record(
            actor=created_by,
            organization_id=organization_id,
            action="account.link.create",
            resource_type="user",
            resource_id=user.id,
            context={"link": str(link.id), "expires_at": link.expires_at.isoformat()},
        )
    return token


def url(base: str, token: str) -> str:
    # The token goes in the fragment: browsers never send it to a server, so it is in no log and no Referer.
    return f"{base.rstrip('/')}/confirm#t={token}"


def _find(token: str) -> AccountLink:
    if not isinstance(token, str) or not token or len(token) > 100:
        raise LinkError(INVALID)
    link = AccountLink.objects.select_related("user").filter(token_hash=_hash(token)).first()
    if link is None or link.used_at or link.revoked_at:
        raise LinkError(INVALID)
    if link.expires_at <= timezone.now():
        audit.record(
            actor=None,
            organization_id=None,
            action="account.link.expired",
            resource_type="user",
            resource_id=link.user_id,
            result=AuditEvent.Result.DENIED,
            context={"link": str(link.id)},
        )
        raise LinkError(INVALID)
    return link


def needs_sign_in_method(user: User) -> bool:
    """Made by the system: no password and no passkey yet, so the link page must set one."""
    return not user.has_usable_password() and not user.passkeys.exists()


def inspect(token: str) -> dict:
    link = _find(token)
    user = link.user
    return {
        "email": user.email,
        "first_name": user.first_name,
        "needs_sign_in_method": needs_sign_in_method(user),
        "expires_at": link.expires_at.isoformat(),
    }


def _activate(link: AccountLink) -> User:
    user = link.user
    now = timezone.now()
    with transaction.atomic():
        locked = AccountLink.objects.select_for_update().get(pk=link.pk)
        if locked.used_at or locked.revoked_at:
            raise LinkError(INVALID)
        locked.used_at = now
        locked.save(update_fields=["used_at"])
        user.is_active = True
        user.email_confirmed_at = now
        user.save(update_fields=["is_active", "email_confirmed_at", "password", "passkey_only"])
        audit.record(
            actor=user,
            organization_id=None,
            action="account.link.use",
            resource_type="user",
            resource_id=user.id,
            context={"link": str(link.id)},
        )
    return user


def confirm(token: str, *, password: str | None = None) -> User:
    """Confirms the email and activates the account. A system-made account must choose its password here (or use
    the passkey ceremony below instead)."""
    link = _find(token)
    user = link.user
    if needs_sign_in_method(user):
        if not password:
            raise LinkError("Choose a password, or add a passkey on your phone.")
        try:
            password_validation.validate_password(password, user)
        except ValidationError as exc:
            raise LinkError(" ".join(exc.messages)) from exc
        user.set_password(password)
    return _activate(link)


def begin_passkey(request, token: str, where: str | None) -> dict:
    """Only for a system-made account: the link stands in for the password that adding a passkey normally needs."""
    link = _find(token)
    if not needs_sign_in_method(link.user):
        raise LinkError("This account already has a way to sign in. Sign in, then add passkeys from your account.")
    request.session[SESSION_KEY] = {"link": str(link.id), "at": time.time()}
    return passkeys.registration_options(request, user=link.user, where=where)


def finish_passkey(request, token: str, credential: dict, name: str) -> User:
    link = _find(token)
    pending = request.session.pop(SESSION_KEY, None)
    if not pending or pending.get("link") != str(link.id) or time.time() - pending.get("at", 0) > SESSION_SECONDS:
        raise LinkError("Start again: open the link and choose Add a passkey.")
    if not needs_sign_in_method(link.user):
        raise LinkError(INVALID)
    passkeys.finish_registration(request, user=link.user, credential=credential, name=name or "Phone")
    link.user.passkey_only = True
    return _activate(link)
