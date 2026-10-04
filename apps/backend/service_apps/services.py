"""Service-application lifecycle and the platform services a service application uses.

Views and the internal API call these functions; they hold every authorization decision
(capabilities through permissions.services.has_permission, ADR-0008) and emit the audit events.
"""

import json
import re
import uuid

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from accounts.models import User
from audit import services as audit
from audit.models import AuditEvent
from organizations.models import Membership
from organizations.services import get_member_organization
from permissions.services import has_permission
from storage.models import Bucket, FileObject, Folder
from workspaces.models import Project, Workspace

from . import provisioning
from .deployments import Deployment, all_deployments, get_deployment
from .models import ServiceApp, ServiceAppAuditReceipt
from .types import clean_config, get_type

WORKSPACE_NAME = "Applications"
MANAGE = "app_instance.manage"


class Conflict(ValidationError):
    status_code = 409


def _resource(app: ServiceApp):
    return ("service_app", app.id)


def can(user, app: ServiceApp, capability: str) -> bool:
    return has_permission(user, capability, organization_id=app.organization_id, resource=_resource(app))


def can_open(user, app: ServiceApp) -> bool:
    return app.enabled and app.removed_at is None and can(user, app, get_type(app.app_type).open_capability)


def can_configure(user, app: ServiceApp) -> bool:
    return can(user, app, get_type(app.app_type).settings_capability) or can(user, app, MANAGE)


def can_manage(user, app: ServiceApp) -> bool:
    return has_permission(user, MANAGE, organization_id=app.organization_id)


# ---------------------------------------------------------------- queries


def _active_org_ids(user) -> set:
    """Organizations the user is an active member of. (Membership, not role assignment: a member
    whose only access is a grant on one application instance must still see that instance.)"""
    if not user or not user.is_authenticated:
        return set()
    return set(
        Membership.objects.filter(user=user, status=Membership.Status.ACTIVE).values_list(
            "organization_id", flat=True
        )
    )


def visible_apps(user) -> list[ServiceApp]:
    """Installed applications in the user's organizations that the user may open, configure or
    manage. Anything else in those organizations -- and everything in other organizations -- is
    invisible."""
    apps = ServiceApp.objects.filter(organization_id__in=_active_org_ids(user)).select_related("organization")
    return [
        a
        for a in apps
        if can_manage(user, a) or (a.removed_at is None and (can_open(user, a) or can_configure(user, a)))
    ]


def get_visible_app(user, app_id) -> ServiceApp:
    """404 (not 403) for anything the user cannot see, so existence does not leak."""
    for app in visible_apps(user):
        if str(app.id) == str(app_id):
            return app
    raise NotFound()


def installable_deployments(user) -> list[dict]:
    """Deployment slots with nothing installed, offered to people who may install applications."""
    orgs = [
        org_id for org_id in _active_org_ids(user) if has_permission(user, MANAGE, organization_id=org_id)
    ]
    if not orgs:
        return []
    taken = set(ServiceApp.objects.values_list("deployment", flat=True))
    return [
        {
            "deployment": d.key,
            "app_type": d.app_type.key,
            "product_name": d.app_type.product_name,
            "description": d.app_type.description,
            "organizations": [str(o) for o in orgs],
        }
        for d in all_deployments().values()
        if d.key not in taken
    ]


# ---------------------------------------------------------------- lifecycle


def _unique_name(model, parent_field: str, parent, base: str) -> str:
    name = base[:190]
    n = 2
    while model.objects.filter(**{parent_field: parent, "name": name}).exists():
        name = f"{base[:185]} ({n})"
        n += 1
    return name


