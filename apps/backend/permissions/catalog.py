"""
The permission catalog and system role definitions, straight from
docs/security/PERMISSIONS.md Sections 2 and 3. This module is the single
source of truth `seed_permissions` loads into the database — new
permissions/roles are added here (and in the doc), never invented ad hoc
in a view or migration.
"""

PERMISSIONS = {
    "app_template.read": "Read organization-owned business application templates and versions",
    "app_template.manage": "Create/edit/archive business application templates",
    "app_template.publish": "Publish immutable template versions",
    "app_instance.read": "Read installed business application definitions",
    "app_instance.manage": "Install, rename, archive business applications",
    "app_instance.schema.manage": "Manage installed application model, field, and relationship definitions",
    "app_instance.workflow.approve": (
        "Apply a workflow transition marked as requiring approval, in addition to the ordinary "
        "database.write every record edit already needs"
    ),
    # Business-operation authority (ADR-0017). Granted per installed application (resource type
    # `inventory_operations`, resource id = the AppInstance) or organization-wide through a role. Each one
    # authorizes ONE kind of stock-changing operation and implies none of the others: the right to sell is not
    # the right to receive, adjust or transfer. All are default-deny.
    "inventory.sell": "Record a sale (order, lines, stock taken out, invoice) in an installed application",
    "inventory.receive": (
        "Receive stock into a warehouse (optionally with a purchase order) in an installed application"
    ),
    "inventory.adjust": (
        "Record arbitrary stock movements directly through the record API of an installed application "
        "(there is no adjustment workflow in v1.0)"
    ),
    "inventory.transfer": (
        "Move stock between warehouses (authority defined; no transfer workflow exists in v1.0)"
    ),
    "workspace.manage": "Create Workspaces and Projects within an organization",
    "org_unit.read": (
        "View an organization's structural units (branches, departments, teams, etc.) and their membership"
    ),
    "org_unit.manage": "Create/rename/reparent/delete organizational units",
    "org_unit.membership.manage": "Add/remove users from organizational units",
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
    "application.read": "View an organization's registered Applications and their metadata",
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
    # Hosted websites (ADR-0019).
    "sites.read": "See the organization's hosted websites and their versions",
    "sites.manage": "Upload, publish, switch versions of, take offline and delete hosted websites",
    # The internet gate (ADR-0020 decision 4): held only by the Super Administrator (platform-wide).
    "sites.internet.manage": (
        "Switch the internet gate (Cloudflare Tunnel) on or off and publish or revoke sites on the internet"
    ),
    # The separately deployed Spare Parts application (ADR-0018). Default-deny, granted per installed
    # service application (resource type `service_app`) or organization-wide through a role. The
    # application's own identity provider maps these onto its permission names.
    "spareparts.view": "Open an installed Spare Parts application and read its settings and documents",
    "spareparts.catalogue.read": "Search and read the Spare Parts reference catalogue",
    "spareparts.catalogue.import": "Import catalogue CSV files and offline catalogue packages",
    "spareparts.catalogue.manage": "Manage catalogue sources, verification and image rights",
    "spareparts.products.read": "Read the shop's own products (My Products)",
    "spareparts.products.manage": "Create and change products, prices, photos and part numbers",
    "spareparts.cost.read": "See purchase costs and inventory value",
    "spareparts.inventory.read": "Read stock levels and movements",
    "spareparts.inventory.manage": "Receive, adjust and transfer stock; manage warehouses and locations",
    "spareparts.sales.read": "Read customers, enquiries, quotations, orders and invoices",
    "spareparts.sales.manage": (
        "Manage customers, enquiries, quotations, orders and invoices, and record payments"
    ),
    "spareparts.suppliers.manage": "Create and change suppliers",
    "spareparts.purchasing.read": "Read suppliers and purchase orders",
    "spareparts.purchasing.manage": "Create purchase orders and receive goods against them",
    "spareparts.reports.inventory": "Read inventory reports",
    "spareparts.reports.sales": "Read sales reports",
    "spareparts.reports.financial": "Read financial reports (outstanding invoices, payments)",
    "spareparts.audit.read": "Read the Spare Parts application's own history",
    "spareparts.settings.manage": "Change the Spare Parts application's shop and document settings",
    # The separately deployed IntraForge Pay application (ADR-0018, amended 2026-10-13): QR checkout with
    # simulated IF Credits. Same default-deny model as Spare Parts; Pay maps these onto its own operations.
    "ifpay.view": "Open an installed IntraForge Pay application",
    "ifpay.checkout": "Take QR payments at the counter and read the shop's receipts",
    "ifpay.customers.manage": "Create and deactivate the shop's customer wallets",
    "ifpay.allocations.request": "Request simulated credit for a customer wallet (maker)",
    "ifpay.allocations.approve": "Approve or reject another person's credit request (checker)",
    "ifpay.audit.read": "Read IntraForge Pay's journal, receipts and history",
    # The Pharmacy: the Spare Parts engine in its pharmacy edition (APP_EDITION=pharmacy), its own
    # application type with batches and expiry, the till and the prescription register. Same
    # default-deny model; it has no reference catalogue.
    "pharmacy.view": "Open an installed Pharmacy and read its settings and documents",
    "pharmacy.products.read": "Read the pharmacy's medicines and products",
    "pharmacy.products.manage": "Create and change medicines, prices, barcodes and prescription status",
    "pharmacy.cost.read": "See purchase costs, stock value and profit",
    "pharmacy.inventory.read": "Read stock, batches and expiry dates",
    "pharmacy.inventory.manage": (
        "Receive, adjust, transfer and write off (expired) stock; manage locations"
    ),
    "pharmacy.sales.read": "Read customers, orders, invoices and payments",
    "pharmacy.sales.manage": "Sell at the till, invoice and record payments",
    "pharmacy.suppliers.manage": "Create and change suppliers",
    "pharmacy.purchasing.read": "Read suppliers and purchase orders",
    "pharmacy.purchasing.manage": "Create purchase orders and receive goods (with batch and expiry)",
    "pharmacy.reports.inventory": "Read stock, low-stock and expiry reports",
    "pharmacy.reports.sales": "Read sales reports and the prescription register",
    "pharmacy.reports.financial": (
        "Read the daily sales book, stock value, write-offs and outstanding invoices"
    ),
    "pharmacy.audit.read": "Read the Pharmacy's own history",
    "pharmacy.settings.manage": "Change the Pharmacy's shop and document settings",
}

