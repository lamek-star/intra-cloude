"""
Service layer for `ConnectedDatabase` (Phase 8, ADR-0009): register/test/
browse/delete an externally-hosted PostgreSQL database in connected mode.
Deliberately separate from `databases/services.py` (which owns the
TenantDatabase DDL pipeline) — this module never issues DDL/DML against
anything the platform owns; every SQL statement it triggers runs against
the *external* system through `databases/connectors.py`.
"""

import uuid

from django.http import Http404
from django.utils import timezone

from audit import services as audit
from audit.models import AuditEvent
from organizations.models import Membership
from permissions.services import has_permission
from workspaces.models import Project

from .connectors import CONNECTORS, ColumnInfo, ConnectionFailed, ConnectionParams, TableInfo
from .crypto import decrypt_credential, encrypt_credential
from .models import ConnectedDatabase


class ConnectionPermissionDenied(Exception):
    pass


class ConnectionValidationError(Exception):
    pass


RESOURCE_TYPE_CONNECTED_DATABASE = "databases.connected_database"


def _require(actor, permission_code, organization_id, *, action, resource_id, request_id, scoped=False):
    # Fine-grained ResourceGrant scoping (Phase 7, has_permission's
    # resource= parameter) only applies to read-style operations here —
    # creating/testing/deleting a connection always requires the
    # organization-wide connection.manage permission, matching how schema
    # management is org-wide-only for TenantDatabase (databases/views.py).
    resource = (RESOURCE_TYPE_CONNECTED_DATABASE, resource_id) if scoped and resource_id else None
    if not has_permission(actor, permission_code, organization_id=organization_id, resource=resource):
        audit.record(
            actor=actor,
            organization_id=organization_id,
            action=action,
            resource_type="connected_database",
            resource_id=resource_id,
            request_id=request_id,
            result=AuditEvent.Result.DENIED,
        )
        raise ConnectionPermissionDenied(f"{permission_code} required")


def get_member_connected_database(user, connected_database_id) -> ConnectedDatabase:
    try:
        return ConnectedDatabase.objects.select_related("project__workspace__organization").get(
            id=connected_database_id,
            project__workspace__organization__memberships__user=user,
            project__workspace__organization__memberships__status=Membership.Status.ACTIVE,
        )
    except ConnectedDatabase.DoesNotExist as exc:
        raise Http404 from exc


def _connection_params(connected_database: ConnectedDatabase, *, password: str) -> ConnectionParams:
    return ConnectionParams(
        host=connected_database.host,
        port=connected_database.port,
        database=connected_database.database_name,
        username=connected_database.username,
        password=password,
        sslmode=connected_database.sslmode,
    )


def _connector(engine: str):
    connector = CONNECTORS.get(engine)
    if connector is None:
        raise ConnectionValidationError(f"unsupported engine: {engine!r}")
    return connector


def create_connected_database(
    *,
    actor,
    project: Project,
    name: str,
    engine: str,
    host: str,
    port: int,
    database_name: str,
    username: str,
    password: str,
    sslmode: str,
    request_id: str = "",
) -> ConnectedDatabase:
    org_id = project.organization_id
    _require(
        actor, "connection.manage", org_id, action="connection.create", resource_id="", request_id=request_id
    )

    if not name or len(name) > 200:
        raise ConnectionValidationError("name must be between 1 and 200 characters")

    connector = _connector(engine)
    params = ConnectionParams(
        host=host, port=port, database=database_name, username=username, password=password, sslmode=sslmode
    )
    # Connection tested BEFORE any credential is persisted (ADR-0009
    # Security Considerations) — a failed test means nothing is saved.
    try:
        connector.test_connection(params)
    except ConnectionFailed as exc:
        audit.record(
            actor=actor,
            organization_id=org_id,
            action="connection.create",
            resource_type="connected_database",
            resource_id="",
            request_id=request_id,
            result=AuditEvent.Result.ERROR,
            context={"name": name, "error": str(exc)},
        )
        raise ConnectionValidationError(str(exc)) from exc

    connected_database = ConnectedDatabase.objects.create(
        id=uuid.uuid4(),
        project=project,
        name=name,
        engine=engine,
        host=host,
        port=port,
        database_name=database_name,
        username=username,
        encrypted_password=encrypt_credential(password),
        sslmode=sslmode,
        status=ConnectedDatabase.Status.CONNECTED,
        last_tested_at=timezone.now(),
        created_by=actor,
    )

    audit.record(
        actor=actor,
        organization_id=org_id,
        action="connection.create",
        resource_type="connected_database",
        resource_id=connected_database.id,
        request_id=request_id,
        context={"name": name, "host": host, "database_name": database_name},
    )
    return connected_database


