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
    "application.create": "Register a new Application",
    "application.credentials.manage": "Issue/rotate/revoke Application credentials",
    "permissions.manage": "Create/edit Roles, assign Roles, create Resource Grants",
    "users.manage": "Invite/remove/suspend users, manage Team membership",
    "audit.read": "View audit logs",
    "backup.manage": "Trigger/inspect backup and restore operations",
    "connection.manage": "Create/edit ConnectedDatabase configurations",
    "sharing.manage": "Create/revoke ShareGrants (internal/external)",
    "system.admin": "Platform-wide administrative operations (Super Administrator only)",
}

_ALL = list(PERMISSIONS.keys())
_STORAGE_RW = ["storage.read", "storage.write"]
_DATABASE_RW = ["database.read", "database.write"]

# slug -> (name, permission codes). `organization=None` / is_system=True for
# all of these — seeded once, shared by every organization, never deleted
# or renamed (docs/security/PERMISSIONS.md Section 3).
SYSTEM_ROLES: dict[str, tuple[str, list[str]]] = {
    "super-administrator": ("Super Administrator", _ALL),
    "organization-administrator": (
        "Organization Administrator",
        [
            "users.manage",
            "permissions.manage",
            "storage.manage",
            "database.create",
            "database.schema.manage",
            "backup.manage",
            "audit.read",
            "connection.manage",
            "sharing.manage",
        ],
    ),
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
        ],
    ),
    "editor": ("Editor", [*_STORAGE_RW, *_DATABASE_RW, "dataset.import"]),
    "viewer": ("Viewer", ["storage.read", "database.read"]),
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