_ALL = list(PERMISSIONS.keys())
_SPAREPARTS_ALL = [p for p in PERMISSIONS if p.startswith("spareparts.")]
_PHARMACY_ALL = [p for p in PERMISSIONS if p.startswith("pharmacy.")]
# Sells and keeps the stock right; no financial reports or settings.
_PHARMACIST = [
    "pharmacy.view",
    "pharmacy.products.read",
    "pharmacy.products.manage",
    "pharmacy.cost.read",
    "pharmacy.inventory.read",
    "pharmacy.inventory.manage",
    "pharmacy.sales.read",
    "pharmacy.sales.manage",
    "pharmacy.suppliers.manage",
    "pharmacy.purchasing.read",
    "pharmacy.purchasing.manage",
    "pharmacy.reports.inventory",
    "pharmacy.reports.sales",
]
# The till only: sells, sees stock, no costs.
_PHARMACY_CASHIER = [
    "pharmacy.view",
    "pharmacy.products.read",
    "pharmacy.inventory.read",
    "pharmacy.sales.read",
    "pharmacy.sales.manage",
    "pharmacy.reports.sales",
]
# Reads everything the accounts need; changes nothing.
_PHARMACY_ACCOUNTANT = [
    "pharmacy.view",
    "pharmacy.products.read",
    "pharmacy.cost.read",
    "pharmacy.inventory.read",
    "pharmacy.sales.read",
    "pharmacy.purchasing.read",
    "pharmacy.reports.inventory",
    "pharmacy.reports.sales",
    "pharmacy.reports.financial",
    "pharmacy.audit.read",
]
_IFPAY_ALL = [p for p in PERMISSIONS if p.startswith("ifpay.")]
_IFPAY_CASHIER = ["ifpay.view", "ifpay.checkout"]
# Requests and approves, but never their own request: Pay and its database refuse self-approval.
_IFPAY_SUPERVISOR = [
    "ifpay.view",
    "ifpay.customers.manage",
    "ifpay.allocations.request",
    "ifpay.allocations.approve",
    "ifpay.audit.read",
]
# The Spare Parts application's own roles (SALES, INVENTORY, VIEWER; ADMIN = every spareparts.*
# capability), reproduced as capability sets so its behaviour stays exactly what its qualification
# tested. Its OWNER additionally manages people -- in IntraForge that is users.manage.
_SPAREPARTS_SALES = [
    "spareparts.view",
    "spareparts.catalogue.read",
    "spareparts.products.read",
    "spareparts.inventory.read",
    "spareparts.sales.read",
    "spareparts.sales.manage",
    "spareparts.reports.sales",
]
_SPAREPARTS_INVENTORY = [
    "spareparts.view",
    "spareparts.catalogue.read",
    "spareparts.products.read",
    "spareparts.products.manage",
    "spareparts.cost.read",
    "spareparts.inventory.read",
    "spareparts.inventory.manage",
    "spareparts.purchasing.read",
    "spareparts.purchasing.manage",
    "spareparts.reports.inventory",
]
_SPAREPARTS_VIEWER = [
    "spareparts.view",
    "spareparts.catalogue.read",
    "spareparts.products.read",
    "spareparts.inventory.read",
]
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
    # Not the internet gate either: putting a site on the internet is the Super Administrator's
    # decision alone.
    "organization-administrator": (
        "Organization Administrator",
        [p for p in _ALL if p not in ("system.admin", "sites.internet.manage")],
    ),
    "storage-administrator": (
        "Storage Administrator",
        [
            "workspace.manage",
            "storage.read",
            "storage.write",
            "storage.delete",
            "storage.share",
            "storage.manage",
        ],
    ),
    "database-administrator": (
        "Database Administrator",
        [
            "workspace.manage",
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
            "workspace.manage",
            "application.read",
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
            "sites.read",
            "sites.manage",
            # Deliberately NOT environment.production.manage: a Developer
            # can create/manage Development and Staging environments and
            # their secrets, but any mutating operation on a
            # production-tier Environment needs that separate permission
            # too -- only organization-administrator holds it by default.
        ],
    ),
    "editor": ("Editor", [*_STORAGE_RW, *_DATABASE_RW, "dataset.import"]),
    "viewer": (
        "Viewer",
        ["storage.read", "database.read", "environment.read", "application.read", "sites.read"],
    ),
    "auditor": ("Auditor", ["audit.read"]),
    # Guest and Service Account hold no role-wide permissions by design —
    # access is entirely via ResourceGrant (docs/security/PERMISSIONS.md
    # Section 3). Still seeded as roles so they exist to assign.
    "guest": ("Guest", []),
    "service-account": ("Service Account", []),
    # Spare Parts staff roles (ADR-0018). Organization administrators already hold every spareparts.*
    # capability; these let an owner give shop staff exactly the application's own role, and nothing
    # else in IntraForge.
    "spare-parts-manager": ("Spare Parts Manager", _SPAREPARTS_ALL),
    "spare-parts-sales": ("Spare Parts Sales", _SPAREPARTS_SALES),
    "spare-parts-inventory": ("Spare Parts Inventory", _SPAREPARTS_INVENTORY),
    "spare-parts-viewer": ("Spare Parts Viewer", _SPAREPARTS_VIEWER),
    "pay-manager": ("Pay Manager", _IFPAY_ALL),
    "pay-supervisor": ("Pay Supervisor", _IFPAY_SUPERVISOR),
    "pay-cashier": ("Pay Cashier", _IFPAY_CASHIER),
    "pharmacy-manager": ("Pharmacy Manager", _PHARMACY_ALL),
    "pharmacist": ("Pharmacist", _PHARMACIST),
    "pharmacy-cashier": ("Pharmacy Cashier", _PHARMACY_CASHIER),
    "pharmacy-accountant": ("Pharmacy Accountant", _PHARMACY_ACCOUNTANT),
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

