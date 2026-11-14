# Chapter 2 — The backend — The service-layer pattern

Topic for: software engineers. Source: IntraForge Engineering Handbook, Chapter 2 — The backend.

Business logic lives in services, never in views or serializers. A service:

1. **Finds the resource inside the caller's organization** (`get_member_bucket`, `get_member_table`, …). A resource of
   another organization raises `Http404` — the caller cannot tell whether it exists.
2. **Checks the capability** through `permissions.services.has_permission(user, code, organization_id, resource)`.
   Effective permission = a role held in that organization (or platform-wide) **or** a non-expired resource grant on
   that exact resource.
3. **Does the work in a transaction.** DDL on the tenant database runs first; if writing the catalog row then fails, a
   compensating DDL undoes it (`databases.services._write_catalog`).
4. **Records an audit event** with `audit.services.record(actor=…, organization_id=…, action=…, result=…)`, including
   a `denied` event when the permission check refuses.

A shortened real example (`databases/services.py`):

```python
def create_tenant_database(*, actor, project, name, request_id=""):
    org_id = project.organization_id
    _require(actor, "database.create", org_id, action="database.create",
             resource_type="tenant_database", resource_id="", request_id=request_id)  # audits "denied" too
    tenant_db = TenantDatabase(project=project, name=name, created_by=actor)
    tenant_db.schema_name = f"db_{tenant_db.id.hex}"
    _execute_tenant_ddl(sql.SQL("CREATE SCHEMA {s}").format(s=sql.Identifier(tenant_db.schema_name)))
    _write_catalog(tenant_db.save,
                   compensating_ddl=sql.SQL("DROP SCHEMA {s} CASCADE").format(s=sql.Identifier(tenant_db.schema_name)))
    audit.record(actor=actor, organization_id=org_id, action="database.create",
                 resource_type="tenant_database", resource_id=tenant_db.id, context={"name": name})
    return tenant_db
```

The view only translates: serializer in, service call, `Response` out, and maps service exceptions to status codes.
