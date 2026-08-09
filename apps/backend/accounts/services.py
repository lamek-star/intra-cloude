"""
MFA (TOTP) lifecycle (Phase 10, docs/architecture/ROADMAP.md). Kept
separate from the HTTP layer (accounts/views.py) so enrollment/
confirmation/verification are testable without going through session
machinery.
"""

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
    before confirming discards any prior unconfirmed secret."""
    secret = totp.generate_secret()
    user.mfa_secret_encrypted = encrypt_secret(secret)
    user.mfa_enabled = False
    user.mfa_confirmed_at = None
    user.save(update_fields=["mfa_secret_encrypted", "mfa_enabled", "mfa_confirmed_at"])
    return {"secret": secret, "provisioning_uri": totp.provisioning_uri(secret, account_name=user.email)}


def confirm_mfa_enrollment(*, user: User, code: str) -> None:
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
    audit.record(
        actor=user, organization_id=None, action="mfa.disable", resource_type="user", resource_id=user.id
    )


def verify_mfa_code(*, user: User, code: str) -> bool:
    if not user.mfa_enabled or not user.mfa_secret_encrypted:
        return False
    secret = decrypt_secret(bytes(user.mfa_secret_encrypted))
    return totp.verify_totp(secret, code)
