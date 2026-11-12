"""
MFA (TOTP) lifecycle (Phase 10, docs/architecture/ROADMAP.md). Kept
separate from the HTTP layer (accounts/views.py) so enrollment/
confirmation/verification are testable without going through session
machinery.
"""

from django.db import transaction
from django.utils import timezone

from audit import services as audit

from . import totp
from .crypto import decrypt_secret, encrypt_secret
from .models import User


class MFAError(Exception):
    pass


def start_mfa_enrollment(*, user: User) -> dict:
    """Generates and stores a new secret, but does NOT enable MFA yet —
    that only happens once the user proves (via confirm_mfa_enrollment)
    they can actually generate a valid code with it. Calling this again
    before confirming discards any prior unconfirmed secret.

    Refused while MFA is on: turning it off needs a current code (disable_mfa), and re-enrolling
    would otherwise clear mfa_enabled and replace the secret with no code at all."""
    if user.mfa_enabled:
        raise MFAError("Two-step sign-in is already on. Turn it off with a current code first.")
    secret = totp.generate_secret()
    user.mfa_secret_encrypted = encrypt_secret(secret)
    user.mfa_enabled = False
    user.mfa_confirmed_at = None
    user.save(update_fields=["mfa_secret_encrypted", "mfa_enabled", "mfa_confirmed_at"])
    return {"secret": secret, "provisioning_uri": totp.provisioning_uri(secret, account_name=user.email)}


def confirm_mfa_enrollment(*, user: User, code: str) -> list[str]:
    if not user.mfa_secret_encrypted:
        raise MFAError("no MFA enrollment in progress")
    secret = decrypt_secret(bytes(user.mfa_secret_encrypted))
    if not totp.verify_totp(secret, code):
        raise MFAError("invalid code")

    user.mfa_enabled = True
    user.mfa_confirmed_at = timezone.now()
    user.save(update_fields=["mfa_enabled", "mfa_confirmed_at"])
    audit.record(
        actor=user, organization_id=None, action="mfa.enable", resource_type="user", resource_id=user.id
    )
    return new_recovery_codes(user)


def disable_mfa(*, user: User, code: str) -> None:
    """Requires a currently-valid code, not just an authenticated
    session, so a hijacked session can't silently strip MFA off an
    account."""
    if not user.mfa_enabled or not user.mfa_secret_encrypted:
        raise MFAError("MFA is not enabled")
    secret = decrypt_secret(bytes(user.mfa_secret_encrypted))
    if not totp.verify_totp(secret, code):
        raise MFAError("invalid code")

    user.mfa_enabled = False
    user.mfa_secret_encrypted = None
    user.mfa_confirmed_at = None
    user.save(update_fields=["mfa_enabled", "mfa_secret_encrypted", "mfa_confirmed_at"])
    user.mfa_recovery_codes.all().delete()
    audit.record(
        actor=user, organization_id=None, action="mfa.disable", resource_type="user", resource_id=user.id
    )


def verify_mfa_code(*, user: User, code: str) -> bool:
    """A 6-digit code from the authenticator, or one of the person's unused recovery codes (used up by
    this)."""
    if not user.mfa_enabled or not user.mfa_secret_encrypted:
        return False
    code = (code or "").strip()
    if code.isdigit() and len(code) == 6:
        secret = decrypt_secret(bytes(user.mfa_secret_encrypted))
        return totp.verify_totp(secret, code)
    return use_recovery_code(user, code)


# ---- recovery codes ----------------------------------------------------------------------------------------
RECOVERY_CODE_COUNT = 10
_RECOVERY_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no 0/O, 1/I


def _normalise_recovery_code(code: str) -> str:
    return "".join(ch for ch in (code or "").upper() if ch.isalnum())


def _hash_recovery_code(code: str) -> str:
    import hashlib

    return hashlib.sha256(("ifrc:" + _normalise_recovery_code(code)).encode()).hexdigest()


