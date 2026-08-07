"""
Ensures Django's migration framework only ever touches the control-plane
("default") database. The "tenant" connection alias exists solely for the
`databases` app's service layer to run validated, schema-scoped DDL/DML
against the tenant PostgreSQL cluster directly (see
docs/architecture/DATA_MODEL.md Section 5) — it is never a Django
migration target, and no Django model is ever routed to write there
through this router.
"""


class TenantConnectionRouter:
    def allow_migrate(self, db, app_label, model_name=None, **hints):
        return db == "default"
