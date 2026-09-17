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
        # Phase 6/7: a reference to an org_units.OrganizationalUnit. Stored
        # physically as a plain UUID column (see runtime_plan.physical_data_type)
        # with NO real Postgres FK -- OrganizationalUnit lives in the control-
        # plane database, this field's value lives in a per-tenant database,
        # and Postgres cannot enforce a cross-database foreign key. Existence
        # and organization-match are validated in records.py at write time
        # instead (the same "validate before it reaches storage" discipline
        # CLAUDE.md requires for anything a real DB constraint can't cover).
        ORG_UNIT_REFERENCE = "org_unit_reference", "Organizational Unit Reference"

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
                    data_type__in=[
                        "text", "integer", "decimal", "boolean", "date", "datetime",
                        "org_unit_reference",
                    ]
                ),
                name="app_field_type_valid",
            ),
        ]

    def __str__(self):
        return self.label


class ConstraintDefinition(Definition):
    """A model-level composite UNIQUE constraint -- Post-Phase-3
    Integration Enablement's general composite-uniqueness capability
    (docs/SPARE_PARTS_INTEGRATION_READINESS.md's "Inventory (Part x
    Warehouse)" row). Membership is `fields` union `relationships`, >=2
    combined, all belonging to this same `model` (enforced by
    definitions.py/instances.py, never by a DB constraint spanning two
    tables). A relationship is only eligible when its own FK column lives
    on this model's table -- i.e. `relationship.source_model == model` and
    `relationship.kind == "many_to_one"`; a `many_to_many` relationship has
    no column on either side (it's a join table) and can never
    participate. Physical enforcement is a real Postgres UNIQUE constraint
    added via databases.services.add_field_set_unique_constraint, keyed by
    this row's own stable `id` -- never by the member set or by `label` --
    so a display-label rename or a member's position/order changing never
    touches DDL or requires reprovisioning.

    NULL semantics: PostgreSQL's UNIQUE constraint treats NULL as
    distinct from every other NULL. If any participating field is
    `required=False`, two records can share NULL in that field (with
    identical values elsewhere) without violating this constraint -- the
    same, already-established platform convention FieldDefinition.unique
    documents above for a single-column unique field, not a new or
    different behavior for the composite case."""

    model = models.ForeignKey(ModelDefinition, on_delete=models.CASCADE, related_name="constraints")
    fields = models.ManyToManyField(FieldDefinition, related_name="unique_constraints")
    # Forward-referenced by string -- RelationshipDefinition is declared
    # later in this file. Also, deliberately, a many_to_one relationship
    # (see the eligibility rule in the class docstring above), never
    # enforced by the DB itself.
    relationships = models.ManyToManyField("RelationshipDefinition", related_name="unique_constraints")

    class Meta(Definition.Meta):
        constraints = [
            models.UniqueConstraint(fields=["model", "key"], name="app_constraint_key_unique"),
            models.UniqueConstraint(
                fields=["model", "source_definition_id"], name="app_constraint_source_unique"
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


class WorkflowDefinition(Definition):
    """Phase 5: a declarative state machine over one of `model`'s own
    existing text fields -- there is no enum type in this platform, so
    `state_field` (validated text-typed, enforced in definitions.py/
    instances.py, never by a DB constraint spanning two tables the way
    FieldDefinition.data_type is) holds whatever value the workflow's
    current state says it should. Like every Definition, `position` is
    excluded from runtime_plan.py's fingerprint -- but unlike every other
    concrete Definition subclass, the *whole* workflow subsystem is
    excluded from it: no migration or provisioning code ever reads these
    tables. It's pure control-plane declaration, governing legal writes to
    an already-physical field, never new schema of its own."""

    model = models.ForeignKey(ModelDefinition, on_delete=models.CASCADE, related_name="workflows")
    state_field = models.ForeignKey(FieldDefinition, on_delete=models.PROTECT, related_name="workflows")

    class Meta(Definition.Meta):
        constraints = [
            models.UniqueConstraint(fields=["model", "key"], name="app_workflow_key_unique"),
            models.UniqueConstraint(
                fields=["model", "source_definition_id"], name="app_workflow_source_unique"
            ),
        ]

    def __str__(self):
        return self.label


class WorkflowState(Definition):
    """A legal value of its workflow's `state_field`. Deliberately no
    separate `value` column -- `key` is already a validated, storage-safe
    identifier (KeyField), and reusing it as the literal text written to
    the record avoids a redundant, driftable second name for the same
    thing."""

    workflow = models.ForeignKey(WorkflowDefinition, on_delete=models.CASCADE, related_name="states")

    class Meta(Definition.Meta):
        constraints = [
            models.UniqueConstraint(fields=["workflow", "key"], name="app_workflow_state_key_unique"),
            models.UniqueConstraint(
                fields=["workflow", "source_definition_id"], name="app_workflow_state_source_unique"
            ),
        ]

    def __str__(self):
        return self.label


class WorkflowTransition(Definition):
    """One legal move from `from_state` (null = valid from any current
    state) to `to_state`. `conditions` is a JSON list of `{field_id,
    operator, value}` (operator in eq/ne/is_null/is_not_null), ANDed --
    deliberately as narrow as databases/rows.py's own exact-match-only
    filtering, not a general expression language. `field_actions` is a
    JSON list of `{field_id, value}` literal writes applied in the exact
    same UPDATE as the state change (databases.rows.update_row_if) --
    literal-only (no calculated values) is what makes a replayed apply
    naturally idempotent: setting a column to a fixed value twice is a
    no-op the second time, unlike e.g. incrementing a counter.
    `requires_approval` gates this specific transition behind the
    `app_instance.workflow.approve` capability, in addition to the
    `database.write` every record write already needs -- see
    docs/implementation/APP_PLATFORM_PHASE5.md for why this is a
    capability gate and not a stateful pending/approve workflow.
    `notify_url`, if set, is validated against
    databases.connectors.assert_host_is_safe at definition time (and
    re-checked immediately before every delivery attempt, since DNS can
    rebind between the two)."""

    workflow = models.ForeignKey(WorkflowDefinition, on_delete=models.CASCADE, related_name="transitions")
    from_state = models.ForeignKey(
        WorkflowState, null=True, on_delete=models.PROTECT, related_name="transitions_from"
    )
    to_state = models.ForeignKey(WorkflowState, on_delete=models.PROTECT, related_name="transitions_to")
    conditions = models.JSONField(default=list, blank=True)
    field_actions = models.JSONField(default=list, blank=True)
    requires_approval = models.BooleanField(default=False)
    notify_url = models.TextField(blank=True)

    class Meta(Definition.Meta):
        constraints = [
            models.UniqueConstraint(fields=["workflow", "key"], name="app_workflow_transition_key_unique"),
            models.UniqueConstraint(
                fields=["workflow", "source_definition_id"], name="app_workflow_transition_source_unique"
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


class WorkflowTransitionAttempt(models.Model):
    """A durable receipt for one "apply this transition to this record"
    request -- operational state, not declarative metadata (deliberately
    not a Definition subclass). Mirrors RuntimeProvision/exports.RestoreJob's
    own reserve-then-execute shape: `completed_at` is the single durable
    "already fully applied" marker a replayed request short-circuits on
    (workflows.py's apply_transition checks it before redoing any work),
    and `idempotency_key` + `request_fingerprint` give the exact same
    actor-opts-in idempotency RestoreJob's own docstring describes -- a
    repeat with the same key AND the same fingerprint returns the original
    outcome; the same key with a different fingerprint is a genuine
    conflicting request, rejected rather than silently reinterpreted.
    `record_id` is a bare UUID, not a FK, the same cross-database
    precedent RecordAttachment.record_id already establishes -- the record
    itself lives in a raw tenant table this app never models in Django."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    transition = models.ForeignKey(WorkflowTransition, on_delete=models.PROTECT, related_name="attempts")
    record_id = models.UUIDField()
    idempotency_key = models.UUIDField(null=True)
    request_fingerprint = models.CharField(max_length=64)
    state_before = models.CharField(max_length=63, blank=True)
    state_after = models.CharField(max_length=63, blank=True)
    completed_at = models.DateTimeField(null=True)
    last_error = models.CharField(max_length=200, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["record_id", "idempotency_key"],
                condition=models.Q(idempotency_key__isnull=False),
                name="app_workflow_attempt_idempotency_unique",
            )
        ]
        indexes = [models.Index(fields=["transition", "record_id"])]

    def __str__(self):
        return str(self.id)


class WorkflowNotificationDelivery(models.Model):
    """A "send at most once" outbox row for one transition attempt's
    notification -- one row per attempt that had a `notify_url` at the
    moment it completed. `url` is a denormalized copy taken at that
    moment, not a live read of the transition's current `notify_url`, so
    editing a transition's notification target later never rewrites
    history. `delivered_at` is the exact same kind of durable completion
    marker WorkflowTransitionAttempt.completed_at is -- the Celery
    delivery task (app_platform/tasks.py) checks it before ever dialing
    out, giving replay-safety for the one genuinely non-idempotent effect
    in this whole subsystem (an HTTP POST, unlike a literal field write,
    isn't idempotent to the receiver by construction)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    attempt = models.ForeignKey(
        WorkflowTransitionAttempt, on_delete=models.CASCADE, related_name="deliveries"
    )
    url = models.TextField()
    delivered_at = models.DateTimeField(null=True)
    attempt_count = models.PositiveIntegerField(default=0)
    last_error = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]

    def __str__(self):
        return f"{self.attempt_id} -> {self.url}"


class WebhookDelivery(models.Model):
    """Phase 10: a durable "at most once" outbox row for one
    `environments.EnvironmentWebhook` delivery of an App Platform event
    (`app_platform/webhooks.py`) -- the "reliable webhooks" this phase's
    own exit bar names, and the concrete mechanism `docs/
    EXTERNAL_APP_API_CONTRACT.md` previously flagged outright as **NOT
    YET IMPLEMENTED** ("Webhooks or any push/event-notification mechanism
    out of App Platform toward an external application").

    Deliberately a separate model from `WorkflowNotificationDelivery`,
    not a widening of it: that one is exactly one `notify_url` per
    transition, denormalized, unsigned, and unchanged since Phase 5. This
    is N subscribed `EnvironmentWebhook` rows per event (record CRUD or a
    workflow transition), HMAC-signed with that webhook's own encrypted
    signing secret, and only ever fires when the emitting instance's
    runtime database is bound to an Environment -- see `webhooks.
    dispatch_event`'s own docstring. `payload` is a snapshot taken at
    dispatch time, the same "never a live re-read" reasoning
    `WorkflowNotificationDelivery.url` already documents. `instance` is
    kept alongside `webhook` (rather than resolved through it) purely for
    cheap history queries -- `webhook.environment_id` already implies
    which Environment received a delivery, but not which AppInstance
    caused it."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    webhook = models.ForeignKey(
        "environments.EnvironmentWebhook", on_delete=models.CASCADE, related_name="app_platform_deliveries"
    )
    instance = models.ForeignKey(AppInstance, on_delete=models.CASCADE, related_name="webhook_deliveries")
    event_type = models.CharField(max_length=100)
    payload = models.JSONField()
    delivered_at = models.DateTimeField(null=True)
    attempt_count = models.PositiveIntegerField(default=0)
    last_error = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]

    def __str__(self):
        return f"{self.event_type} -> {self.webhook_id}"


class UnitScopedGrant(models.Model):
    """Phase 7 Step 3 ("unit scope"): grants one user read/write access to
    a model's records, restricted to records whose org_unit_reference
    field equals `unit`. Real FKs to both `model` and `unit` -- unlike
    org_unit_reference itself, both rows here live in the control-plane
    database (this app and org_units), so there's no cross-database
    problem to work around.

    Deliberately a dedicated model rather than forcing this into
    permissions.ResourceGrant's single (resource_type, resource_id) shape
    (which can't express a two-key "this model AND this unit" scope
    without an opaque derived id no admin UI could ever display
    meaningfully) or sharing.ShareGrant (built for exactly one resource
    id per share, same problem). Enforcement still runs entirely through
    `level` mapping onto real permission codes
    (`unit_scope.LEVEL_PERMISSIONS`) checked in `records.py` -- this is a
    grant *source*, the same relationship ShareGrant already has to
    ResourceGrant, never a second authorization mechanism (ADR-0008).

    Requires the target model to have exactly one org_unit_reference field
    (validated at grant-creation time, not here) -- two such fields on one
    model would make "restricted to unit X" ambiguous about which field it
    means; not supported in this pass."""

    class Level(models.TextChoices):
        READ = "read", "Read"
        WRITE = "write", "Write"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    model = models.ForeignKey(ModelDefinition, on_delete=models.CASCADE, related_name="unit_scoped_grants")
    unit = models.ForeignKey(
        "org_units.OrganizationalUnit", on_delete=models.CASCADE, related_name="app_model_grants"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="unit_scoped_grants"
    )
    level = models.CharField(max_length=10, choices=Level.choices)
    granted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="unit_scoped_grants_created",
    )
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["model", "unit", "user"], name="app_unit_scoped_grant_unique"),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} -> {self.level} on {self.model_id}/{self.unit_id}"


class AppInstanceUpgrade(models.Model):
    """Phase 9: a durable receipt for one `upgrades.apply_upgrade` call --
    operational history, not declarative metadata (deliberately not a
    `Definition` subclass, the same distinction `WorkflowTransitionAttempt`
    already draws above). `summary` is the full three-way diff this call
    computed (see `upgrades.py`): every item added or label-synced, and
    every item that needed a human because it conflicted with a local
    customization, changed something a live migration can't safely apply,
    or was removed upstream -- recorded even when it wasn't applied, never
    silently dropped. There is nothing here to *resume*: `apply_upgrade`
    runs entirely inside one control-plane transaction (plus one nested
    tenant transaction for any real DDL), so a crash mid-call leaves
    nothing partially applied -- Postgres's own transactional DDL is the
    recovery mechanism, matching every other schema_evolution.py caller
    (RuntimeProvision/WorkflowTransitionAttempt need their own resumable-
    job machinery only because they span an async Celery task; this
    doesn't)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    instance = models.ForeignKey(AppInstance, on_delete=models.CASCADE, related_name="upgrades")
    from_version = models.ForeignKey(AppTemplateVersion, on_delete=models.PROTECT, related_name="+")
    to_version = models.ForeignKey(AppTemplateVersion, on_delete=models.PROTECT, related_name="+")
    summary = models.JSONField()
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "id"]

    def __str__(self):
        return f"{self.instance_id}: v{self.from_version.number} -> v{self.to_version.number}"