def new_recovery_codes(user: User) -> list[str]:
    """Replaces the person's recovery codes with 10 new ones and returns them (the only time they are
    shown)."""
    import secrets

    from .models import MFARecoveryCode

    codes = []
    for _ in range(RECOVERY_CODE_COUNT):
        raw = "".join(secrets.choice(_RECOVERY_ALPHABET) for _ in range(8))
        codes.append(f"{raw[:4]}-{raw[4:]}")
    with transaction.atomic():
        user.mfa_recovery_codes.all().delete()
        MFARecoveryCode.objects.bulk_create(
            [MFARecoveryCode(user=user, code_hash=_hash_recovery_code(c)) for c in codes]
        )
    audit.record(
        actor=user,
        organization_id=None,
        action="mfa.recovery_codes",
        resource_type="user",
        resource_id=user.id,
    )
    return codes


def use_recovery_code(user: User, code: str) -> bool:
    from .models import MFARecoveryCode

    if len(_normalise_recovery_code(code)) != 8:
        return False
    with transaction.atomic():
        found = (
            MFARecoveryCode.objects.select_for_update()
            .filter(user=user, code_hash=_hash_recovery_code(code), used_at__isnull=True)
            .first()
        )
        if found is None:
            return False
        found.used_at = timezone.now()
        found.save(update_fields=["used_at"])
    audit.record(
        actor=user,
        organization_id=None,
        action="mfa.recovery_code_used",
        resource_type="user",
        resource_id=user.id,
        context={"left": recovery_codes_left(user)},
    )
    return True


def recovery_codes_left(user: User) -> int:
    return user.mfa_recovery_codes.filter(used_at__isnull=True).count()


# ---- passwords ---------------------------------------------------------------------------------------------
class PasswordError(Exception):
    """A password change or reset that cannot happen; the message says why, for the person."""


def change_password(*, user: User, current: str, new: str) -> None:
    """The person's own change: their current password, then a new one that passes the password rules."""
    from django.contrib.auth.password_validation import ValidationError, validate_password

    if not user.check_password(current or ""):
        raise PasswordError("The current password is not right.")
    if (new or "") == (current or ""):
        raise PasswordError("Choose a password different from the current one.")
    try:
        validate_password(new, user=user)
    except ValidationError as exc:
        raise PasswordError(" ".join(exc.messages)) from exc
    user.set_password(new)
    user.must_change_password = False
    user.save(update_fields=["password", "must_change_password"])
    audit.record(
        actor=user,
        organization_id=None,
        action="auth.password_change",
        resource_type="user",
        resource_id=user.id,
    )


def can_reset_password(actor: User, target: User) -> bool:
    """An administrator may reset only someone whose every organization they manage (users.manage there),
    never the platform's Super Administrator, a service account or themselves."""
    from organizations.models import Membership
    from permissions.services import has_permission

    if actor.pk == target.pk or hasattr(target, "service_account"):
        return False
    if has_permission(target, "system.admin", organization_id=None):
        return False
    if has_permission(actor, "system.admin", organization_id=None):
        return True
    orgs = set(
        Membership.objects.filter(user=target, status=Membership.Status.ACTIVE).values_list(
            "organization_id", flat=True
        )
    )
    return bool(orgs) and all(has_permission(actor, "users.manage", organization_id=o) for o in orgs)


def reset_password(*, actor: User, target: User, organization_id) -> str:
    """Gives the person a temporary password (returned once), signs them out everywhere, and makes them choose
    their own at the next sign-in. Two-step sign-in, if they use it, stays on."""
    import secrets

    from django.contrib.sessions.models import Session

    if not can_reset_password(actor, target):
        raise PasswordError("You cannot reset this person's password.")
    temporary = "-".join("".join(secrets.choice(_RECOVERY_ALPHABET) for _ in range(4)) for _ in range(3))
    target.set_password(temporary)
    target.must_change_password = True
    target.save(update_fields=["password", "must_change_password"])
    # Every signed-in browser of theirs signs out (sessions are kept in the database).
    for session in Session.objects.filter(expire_date__gt=timezone.now()).iterator():
        if session.get_decoded().get("_auth_user_id") == str(target.pk):
            session.delete()
    audit.record(
        actor=actor,
        organization_id=organization_id,
        action="auth.password_reset",
        resource_type="user",
        resource_id=target.id,
    )
    return temporary
