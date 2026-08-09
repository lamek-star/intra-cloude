import uuid

from django.conf import settings
from django.db import models


class TenantDatabase(models.Model):
    """A logical database the platform manages for a Project. Maps 1:1 to
    one physical PostgreSQL schema in the tenant cluster
    (docs/architecture/adr/0005-tenant-database-isolation-strategy.md).
    `schema_name` is server-generated from this row's own UUID — never
    derived from user input (Section 5/8 of the master prompt)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        "workspaces.Project", on_delete=models.CASCADE, related_name="tenant_databases"
    )
    name = models.CharField(max_length=200)
    schema_name = models.CharField(max_length=63, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="tenant_databases_created"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["project", "name"], name="unique_tenant_database_name_per_project"
            ),
        ]
        ordering = ["name"]

    def __str__(self):
        return self.name

    @property
    def organization_id(self):
        return self.project.workspace.organization_id


class DBTable(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_database = models.ForeignKey(TenantDatabase, on_delete=models.CASCADE, related_name="tables")
    name = models.CharField(max_length=63)  # validated as a Postgres identifier before use
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="tables_created"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_database", "name"], name="unique_table_name_per_database"
            ),
        ]
        ordering = ["name"]

    def __str__(self):
        return self.name

    @property
    def organization_id(self):
        return self.tenant_database.organization_id


class DBColumn(models.Model):
    # Deliberately not every PostgreSQL type — a curated, safe subset per
    # Section 9 of the master prompt.
    class DataType(models.TextChoices):
        TEXT = "text", "Text"
        VARCHAR = "varchar", "Varchar"
        INTEGER = "integer", "Integer"
        BIGINT = "bigint", "Big Integer"
        DECIMAL = "decimal", "Decimal"
        BOOLEAN = "boolean", "Boolean"
        DATE = "date", "Date"
        DATETIME = "datetime", "Datetime"
        UUID = "uuid", "UUID"
        JSON = "json", "JSON"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    table = models.ForeignKey(DBTable, on_delete=models.CASCADE, related_name="columns")
    name = models.CharField(max_length=63)
    data_type = models.CharField(max_length=20, choices=DataType.choices)
    max_length = models.PositiveIntegerField(null=True, blank=True)  # varchar only
    precision = models.PositiveIntegerField(null=True, blank=True)  # decimal only
    scale = models.PositiveIntegerField(null=True, blank=True)  # decimal only
    is_primary_key = models.BooleanField(default=False)
    is_nullable = models.BooleanField(default=True)
    is_unique = models.BooleanField(default=False)
    # Validated against data_type and safely embedded via psycopg.sql.Literal
    # before ever reaching DDL (databases/ddl.py) — an "approved safe set"
    # per Section 9, not arbitrary unvalidated SQL text.
    default_value = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["table", "name"], name="unique_column_name_per_table"),
        ]
        ordering = ["name"]

    def __str__(self):
        return f"{self.table}.{self.name}"

    @property
    def organization_id(self):
        return self.table.organization_id


class DBForeignKey(models.Model):
    class OnDelete(models.TextChoices):
        CASCADE = "cascade", "Cascade"
        RESTRICT = "restrict", "Restrict"
        SET_NULL = "set_null", "Set Null"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    column = models.OneToOneField(DBColumn, on_delete=models.CASCADE, related_name="foreign_key")
    references_table = models.ForeignKey(DBTable, on_delete=models.CASCADE, related_name="referenced_by")
    references_column = models.ForeignKey(
        DBColumn, on_delete=models.CASCADE, related_name="referenced_by_fk"
    )
    on_delete = models.CharField(max_length=20, choices=OnDelete.choices, default=OnDelete.RESTRICT)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.column} -> {self.references_table}.{self.references_column}"


class DBIndex(models.Model):
    """Created automatically alongside unique columns and primary keys —
    not (yet) a user-facing "create an arbitrary index" feature; still a
    real catalog entry mirroring what actually exists in the tenant
    schema, per docs/architecture/DATA_MODEL.md Section 3.5."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    table = models.ForeignKey(DBTable, on_delete=models.CASCADE, related_name="indexes")
    name = models.CharField(max_length=63, unique=True, editable=False)
    columns = models.ManyToManyField(DBColumn, related_name="indexes")
    is_unique = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