# The roles an organization's administrators can give to their own members from the members page,
# in the order the page lists them, each with the one line it shows. Super Administrator is
# platform-wide only and Service Account belongs to applications, so neither is offered there (and
# organizations.views refuses them on that endpoint).
ORGANIZATION_ROLE_SUMMARIES: dict[str, str] = {
    "organization-administrator": "Everything in this organization, including members and roles.",
    "spare-parts-manager": "Everything in Spare Parts, including prices, reports and settings.",
    "spare-parts-sales": "Spare Parts selling: customers, quotations, orders, invoices. No cost prices.",
    "spare-parts-inventory": "Spare Parts stock and purchasing, with cost prices. No selling.",
    "spare-parts-viewer": "Spare Parts look-only: catalogue, products and stock levels.",
    "pay-manager": "Everything in IntraForge Pay: counter, customer wallets, credit requests and approvals.",
    "pay-supervisor": "IntraForge Pay customer wallets, credit requests and approvals, history. No counter.",
    "pay-cashier": "IntraForge Pay counter: show payment QR codes and read the shop's receipts.",
    "pharmacy-manager": "Everything in the Pharmacy, including costs, reports and settings.",
    "pharmacist": "Pharmacy till and stock: sell, receive with batch and expiry, write off expired stock.",
    "pharmacy-cashier": "Pharmacy till only: scan and sell, take payment. No costs.",
    "pharmacy-accountant": (
        "Pharmacy reports for the accounts: daily sales book, stock value, write-offs. Read-only."
    ),
    "editor": "Read and change files and databases.",
    "viewer": "Read files, databases, environments, applications and hosted websites.",
    "storage-administrator": "Manage file storage.",
    "database-administrator": "Manage databases, imports and connections.",
    "developer": "Build applications, manage development environments and publish hosted websites.",
    "auditor": "Read the audit log.",
    "guest": "No access of their own; only what is shared with them.",
}
