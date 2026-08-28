"""
Environment lifecycle: create/update/clone/disable/delete, secrets,
variables, webhooks, environment-scoped credential issuance (reusing
applications.services -- never a second credential mechanism), and the
runtime isolation check databases/storage call before returning row or
file data to a credential-authenticated request.
"""

from __future__ import annotations

import uuid

from django.db import transaction
from django.http import Http404
from django.utils import timezone
from django.utils.text import slugify

from applications.models import ApplicationCredential
from audit import services as audit
from organizations.models import Membership
from permissions.services import has_permission

from . import crypto
from .models import Environment, EnvironmentSecret, EnvironmentVariable, EnvironmentWebhook


class EnvironmentValidationError(Exception):
    pass


class EnvironmentPermissionError(Exception):
    pass


def get_member_environment(user, environment_id) -> Environment:
    """Same isolation discipline as every other get_member_* helper: 404,
    not 403, if the requester isn't an active member of the owning
    organization (docs/security/THREAT_MODEL.md Section 4)."""
    try:
        return Environment.objects.select_related("application__organization").get(
            id=environment_id,
            application__organization__memberships__user=user,
            application__organization__memberships__status=Membership.Status.ACTIVE,
        )
    except Environment.DoesNotExist as exc:
        raise Http404 from exc


def can_manage_environment(user, environment: Environment, base_permission_code: str) -> bool:
    """The one place production's extra gate is enforced: holding
    `base_permission_code` is always required; a production-tier
    Environment additionally requires `environment.production.manage`.
    Capability-based (ADR-0008) -- never a role-name check. Resource-
    scoped via ResourceGrant is also honored (an Application's service
    account, or a user explicitly granted access to one Environment, can
    hold the permission on just that resource without a role-wide
    grant)."""
    resource = ("environment", environment.id)
    if not has_permission(
        user, base_permission_code, organization_id=environment.organization_id, resource=resource
    ):
        return False
    if environment.is_production_tier and not has_permission(
        user, "environment.production.manage", organization_id=environment.organization_id
    ):
        return False
    return True


def _unique_slug(application, base_slug: str, *, exclude_id=None) -> str:
    slug = base_slug or "environment"
    candidate = slug
    n = 1
    qs = Environment.objects.filter(application=application, slug=candidate)
    if exclude_id:
        qs = qs.exclude(id=exclude_id)
    while qs.exists():
        n += 1
        candidate = f"{slug}-{n}"
        qs = Environment.objects.filter(application=application, slug=candidate)
        if exclude_id:
            qs = qs.exclude(id=exclude_id)
    return candidate


def create_environment(
    *,
    application,
    name: str,
    environment_type: str,
    actor,
    is_production_tier: bool | None = None,
    config: dict | None = None,
    slug: str | None = None,
) -> Environment:
    if is_production_tier is None:
        is_production_tier = environment_type == "production"
    environment = Environment.objects.create(
        application=application,
        name=name,
        slug=_unique_slug(application, slugify(slug or name)),
        environment_type=environment_type,
        is_production_tier=is_production_tier,
        config=config or {},
        created_by=actor,
    )
    audit.record(
        actor=actor,
        organization_id=application.organization_id,
        action="environment.created",
        resource_type="environment",
        resource_id=environment.id,
        context={"application": str(application.id), "name": name, "environment_type": environment_type},
    )
    return environment


def update_environment(*, environment: Environment, actor, **fields) -> Environment:
    """`fields` may include name, config, environment_type,
    is_production_tier -- whichever the caller validated and wants to
    change. `slug` is deliberately not updatable here (it's the stable
    identifier credentials/URLs may already reference)."""
    changed = []
    for field, value in fields.items():
        if value is not None and getattr(environment, field) != value:
            setattr(environment, field, value)
            changed.append(field)
    if changed:
        environment.updated_at = timezone.now()
        environment.last_activity_at = timezone.now()
        environment.save(update_fields=[*changed, "updated_at", "last_activity_at"])
        audit.record(
            actor=actor,
            organization_id=environment.organization_id,
            action="environment.updated",
            resource_type="environment",
            resource_id=environment.id,
            context={"changed_fields": changed},
        )
    return environment