def install(
    actor, *, deployment_key: str, organization_id, display_name: str, config: dict | None = None
) -> ServiceApp:
    deployment = get_deployment(deployment_key)
    if deployment is None:
        raise ValidationError({"deployment": "This application is not available in this installation."})
    organization = get_member_organization(actor, organization_id)
    if not has_permission(actor, MANAGE, organization_id=organization.id):
        raise PermissionDenied("Installing applications needs the app_instance.manage capability.")
    display_name = (display_name or "").strip()
    if not display_name or len(display_name) > 200:
        raise ValidationError({"display_name": "Enter the shop name (up to 200 characters)."})
    if ServiceApp.objects.filter(deployment=deployment.key).exists():
        raise Conflict({"deployment": "This application is already installed."})
    app_type = deployment.app_type
    cleaned = clean_config(app_type, {}, {"shopName": display_name, **(config or {})})

    app_id = uuid.uuid4()
    schema = f"svc_{app_type.key.replace('_', '')[:8]}_{app_id.hex[:12]}"
    # Tenant DDL cannot join the control-plane transaction; it is idempotent and runs first, so a
    # failure below leaves at most an empty schema and no registry entry.
    provisioning.ensure_role(deployment.db_role, deployment.db_password)
    provisioning.ensure_schema(schema, deployment.db_role)

    with transaction.atomic():
        workspace = Workspace.objects.filter(organization=organization, name=WORKSPACE_NAME).first()
        if workspace is None:
            workspace = Workspace.objects.create(
                organization=organization, name=WORKSPACE_NAME, created_by=actor
            )
            audit.record(
                actor=actor,
                organization_id=organization.id,
                action="workspace.create",
                resource_type="workspace",
                resource_id=workspace.id,
                context={"name": workspace.name},
            )
        project = Project.objects.create(
            workspace=workspace,
            name=_unique_name(Project, "workspace", workspace, f"{display_name} ({app_type.product_name})"),
            created_by=actor,
        )
        audit.record(
            actor=actor,
            organization_id=organization.id,
            action="project.create",
            resource_type="project",
            resource_id=project.id,
            context={"name": project.name},
        )
        bucket = Bucket.objects.create(
            project=project, name=f"{app_type.product_name} files", created_by=actor
        )
        audit.record(
            actor=actor,
            organization_id=organization.id,
            action="storage.bucket.create",
            resource_type="bucket",
            resource_id=bucket.id,
            context={"name": bucket.name},
        )
        app = ServiceApp.objects.create(
            id=app_id,
            organization=organization,
            project=project,
            deployment=deployment.key,
            app_type=app_type.key,
            display_name=display_name,
            config=cleaned,
            schema_name=schema,
            bucket=bucket,
            created_by=actor,
        )
        audit.record(
            actor=actor,
            organization_id=organization.id,
            action="service_app.install",
            resource_type="service_app",
            resource_id=app.id,
            context={"app_type": app_type.key, "deployment": deployment.key, "display_name": display_name},
        )
    return app


def update(actor, app: ServiceApp, *, display_name=None, config=None, enabled=None) -> ServiceApp:
    changed = []
    with transaction.atomic():
        app = ServiceApp.objects.select_for_update().get(pk=app.pk)
        if app.removed_at is not None:
            raise ValidationError("This application has been removed; reinstate it first.")
        if display_name is not None or config is not None:
            if not can_configure(actor, app):
                raise PermissionDenied()
            if display_name is not None:
                display_name = display_name.strip()
                if not display_name or len(display_name) > 200:
                    raise ValidationError({"display_name": "Enter a name (up to 200 characters)."})
                app.display_name = display_name
                changed.append("display_name")
            if config is not None:
                app.config = clean_config(get_type(app.app_type), app.config, config)
                changed.append("config")
                changed += [f"config.{k}" for k in sorted(config)]
        if enabled is not None:
            if not can_manage(actor, app):
                raise PermissionDenied()
            app.enabled = bool(enabled)
            changed.append("enabled")
        app.save()
        audit.record(
            actor=actor,
            organization_id=app.organization_id,
            action="service_app.update",
            resource_type="service_app",
            resource_id=app.id,
            context={"fields": changed, "enabled": app.enabled},
        )
    return app


