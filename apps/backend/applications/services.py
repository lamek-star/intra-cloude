"""
Application/service-account lifecycle: register an Application (creates
its ServiceAccount and the User row that identity resolves to), issue/
rotate/revoke credentials, and resolve a bearer token back to a
ServiceAccount at request time (applications/authentication.py).
"""

import hashlib
import hmac
import secrets
import uuid

from django.db import transaction
from django.utils import timezone

from accounts.models import User
from audit import services as audit
from organizations.models import Membership

from .models import Application, ApplicationCredential, ServiceAccount

TOKEN_PREFIX = "pdc_sk_"


class InvalidCredential(Exception):
    pass


def register_application(*, organization, name: str, description: str, owner) -> Application:
    with transaction.atomic():
        application = Application.objects.create(
            organization=organization, name=name, description=description, owner=owner
        )
        identity_user = User.objects.create_user(
            email=f"service-account+{application.id}@service.internal"
        )
        # No login is ever possible for this identity: no usable password
        # can be set for it, independent of anything a caller passes in
        # (defense in depth beyond simply omitting a password at creation).
        identity_user.set_unusable_password()
        identity_user.save(update_fields=["password"])
        ServiceAccount.objects.create(application=application, identity_user=identity_user)
        # Grants no permissions by itself (Membership never does) — only
        # makes the identity resolvable by the existing get_member_*
        # helpers every resource type already uses.
        Membership.objects.create(
            user=identity_user, organization=organization, status=Membership.Status.ACTIVE
        )
    audit.record(
        actor=owner,
        organization_id=organization.id,
        action="application.create",
        resource_type="application",
        resource_id=application.id,
        context={"name": name},
    )
    return application


def _hash_secret(secret: str) -> str:
    return hashlib.sha256(secret.encode()).hexdigest()


def issue_credential(
    *, service_account: ServiceAccount, actor, expires_at=None, environment=None
) -> tuple[ApplicationCredential, str]:
    """Returns (credential, plaintext_token). The plaintext is never
    stored or logged — this is the only place it ever exists as a whole
    string.

    `environment`, if given, scopes this credential to that Environment
    (environments app) -- enforced by environments.services.
    check_environment_scope, called from databases/storage's row/file
    views, not here; this function only records the binding."""
    credential_id = uuid.uuid4()
    secret = secrets.token_urlsafe(32)
    token = f"{TOKEN_PREFIX}{credential_id.hex}.{secret}"

    credential = ApplicationCredential.objects.create(
        id=credential_id,
        service_account=service_account,
        secret_hash=_hash_secret(secret),
        created_by=actor,
        expires_at=expires_at,
        environment=environment,
    )
    audit.record(
        actor=actor,
        organization_id=service_account.organization_id,
        action="application.credentials.create",
        resource_type="application_credential",
        resource_id=credential.id,
        context={"environment": str(environment.id)} if environment else None,
    )
    return credential, token


def revoke_credential(*, credential: ApplicationCredential, actor) -> None:
    credential.revoked_at = timezone.now()
    credential.save(update_fields=["revoked_at"])
    audit.record(
        actor=actor,
        organization_id=credential.organization_id,
        action="application.credentials.revoke",
        resource_type="application_credential",
        resource_id=credential.id,
    )


def rotate_credential(*, credential: ApplicationCredential, actor) -> tuple[ApplicationCredential, str]:
    with transaction.atomic():
        revoke_credential(credential=credential, actor=actor)
        # Preserves the same Environment scope (if any) -- rotating a
        # credential must never silently widen it to unscoped access.
        new_credential, token = issue_credential(
            service_account=credential.service_account, actor=actor, environment=credential.environment
        )
    audit.record(
        actor=actor,
        organization_id=credential.organization_id,
        action="application.credentials.rotate",
        resource_type="application_credential",
        resource_id=new_credential.id,
        context={"replaced": str(credential.id)},
    )
    return new_credential, token


def resolve_credential(token: str) -> ApplicationCredential:
    if not token.startswith(TOKEN_PREFIX):
        raise InvalidCredential("unrecognized token format")

    remainder = token[len(TOKEN_PREFIX) :]
    id_part, _, secret = remainder.partition(".")
    if not secret:
        raise InvalidCredential("unrecognized token format")

    try:
        credential_id = uuid.UUID(id_part)
    except ValueError as exc:
        raise InvalidCredential("unrecognized token format") from exc

    try:
        credential = ApplicationCredential.objects.select_related(
            "service_account__identity_user"
        ).get(id=credential_id)
    except ApplicationCredential.DoesNotExist as exc:
        raise InvalidCredential("unknown credential") from exc

    if credential.revoked_at is not None:
        raise InvalidCredential("credential revoked")
    if credential.expires_at is not None and credential.expires_at <= timezone.now():
        raise InvalidCredential("credential expired")
    if not hmac.compare_digest(credential.secret_hash, _hash_secret(secret)):
        raise InvalidCredential("invalid credential")

    credential.last_used_at = timezone.now()
    credential.save(update_fields=["last_used_at"])
    if credential.environment_id is not None:
        # Best-effort "Last activity" signal for the Environment UI --
        # not itself a security control, so a stale value here (e.g. a
        # request that fails after auth) is an acceptable, non-critical
        # gap.
        from environments.models import Environment

        Environment.objects.filter(id=credential.environment_id).update(last_activity_at=timezone.now())
    return credential