def clone_environment(*, environment: Environment, actor, name: str, slug: str | None = None) -> Environment:
    """Copies configuration and variables, and webhook URLs/event types --
    but deliberately creates zero secrets and zero webhook signing
    secrets on the clone. A secret value or a webhook's signing secret
    silently shared between two Environments (e.g. a freshly-cloned
    "staging-2" quietly holding production's API key) is exactly the
    kind of cross-environment leak this subsystem exists to prevent;
    cloning configuration shape is useful, cloning secret material by
    default is not something this implements without the operator
    explicitly re-creating each one for the clone."""
    with transaction.atomic():
        clone = Environment.objects.create(
            application=environment.application,
            name=name,
            slug=_unique_slug(environment.application, slugify(slug or name)),
            environment_type=environment.environment_type,
            is_production_tier=environment.is_production_tier,
            config=dict(environment.config),
            created_by=actor,
        )
        for variable in environment.variables.all():
            EnvironmentVariable.objects.create(environment=clone, key=variable.key, value=variable.value)
        for webhook in environment.webhooks.all():
            EnvironmentWebhook.objects.create(
                environment=clone,
                url=webhook.url,
                event_types=list(webhook.event_types),
                enabled=webhook.enabled,
                # A fresh signing secret, never the source's -- see
                # docstring above.
                signing_secret_ciphertext=crypto.encrypt_secret(uuid.uuid4().hex),
                created_by=actor,
            )
    audit.record(
        actor=actor,
        organization_id=environment.organization_id,
        action="environment.created",
        resource_type="environment",
        resource_id=clone.id,
        context={"cloned_from": str(environment.id)},
    )
    return clone


def set_environment_status(*, environment: Environment, actor, status: str) -> Environment:
    if status not in Environment.Status.values:
        raise EnvironmentValidationError(f"Unknown status: {status!r}")
    environment.status = status
    environment.updated_at = timezone.now()
    environment.save(update_fields=["status", "updated_at"])
    audit.record(
        actor=actor,
        organization_id=environment.organization_id,
        action="environment.disabled" if status == Environment.Status.DISABLED else "environment.updated",
        resource_type="environment",
        resource_id=environment.id,
        context={"status": status},
    )
    return environment


def delete_environment(
    *, environment: Environment, actor, confirm_name: str, confirm_production_understanding: bool = False
) -> None:
    """Deletion always requires typing the Environment's exact name.
    A production-tier Environment additionally requires the caller to
    explicitly pass `confirm_production_understanding=True` -- a second,
    distinct confirmation a UI can't satisfy by only wiring up the name
    field, matching the spec's "Production deletion requires stronger
    confirmation" requirement as a real server-side rule, not merely a
    frontend dialog's copy."""
    if confirm_name != environment.name:
        raise EnvironmentValidationError("Type the environment name exactly to confirm deletion.")
    if environment.is_production_tier and not confirm_production_understanding:
        raise EnvironmentValidationError(
            "Deleting a production environment requires explicit additional confirmation."
        )
    environment_id = environment.id
    organization_id = environment.organization_id
    application_id = environment.application_id
    name = environment.name
    environment.delete()
    audit.record(
        actor=actor,
        organization_id=organization_id,
        action="environment.deleted",
        resource_type="environment",
        resource_id=environment_id,
        context={"application": str(application_id), "name": name},
    )


# --- Variables (plain, non-secret) -----------------------------------


def set_variable(*, environment: Environment, key: str, value: str, actor) -> EnvironmentVariable:
    variable, _ = EnvironmentVariable.objects.update_or_create(
        environment=environment, key=key, defaults={"value": value}
    )
    environment.last_activity_at = timezone.now()
    environment.save(update_fields=["last_activity_at"])
    audit.record(
        actor=actor,
        organization_id=environment.organization_id,
        action="configuration.updated",
        resource_type="environment_variable",
        resource_id=variable.id,
        context={"environment": str(environment.id), "key": key},
    )
    return variable


def delete_variable(*, variable: EnvironmentVariable, actor) -> None:
    environment = variable.environment
    variable_id = variable.id
    key = variable.key
    variable.delete()
    audit.record(
        actor=actor,
        organization_id=environment.organization_id,
        action="configuration.updated",
        resource_type="environment_variable",
        resource_id=variable_id,
        context={"environment": str(environment.id), "key": key, "deleted": True},
    )