def remove(actor, app: ServiceApp, *, confirm_name: str, delete_data: bool) -> dict:
    """Removes an application without touching IntraForge or other applications.

    Without delete_data the application is closed and hidden, and its schema and files are kept
    (reinstate() brings it back). With delete_data a fresh backup of the tenant database and of
    object storage is taken first, and nothing is deleted unless both succeed; then its schema and
    files are erased."""
    if not can_manage(actor, app):
        raise PermissionDenied()
    if (confirm_name or "").strip() != app.display_name:
        raise ValidationError({"confirm_name": "Type the application's name exactly to confirm."})
    if not delete_data:
        with transaction.atomic():
            ServiceApp.objects.filter(pk=app.pk).update(removed_at=timezone.now(), enabled=False)
            app.sessions.filter(revoked_at__isnull=True).update(revoked_at=timezone.now())
            audit.record(
                actor=actor,
                organization_id=app.organization_id,
                action="service_app.remove",
                resource_type="service_app",
                resource_id=app.id,
                context={"data_kept": True, "schema": app.schema_name, "bucket": str(app.bucket_id)},
            )
        return {"removed": True, "data_deleted": False}

    from system.backups import run_backup
    from system.models import BackupRecord

    backups = {}
    for kind in (BackupRecord.BackupType.TENANT_DB, BackupRecord.BackupType.OBJECT_STORAGE):
        record = run_backup(kind)
        if record.status != BackupRecord.Status.SUCCESS:
            audit.record(
                actor=actor,
                organization_id=app.organization_id,
                action="service_app.delete_data",
                resource_type="service_app",
                resource_id=app.id,
                result=AuditEvent.Result.ERROR,
                context={"reason": "safety backup failed", "backup_type": kind},
            )
            raise ValidationError("The safety backup failed, so nothing was deleted. Check Backup & Restore.")
        backups[kind] = str(record.id)
    counts = (
        provisioning.schema_summary(app.schema_name) if provisioning.schema_exists(app.schema_name) else {}
    )
    provisioning.drop_schema(app.schema_name)
    from storage.backends import get_client

    client = get_client()
    keys = list(FileObject.objects.filter(bucket=app.bucket).values_list("object_key", flat=True))
    with transaction.atomic():
        org_id, app_pk, bucket = app.organization_id, app.pk, app.bucket
        FileObject.objects.filter(bucket=bucket).delete()
        Folder.objects.filter(bucket=bucket).delete()
        app.delete()
        bucket.delete()
        audit.record(
            actor=actor,
            organization_id=org_id,
            action="service_app.delete_data",
            resource_type="service_app",
            resource_id=app_pk,
            context={"schema": app.schema_name, "rows": counts, "files": len(keys), "backups": backups},
        )
    for key in keys:
        try:
            client.delete(key)
        except Exception:  # noqa: BLE001 -- best effort; the catalog rows are already gone
            pass
    return {"removed": True, "data_deleted": True, "rows": counts, "files": len(keys), "backups": backups}


def reinstate(actor, app: ServiceApp) -> ServiceApp:
    if not can_manage(actor, app):
        raise PermissionDenied()
    deployment = get_deployment(app.deployment)
    if deployment is None:
        raise ValidationError("This application's service is not part of this installation any more.")
    provisioning.ensure_role(deployment.db_role, deployment.db_password)
    provisioning.ensure_schema(app.schema_name, deployment.db_role)
    ServiceApp.objects.filter(pk=app.pk).update(removed_at=None, enabled=True)
    audit.record(
        actor=actor,
        organization_id=app.organization_id,
        action="service_app.reinstate",
        resource_type="service_app",
        resource_id=app.id,
    )
    app.refresh_from_db()
    return app


def sync_deployment(deployment: Deployment) -> ServiceApp | None:
    """Idempotent start-up step: the deployment's role exists with the configured password and its
    installed instance's schema is owned by it (after a restore or a password change)."""
    provisioning.ensure_role(deployment.db_role, deployment.db_password)
    app = ServiceApp.objects.filter(deployment=deployment.key).first()
    if app is not None:
        provisioning.ensure_schema(app.schema_name, deployment.db_role)
    return app


# ---------------------------------------------------------------- platform services for the service


def heartbeat(app: ServiceApp, *, version: str) -> None:
    ServiceApp.objects.filter(pk=app.pk).update(
        last_seen_at=timezone.now(), reported_version=(version or "")[:64]
    )


_EVENT_ID = re.compile(r"^[A-Za-z0-9-]{8,64}$")
_ACTION = re.compile(r"^[a-z0-9_.-]{1,60}$")
_ENTITY = re.compile(r"^[A-Za-z0-9_.-]{1,50}$")


def _member_user(app: ServiceApp, actor_id) -> User | None:
    if not actor_id:
        return None
    try:
        uid = uuid.UUID(str(actor_id))
    except ValueError:
        return None
    return User.objects.filter(pk=uid, memberships__organization_id=app.organization_id).first()


