"""Control-plane application definitions; never business-record storage."""

import uuid

from django.conf import settings
from django.db import models


def empty_definition():
    return {"schema_version": 1, "models": [], "relationships": []}


class Identity(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    label = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True
        ordering = ["created_at", "id"]


class AppTemplate(Identity):
    organization = models.ForeignKey("organizations.Organization", on_delete=models.CASCADE)
    description = models.TextField(blank=True)
    draft = models.JSONField(default=empty_definition)
    archived = models.BooleanField(default=False)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)

    def __str__(self):
        return self.label


class AppTemplateVersion(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    template = models.ForeignKey(AppTemplate, on_delete=models.PROTECT, related_name="versions")
    number = models.PositiveIntegerField()
    definition = models.JSONField()
    checksum_sha256 = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)

    class Meta:
        ordering = ["number", "id"]
        constraints = [
            models.UniqueConstraint(fields=["template", "number"], name="app_version_number_unique"),
            models.CheckConstraint(condition=models.Q(number__gt=0), name="app_version_number_positive"),
        ]

    def __str__(self):
        return f"{self.template_id} v{self.number}"


class AppInstance(Identity):
    organization = models.ForeignKey("organizations.Organization", on_delete=models.CASCADE)
    project = models.ForeignKey("workspaces.Project", on_delete=models.PROTECT, related_name="app_instances")
    source_version = models.ForeignKey(AppTemplateVersion, on_delete=models.PROTECT)
    archived = models.BooleanField(default=False)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)

    def __str__(self):
        return self.label


class Definition(Identity):
    key = models.CharField(max_length=63)
    source_definition_id = models.UUIDField(null=True, editable=False)
    # Explicit display order among siblings (within a model for fields,
    # within an instance for models/relationships) -- deliberately not part
    # of the runtime plan/fingerprint (runtime_plan.py), since it affects
    # nothing physical. Set from definition-array order at install time and
    # append-position for anything added afterward; reorderable any time,
    # including after provisioning, since it never touches DDL.
    position = models.PositiveIntegerField(default=0)

    class Meta(Identity.Meta):
        abstract = True
        ordering = ["position", "created_at", "id"]


class ModelDefinition(Definition):
    instance = models.ForeignKey(AppInstance, on_delete=models.CASCADE, related_name="models")

    class Meta(Definition.Meta):
        constraints = [
            models.UniqueConstraint(fields=["instance", "key"], name="app_model_key_unique"),
            models.UniqueConstraint(
                fields=["instance", "source_definition_id"], name="app_model_source_unique"
            ),
        ]

    def __str__(self):
        return self.label


class FieldDefinition(Definition):
    class DataType(models.TextChoices):
        TEXT = "text", "Text"
        INTEGER = "integer", "Integer"
        DECIMAL = "decimal", "Decimal"
        BOOLEAN = "boolean", "Boolean"
        DATE = "date", "Date"
        DATETIME = "datetime", "Datetime"

    model = models.ForeignKey(ModelDefinition, on_delete=models.CASCADE, related_name="fields")
    data_type = models.CharField(max_length=20, choices=DataType.choices)
    required = models.BooleanField(default=False)
    # Validated against data_type by definitions.validate_field_default
    # before this is ever set -- never an arbitrary/unvalidated expression.
    default_value = models.JSONField(null=True, blank=True)
    # Post-Phase-3 Integration Enablement: a real Postgres UNIQUE
    # constraint (which is also a real B-tree index) on this field's
    # physical column. `unique` implies indexed lookup for free, so
    # `indexed` below is only meaningful when `unique` is False --
    # runtime_build.py/schema_evolution.py never issue a second, redundant
    # index for a unique column. NULL values never conflict with each
    # other under a Postgres UNIQUE constraint (multiple NULLs are always
    # allowed) -- see schema_evolution.py's set_field_unique docstring for
    # what that means for a `required=False, unique=True` field.
    unique = models.BooleanField(default=False)
    # A plain B-tree index with no uniqueness requirement -- for fields
    # that need fast exact-match lookup (e.g. an external reference id)
    # but can legitimately repeat. Meaningless (and never actually
    # applied) when `unique` is already True.
    indexed = models.BooleanField(default=False)

    class Meta(Definition.Meta):
        constraints = [
            models.UniqueConstraint(fields=["model", "key"], name="app_field_key_unique"),
            models.UniqueConstraint(fields=["model", "source_definition_id"], name="app_field_source_unique"),
            models.CheckConstraint(
                condition=models.Q(
                    data_type__in=["text", "integer", "decimal", "boolean", "date", "datetime"]
                ),
                name="app_field_type_valid",
            ),
        ]

    def __str__(self):
        return self.label


