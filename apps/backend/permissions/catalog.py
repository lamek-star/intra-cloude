"""
The permission catalog and system role definitions, straight from
docs/security/PERMISSIONS.md Sections 2 and 3. This module is the single
source of truth `seed_permissions` loads into the database — new
permissions/roles are added here (and in the doc), never invented ad hoc
in a view or migration.
"""

PERMISSIONS = {
    "storage.read": "View/download files and folders",
    "storage.write": "Upload, create folders, rename, move",
    "storage.delete": "Delete/restore files and folders",
    "storage.share": "Create share grants for storage resources",
    "storage.manage": "Bucket-level configuration (quotas, versioning, retention)",
    "database.create": "Create a new TenantDatabase within a Project",
    "database.read": "Query/browse data in a database the actor can reach",
    "database.write": "Insert/update/delete rows",
    "database.schema.manage": "Create/alter tables, columns, constraints, relationships",
    "database.delete": "Drop a database/schema",
    "dataset.import": "Run CSV import jobs",
    "dataset.export": "Export data (CSV, API)",
    "dataset.analyze": "Create/edit saved analytics dashboards (ad-hoc analysis only needs database.read)",
    "application.create": "Register a new Application",
    "application.credentials.manage": "Issue/rotate/revoke Application credentials",
    "permissions.manage": "Create/edit Roles, assign Roles, create Resource Grants",
    "users.manage": "Invite/remove/suspend users, manage Team membership",
    "audit.read": "View audit logs",
    "backup.manage": "Trigger/inspect backup and restore operations",
    "export.manage": "Create and download portable (.icp) exports of an organization",
    "connection.manage": "Create/edit ConnectedDatabase configurations",
    "sharing.manage": "Create/revoke ShareGrants (internal/external)",
    "system.admin": "Platform-wide administrative operations (Super Administrator only)",
    "environment.read": "View an Application's Environments and their non-secret configuration/status",
    "environment.manage": "Create/update/clone/disable/delete Environments, variables, and webhooks",
    "environment.secrets.manage": (
        "Create/rotate/delete Environment secrets and issue/revoke environment-scoped credentials"
    ),
    "environment.production.manage": (
        "Required in addition to environment.manage/environment.secrets.manage for any mutating "
        "operation on a production-tier Environment"
    ),
}

_ALL = list(PERMISSIONS.keys())
_STORAGE_RW = ["storage.read", "storage.write"]
_DATABASE_RW = ["database.read", "database.write"]

# slug -> (name, permission codes). `organization=None` / is_system=True for
# all of these — seeded once, shared by every organization, never deleted
# or renamed (docs/security/PERMISSIONS.md Section 3).
SYSTEM_ROLES: dict[str, tuple[str, list[str]]] = {
    "super-administrator": ("Super Administrator", _ALL),
    # Full authority within their own org — everything except system.admin,
    # which is platform-wide-only. docs/security/PERMISSIONS.md Section 3
    # originally listed only a "representative" subset here (storage.manage
    # but not storage.read/write, etc.); actually exercising the org-admin
    # role in Phase 3 (an admin couldn't touch their own org's files)
    # showed that reading as an exhaustive list breaks the "Org owner/IT
    # admin" intent, so this is now the full grant.
    "organization-administrator": ("Organization Administrator", [p for p in _ALL if p != "system.admin"]),
    "storage-administrator": (
        "Storage Administrator",
        ["storage.read", "storage.write", "storage.delete", "storage.share", "storage.manage"],
    ),
    "database-administrator": (
        "Database Administrator",
        [
            "database.create",
            "database.read",
            "database.write",
            "database.schema.manage",
            "database.delete",
            "dataset.import",
            "dataset.export",
            "dataset.analyze",
            "connection.manage",
        ],
    ),
    "developer": (
        "Developer",
        [
            "application.create",
            "application.credentials.manage",
            "database.read",
            "database.write",
            "dataset.import",
            "dataset.export",
            "dataset.analyze",
            "environment.read",
            "environment.manage",
            "environment.secrets.manage",
            # Deliberately NOT environment.production.manage: a Developer
            # can create/manage Development and Staging environments and
            # their secrets, but any mutating operation on a
            # production-tier Environment needs that separate permission
            # too -- only organization-administrator holds it by default.
        ],
    ),
    "editor": ("Editor", [*_STORAGE_RW, *_DATABASE_RW, "dataset.import"]),
    "viewer": ("Viewer", ["storage.read", "database.read", "environment.read"]),
    "auditor": ("Auditor", ["audit.read"]),
    # Guest and Service Account hold no role-wide permissions by design —
    # access is entirely via ResourceGrant (docs/security/PERMISSIONS.md
    # Section 3). Still seeded as roles so they exist to assign.
    "guest": ("Guest", []),
    "service-account": ("Service Account", []),
}

# Only this role may be assigned with organization=None (platform-wide) —
# enforced in permissions.services.assign_role.
PLATFORM_WIDE_ROLE_SLUG = "super-administrator"

# A role granting any of these is "administrative" for Phase 10's MFA
# enforcement (docs/architecture/ROADMAP.md Phase 10): when
# FEATURE_INTERNET_GATEWAY_ENABLED is on, assigning a role that includes
# one of these permissions requires the target user to already have MFA
# enabled (permissions.services.assign_role). Not enforced for
# already-existing assignments made before the gateway was enabled —
# see ROADMAP.md Phase 10 for why that's a deliberate, documented scope
# limit, not an oversight.
ADMIN_PERMISSION_CODES = {"permissions.manage", "system.admin"}