# --- Secrets (encrypted, write-only after creation) --------------------


def create_secret(*, environment: Environment, key: str, value: str, actor) -> EnvironmentSecret:
    secret = EnvironmentSecret.objects.create(
        environment=environment,
        key=key,
        value_ciphertext=crypto.encrypt_secret(value),
        created_by=actor,
    )
    environment.last_activity_at = timezone.now()
    environment.save(update_fields=["last_activity_at"])
    audit.record(
        actor=actor,
        organization_id=environment.organization_id,
        action="secret.created",
        resource_type="environment_secret",
        resource_id=secret.id,
        # Never the value -- only the key name, same discipline as every
        # other secret-adjacent audit event in this codebase.
        context={"environment": str(environment.id), "key": key},
    )
    return secret


def rotate_secret(*, secret: EnvironmentSecret, value: str, actor) -> EnvironmentSecret:
    secret.value_ciphertext = crypto.encrypt_secret(value)
    secret.rotated_at = timezone.now()
    secret.save(update_fields=["value_ciphertext", "rotated_at"])
    audit.record(
        actor=actor,
        organization_id=secret.environment.organization_id,
        action="secret.rotated",
        resource_type="environment_secret",
        resource_id=secret.id,
        context={"environment": str(secret.environment_id), "key": secret.key},
    )
    return secret


def delete_secret(*, secret: EnvironmentSecret, actor) -> None:
    environment = secret.environment
    secret_id = secret.id
    key = secret.key
    secret.delete()
    audit.record(
        actor=actor,
        organization_id=environment.organization_id,
        action="secret.deleted",
        resource_type="environment_secret",
        resource_id=secret_id,
        context={"environment": str(environment.id), "key": key},
    )


# --- Webhooks -----------------------------------------------------------


def create_webhook(
    *, environment: Environment, url: str, event_types: list[str], actor, enabled: bool = True
) -> tuple[EnvironmentWebhook, str]:
    """Returns (webhook, plaintext_signing_secret) -- the plaintext is
    shown exactly once, same discipline as an ApplicationCredential."""
    signing_secret = uuid.uuid4().hex + uuid.uuid4().hex
    webhook = EnvironmentWebhook.objects.create(
        environment=environment,
        url=url,
        event_types=event_types,
        enabled=enabled,
        signing_secret_ciphertext=crypto.encrypt_secret(signing_secret),
        created_by=actor,
    )
    audit.record(
        actor=actor,
        organization_id=environment.organization_id,
        action="configuration.updated",
        resource_type="environment_webhook",
        resource_id=webhook.id,
        context={"environment": str(environment.id), "url": url},
    )
    return webhook, signing_secret


def update_webhook(*, webhook: EnvironmentWebhook, actor, **fields) -> EnvironmentWebhook:
    changed = []
    for field, value in fields.items():
        if value is not None and getattr(webhook, field) != value:
            setattr(webhook, field, value)
            changed.append(field)
    if changed:
        webhook.save(update_fields=changed)
        audit.record(
            actor=actor,
            organization_id=webhook.environment.organization_id,
            action="configuration.updated",
            resource_type="environment_webhook",
            resource_id=webhook.id,
            context={"environment": str(webhook.environment_id), "changed_fields": changed},
        )
    return webhook


def delete_webhook(*, webhook: EnvironmentWebhook, actor) -> None:
    environment = webhook.environment
    webhook_id = webhook.id
    webhook.delete()
    audit.record(
        actor=actor,
        organization_id=environment.organization_id,
        action="configuration.updated",
        resource_type="environment_webhook",
        resource_id=webhook_id,
        context={"environment": str(environment.id), "deleted": True},
    )


# --- Environment-scoped credentials (reuses applications.services) -----


def issue_environment_credential(*, environment: Environment, actor, expires_at=None):
    """Reuses applications.services.issue_credential -- the exact same
    mechanism every Application credential already goes through, not a
    parallel one -- passing this Environment so the credential's access
    is scoped to it (see check_environment_scope below)."""
    from applications import services as application_services

    credential, token = application_services.issue_credential(
        service_account=environment.application.service_account,
        actor=actor,
        expires_at=expires_at,
        environment=environment,
    )
    audit.record(
        actor=actor,
        organization_id=environment.organization_id,
        action="credential.created",
        resource_type="application_credential",
        resource_id=credential.id,
        context={"environment": str(environment.id)},
    )
    return credential, token