class RelationshipDefinition(Definition):
    instance = models.ForeignKey(AppInstance, on_delete=models.CASCADE, related_name="relationships")
    source_model = models.ForeignKey(ModelDefinition, on_delete=models.PROTECT, related_name="outgoing")
    target_model = models.ForeignKey(ModelDefinition, on_delete=models.PROTECT, related_name="incoming")
    kind = models.CharField(max_length=20, default="many_to_one")
    # Meaningless for kind="many_to_many" -- definitions.RelationshipInput
    # normalizes it to "restrict" on write rather than rejecting it, but it
    # is never actually read for an M:M relationship. A join table's own
    # two FK columns are always physically ON DELETE CASCADE regardless
    # (runtime_build.py/schema_evolution.py) -- "restrict"/"set_null"
    # don't map cleanly onto a pivot row either way.
    deletion_policy = models.CharField(max_length=20, default="restrict")

    class Meta(Definition.Meta):
        constraints = [
            models.UniqueConstraint(fields=["instance", "key"], name="app_relationship_key_unique"),
            models.UniqueConstraint(
                fields=["instance", "source_definition_id"], name="app_relation_source_unique"
            ),
            models.CheckConstraint(
                condition=models.Q(kind__in=["many_to_one", "many_to_many"]), name="app_relation_kind_valid"
            ),
            models.CheckConstraint(
                condition=models.Q(deletion_policy__in=["restrict", "set_null"]),
                name="app_relation_delete_valid",
            ),
        ]

    def __str__(self):
        return self.label


class RuntimeProvision(models.Model):
    """Durable reservation and immutable publication of one runtime per instance."""

    instance = models.OneToOneField(
        AppInstance, primary_key=True, on_delete=models.PROTECT, related_name="runtime_provision"
    )
    plan = models.JSONField()
    fingerprint = models.CharField(max_length=64)
    database = models.OneToOneField(
        "databases.TenantDatabase", null=True, on_delete=models.PROTECT, related_name="app_runtime"
    )
    bindings = models.JSONField(default=dict)
    last_error = models.CharField(max_length=200, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(database__isnull=True, completed_at__isnull=True)
                    | models.Q(database__isnull=False, completed_at__isnull=False)
                ),
                name="app_runtime_completion_consistent",
            )
        ]

    def __str__(self):
        return str(self.instance_id)


class RecordAttachment(models.Model):
    """Links an existing `storage.FileObject` to one record. The record
    itself lives in a raw tenant table this app never models in Django, so
    `record_id` is a plain UUID, not a foreign key -- its only integrity
    guarantee is `records.delete_record` also removing rows here, not a
    database constraint (see that function's own docstring for why this
    can't be a single atomic operation across the control/tenant databases)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    model = models.ForeignKey(ModelDefinition, on_delete=models.CASCADE, related_name="attachments")
    record_id = models.UUIDField()
    file = models.ForeignKey(
        "storage.FileObject", on_delete=models.PROTECT, related_name="app_attachments"
    )
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]
        indexes = [models.Index(fields=["model", "record_id"])]

    def __str__(self):
        return f"{self.record_id} -> {self.file_id}"