def test_connected_database(
    *, actor, connected_database: ConnectedDatabase, request_id: str = ""
) -> ConnectedDatabase:
    org_id = connected_database.organization_id
    _require(
        actor,
        "connection.manage",
        org_id,
        action="connection.test",
        resource_id=connected_database.id,
        request_id=request_id,
    )

    connector = _connector(connected_database.engine)
    password = decrypt_credential(bytes(connected_database.encrypted_password))
    params = _connection_params(connected_database, password=password)

    try:
        connector.test_connection(params)
    except ConnectionFailed as exc:
        connected_database.status = ConnectedDatabase.Status.UNREACHABLE
        connected_database.last_test_error = str(exc)
    else:
        connected_database.status = ConnectedDatabase.Status.CONNECTED
        connected_database.last_test_error = ""
    connected_database.last_tested_at = timezone.now()
    connected_database.save(update_fields=["status", "last_test_error", "last_tested_at"])

    audit.record(
        actor=actor,
        organization_id=org_id,
        action="connection.test",
        resource_type="connected_database",
        resource_id=connected_database.id,
        request_id=request_id,
        context={"status": connected_database.status},
    )
    return connected_database


def get_connected_database_schema(
    *, actor, connected_database: ConnectedDatabase, request_id: str = ""
) -> list[TableInfo]:
    org_id = connected_database.organization_id
    _require(
        actor,
        "database.read",
        org_id,
        action="connection.schema.read",
        resource_id=connected_database.id,
        request_id=request_id,
        scoped=True,
    )

    connector = _connector(connected_database.engine)
    password = decrypt_credential(bytes(connected_database.encrypted_password))
    params = _connection_params(connected_database, password=password)
    return connector.introspect_schema(params)


def list_connected_database_rows(
    *,
    actor,
    connected_database: ConnectedDatabase,
    table_name: str,
    limit: int,
    offset: int,
    request_id: str = "",
) -> dict:
    org_id = connected_database.organization_id
    _require(
        actor,
        "database.read",
        org_id,
        action="connection.rows.read",
        resource_id=connected_database.id,
        request_id=request_id,
        scoped=True,
    )

    connector = _connector(connected_database.engine)
    password = decrypt_credential(bytes(connected_database.encrypted_password))
    params = _connection_params(connected_database, password=password)

    # Re-introspect and cross-check table_name against the live schema on
    # every call rather than trusting a client-supplied identifier —
    # avoids depending on a possibly-stale cached schema, and means
    # sql.Identifier quoting in connectors.py is defense in depth, not the
    # only check (same two-layer discipline as platform-native tables).
    tables = {t.name: t for t in connector.introspect_schema(params)}
    if table_name not in tables:
        raise ConnectionValidationError(f"unknown table: {table_name}")

    return connector.list_rows(params, table_name, limit=limit, offset=offset)


def delete_connected_database(*, actor, connected_database: ConnectedDatabase, request_id: str = "") -> None:
    org_id = connected_database.organization_id
    _require(
        actor,
        "connection.manage",
        org_id,
        action="connection.delete",
        resource_id=connected_database.id,
        request_id=request_id,
    )

    connected_database_id = connected_database.id
    connected_database.delete()

    audit.record(
        actor=actor,
        organization_id=org_id,
        action="connection.delete",
        resource_type="connected_database",
        resource_id=connected_database_id,
        request_id=request_id,
    )


__all__ = [
    "ColumnInfo",
    "ConnectionPermissionDenied",
    "ConnectionValidationError",
    "TableInfo",
    "create_connected_database",
    "delete_connected_database",
    "get_connected_database_schema",
    "get_member_connected_database",
    "list_connected_database_rows",
    "test_connected_database",
]