def ingest_audit(app: ServiceApp, events: list) -> list[str]:
    """Records the service's audit events in IntraForge's audit log, exactly once each.
    Returns the ids now known to IntraForge (newly recorded or already recorded)."""
    if not isinstance(events, list) or len(events) > 500:
        raise ValidationError({"events": "Send up to 500 events."})
    app_type = get_type(app.app_type)
    prefix = app_type.key.replace("_", "")
    accepted = []
    for raw in events:
        if not isinstance(raw, dict):
            raise ValidationError({"events": "Each event must be an object."})
        event_id = str(raw.get("id", ""))
        action = str(raw.get("action", ""))
        entity_type = str(raw.get("entityType", ""))
        entity_id = str(raw.get("entityId") or "")[:64]
        if not _EVENT_ID.match(event_id) or not _ACTION.match(action) or not _ENTITY.match(entity_type):
            raise ValidationError({"events": f"Malformed event {event_id[:64]!r}."})
        metadata = raw.get("metadata") if isinstance(raw.get("metadata"), dict) else {}
        if len(json.dumps(metadata, default=str)) > 4000:
            metadata = {"truncated": True}
        occurred = parse_datetime(str(raw.get("at", ""))) if raw.get("at") else None
        with transaction.atomic():
            if ServiceAppAuditReceipt.objects.select_for_update().filter(event_id=event_id).exists():
                accepted.append(event_id)
                continue
            event = audit.record(
                actor=_member_user(app, raw.get("actorId")),
                organization_id=app.organization_id,
                action=f"{prefix}.{action}"[:100],
                resource_type=f"{prefix}.{entity_type}"[:100],
                resource_id=entity_id,
                context={
                    "application": {"id": str(app.id), "type": app_type.key, "name": app.display_name},
                    "summary": str(raw.get("summary", ""))[:500],
                    "metadata": metadata,
                    "occurred_at": occurred.isoformat() if occurred else None,
                    "actor_label": str(raw.get("actorLabel", ""))[:200],
                    "source_event_id": event_id,
                },
            )
            ServiceAppAuditReceipt.objects.create(event_id=event_id, service_app=app, audit_event=event)
        accepted.append(event_id)
    return accepted


def config_for_service(app: ServiceApp) -> dict:
    from .types import public_config

    return public_config(get_type(app.app_type), app.config)


def update_config_for_actor(app: ServiceApp, actor_id, patch: dict) -> dict:
    """A settings change made inside the application: IntraForge re-checks the acting user's
    capability itself instead of trusting the service's decision."""
    user = _member_user(app, actor_id)
    if (
        user is None
        or not user.is_active
        or not Membership.objects.filter(
            organization_id=app.organization_id, user=user, status=Membership.Status.ACTIVE
        ).exists()
    ):
        raise PermissionDenied()
    update(user, app, config=patch)
    app.refresh_from_db()
    return config_for_service(app)


def application_users(app: ServiceApp) -> list[dict]:
    """People who may open the application (for its user list and name look-ups); no secrets."""
    from .sessions import capabilities_for, display_name

    out = []
    members = Membership.objects.filter(
        organization_id=app.organization_id, status=Membership.Status.ACTIVE
    ).select_related("user")
    open_cap = get_type(app.app_type).open_capability
    for m in members:
        caps = capabilities_for(m.user, app)
        if open_cap in caps:
            out.append(
                {
                    "id": str(m.user.pk),
                    "email": m.user.email,
                    "displayName": display_name(m.user),
                    "active": m.user.is_active,
                    "capabilities": caps,
                }
            )
    return out


# ---------------------------------------------------------------- files


_KIND = re.compile(r"^[A-Z][A-Z_]{1,39}$")


def _folder(app: ServiceApp, kind: str, creator) -> Folder:
    name = kind.lower().replace("_", "-")
    folder = Folder.objects.filter(bucket=app.bucket, parent=None, name=name).first()
    return folder or Folder.objects.create(bucket=app.bucket, parent=None, name=name, created_by=creator)


def store_file(app: ServiceApp, *, uploaded_file, kind: str, actor_id) -> FileObject:
    """Stores an application file in IntraForge object storage through the ordinary upload pipeline
    (size limit, content sniffing, optional malware scan, SHA-256, audit)."""
    from storage import services as storage

    if not _KIND.match(kind or ""):
        raise ValidationError({"kind": "Invalid file kind."})
    if uploaded_file is None or uploaded_file.size == 0:
        raise ValidationError({"file": "Empty file."})
    creator = _member_user(app, actor_id) or app.created_by
    safe = re.sub(r"[^\w.() -]", "_", uploaded_file.name or "file")[:120] or "file"
    with transaction.atomic():
        folder = _folder(app, kind, creator)
    return storage.upload_file(
        bucket=app.bucket,
        folder=folder,
        uploaded_file=uploaded_file,
        display_filename=f"{uuid.uuid4().hex[:12]}-{safe}",
        creator=creator,
    )


def app_file(app: ServiceApp, file_id) -> FileObject:
    """Only files in the instance's own bucket are reachable: a file id from anywhere else is 404."""
    try:
        return FileObject.objects.get(pk=file_id, bucket=app.bucket, status=FileObject.Status.ACTIVE)
    except (FileObject.DoesNotExist, ValueError, DjangoValidationError) as exc:
        raise NotFound() from exc
