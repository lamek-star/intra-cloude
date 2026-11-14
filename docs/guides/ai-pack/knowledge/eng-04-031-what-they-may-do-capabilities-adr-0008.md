# Chapter 4 — Security and permissions — What they may do — capabilities (ADR-0008)

Topic for: software engineers. Source: IntraForge Engineering Handbook, Chapter 4 — Security and permissions.

A **capability** is a permission string. Code never branches on a role name; it calls:

```python
from permissions.services import has_permission
has_permission(user, "inventory.sell", organization_id=org.id, resource=("app_instance", instance.id))
```

Effective permission = a **role** held in that organization (or platform-wide, for the Super Administrator) whose
capability set includes the code, **or** a non-expired **ResourceGrant** for that exact capability on that exact
resource. Sharing (`ShareGrant`) compiles down to ResourceGrants — there is no second enforcement path.

Capability families (all in `permissions/catalog.py`, the single source of truth that `seed_permissions` loads):

| Family | Examples |
|---|---|
| Platform | `system.admin`, `backup.manage`, `users.manage`, `permissions.manage`, `audit.read`, `sites.internet.manage` |
| Workspaces, storage | `workspace.manage`, `storage.read/write/delete/share/manage`, `sharing.manage` |
| Databases, data | `database.create/read/write/delete/schema.manage`, `dataset.import/export/analyze`, `connection.manage` |
| Integration | `application.create/read/credentials.manage`, `environment.read/manage/secrets.manage/production.manage`, `export.manage` |
| App platform | `app_template.read/manage/publish`, `app_instance.read/manage/schema.manage/workflow.approve`, `org_unit.*` |
| Stock (ADR-0017) | `inventory.sell`, `inventory.receive`, `inventory.adjust`, `inventory.transfer` — separate, none implies another |
| Service apps | `ifpay.*`, `spareparts.*`, `pharmacy.*` |
| Shop features | `movies.read/sell/manage`, `sites.read/manage` |

System roles are named bundles: Super Administrator (everything, platform-wide), Organization Administrator, Storage
Administrator, Database Administrator, Developer, Editor, Viewer, Auditor, Guest, Service Account, and the app roles
(Spare Parts Manager/Sales/Inventory/Viewer, Pay Manager/Supervisor/Cashier, Pharmacy Manager/Pharmacist/Cashier/
Accountant). **Adding a capability:** add it to `catalog.py` and to `PERMISSIONS.md`, re-run `seed_permissions`, check
it in the service, and test both the allowed and the denied path.