def revoke_environment_credential(*, credential: ApplicationCredential, actor) -> None:
    from applications import services as application_services

    environment_id = credential.environment_id
    application_services.revoke_credential(credential=credential, actor=actor)
    audit.record(
        actor=actor,
        organization_id=credential.organization_id,
        action="credential.revoked",
        resource_type="application_credential",
        resource_id=credential.id,
        context={"environment": str(environment_id) if environment_id else None},
    )


def rotate_environment_credential(*, credential: ApplicationCredential, actor):
    from applications import services as application_services

    new_credential, token = application_services.rotate_credential(credential=credential, actor=actor)
    audit.record(
        actor=actor,
        organization_id=new_credential.organization_id,
        action="credential.rotated",
        resource_type="application_credential",
        resource_id=new_credential.id,
        context={
            "environment": str(new_credential.environment_id) if new_credential.environment_id else None
        },
    )
    return new_credential, token


# --- Database / storage bindings ----------------------------------------


def bind_database(*, environment: Environment, tenant_database, actor) -> None:
    tenant_database.environment = environment
    tenant_database.save(update_fields=["environment"])
    environment.last_activity_at = timezone.now()
    environment.save(update_fields=["last_activity_at"])
    audit.record(
        actor=actor,
        organization_id=environment.organization_id,
        action="environment.updated",
        resource_type="environment",
        resource_id=environment.id,
        context={"database_bound": str(tenant_database.id)},
    )


def unbind_database(*, environment: Environment, actor) -> None:
    from databases.models import TenantDatabase

    TenantDatabase.objects.filter(environment=environment).update(environment=None)
    environment.last_activity_at = timezone.now()
    environment.save(update_fields=["last_activity_at"])
    audit.record(
        actor=actor,
        organization_id=environment.organization_id,
        action="environment.updated",
        resource_type="environment",
        resource_id=environment.id,
        context={"database_unbound": True},
    )


def bind_storage(*, environment: Environment, bucket, actor) -> None:
    bucket.environment = environment
    bucket.save(update_fields=["environment"])
    environment.last_activity_at = timezone.now()
    environment.save(update_fields=["last_activity_at"])
    audit.record(
        actor=actor,
        organization_id=environment.organization_id,
        action="environment.updated",
        resource_type="environment",
        resource_id=environment.id,
        context={"bucket_bound": str(bucket.id)},
    )


def unbind_storage(*, environment: Environment, actor) -> None:
    from storage.models import Bucket

    Bucket.objects.filter(environment=environment).update(environment=None)
    environment.last_activity_at = timezone.now()
    environment.save(update_fields=["last_activity_at"])
    audit.record(
        actor=actor,
        organization_id=environment.organization_id,
        action="environment.updated",
        resource_type="environment",
        resource_id=environment.id,
        context={"bucket_unbound": True},
    )


# --- Runtime isolation enforcement --------------------------------------


def check_environment_scope(request, *, tenant_database=None, bucket=None) -> bool:
    """True if this request is allowed to reach the given resource. Only
    ever restricts requests authenticated via an environment-scoped
    ApplicationCredential (request.auth) -- human/session-authenticated
    requests and credentials with no environment (environment_id is
    None) are unrestricted by this specific check, exactly as before this
    subsystem existed.

    When the credential IS environment-scoped: the target resource must
    be bound to that *exact* Environment. A resource with no binding at
    all (environment_id is None on the TenantDatabase/Bucket) is *not*
    reachable through an environment-scoped credential -- explicit
    binding is required, not merely "no conflicting binding exists" --
    which is what actually stops a Development credential from reaching
    a Production database that simply hasn't been assigned to any
    Environment's binding slot yet.
    """
    credential = getattr(request, "auth", None)
    if not isinstance(credential, ApplicationCredential) or credential.environment_id is None:
        return True
    if tenant_database is not None:
        return tenant_database.environment_id == credential.environment_id
    if bucket is not None:
        return bucket.environment_id == credential.environment_id
    return True
