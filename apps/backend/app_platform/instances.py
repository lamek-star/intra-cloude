"""Independent installation and serialized metadata edits; no tenant DDL."""

from django.db import transaction
from rest_framework import serializers

from audit import services as audit

from . import schema_evolution
from .access import check, get_owned, require_manage
from .definitions import (
    ConstraintInput,
    FieldInput,
    ModelInput,
    RelationshipInput,
    StrictSerializer,
    validate_definition,
    validate_field_default,
)
from .models import (
    AppInstance,
    AppTemplateVersion,
    ConstraintDefinition,
    FieldDefinition,
    ModelDefinition,
    RelationshipDefinition,
    RuntimeProvision,
)


class InstallInput(StrictSerializer):
    template_version = serializers.UUIDField()
    label = serializers.CharField(max_length=200)  # type: ignore[assignment]  # DRF declarative field, removed by its metaclass


class InstanceInput(StrictSerializer):
    label = serializers.CharField(max_length=200, required=False)  # type: ignore[assignment]  # DRF declarative field, removed by its metaclass
    archived = serializers.BooleanField(required=False)


class LabelInput(StrictSerializer):
    label = serializers.CharField(max_length=200, required=False)  # type: ignore[assignment]  # DRF declarative field, removed by its metaclass
    # Reordering is never structural (see Definition.position's docstring
    # in models.py) -- allowed on every definition kind, any time.
    position = serializers.IntegerField(min_value=0, required=False)


class FieldPatch(LabelInput):
    required = serializers.BooleanField(required=False)  # type: ignore[assignment]  # DRF declarative field, removed by its metaclass
    default_value = serializers.JSONField(required=False, allow_null=True)


class RelationshipPatch(LabelInput):
    deletion_policy = serializers.ChoiceField(choices=["restrict", "set_null"], required=False)


def install(actor, project, data):
    org_id = project.workspace.organization_id
    check(actor, org_id, "app_instance.manage")
    payload = validated(InstallInput, data)
    version = get_owned(AppTemplateVersion, payload["template_version"], actor, "template__organization")
    if version.template.organization_id != org_id:
        raise serializers.ValidationError("Template and project must belong to the same organization.")
    check(actor, org_id, "app_template.read", ("app_template", version.template_id))
    with transaction.atomic():
        # Serialize against template archive/publication without ever changing the version.
        template = type(version.template).objects.select_for_update().get(pk=version.template_id)
        if template.archived:
            raise serializers.ValidationError("Archived templates cannot be installed.")
        definition = validate_definition(version.definition)
        instance = AppInstance.objects.create(
            organization_id=org_id,
            project=project,
            source_version=version,
            label=payload["label"],
            created_by=actor,
        )
        models = {}
        for model_position, item in enumerate(definition["models"]):
            model = ModelDefinition.objects.create(
                instance=instance,
                key=item["key"],
                label=item["label"],
                source_definition_id=item["id"],
                position=model_position,
            )
            models[item["id"]] = model
            fields = {}
            for field_position, field in enumerate(item["fields"]):
                values = {key: value for key, value in field.items() if key != "id"}
                fields[field["id"]] = FieldDefinition.objects.create(
                    model=model, source_definition_id=field["id"], position=field_position, **values
                )
            for constraint_position, constraint in enumerate(item.get("constraints", [])):
                created = ConstraintDefinition.objects.create(
                    model=model,
                    key=constraint["key"],
                    label=constraint["label"],
                    source_definition_id=constraint["id"],
                    position=constraint_position,
                )
                created.fields.set([fields[field_id] for field_id in constraint["field_ids"]])
        for relation_position, item in enumerate(definition["relationships"]):
            RelationshipDefinition.objects.create(
                instance=instance,
                source_definition_id=item["id"],
                key=item["key"],
                label=item["label"],
                source_model=models[item["source_model"]],
                target_model=models[item["target_model"]],
                kind=item["kind"],
                deletion_policy=item["deletion_policy"],
                position=relation_position,
            )
        event(actor, instance, "install", instance.id)
    return instance


def validated(serializer_type, data):
    serializer = serializer_type(data=data)
    serializer.is_valid(raise_exception=True)
    return serializer.validated_data


def _lock_instance(instance):
    instance = AppInstance.objects.select_for_update().get(pk=instance.pk)
    if instance.archived:
        raise serializers.ValidationError("Archived instance definitions cannot be changed.")
    return instance


def lock_active(instance, *, structural=True):
    instance = _lock_instance(instance)
    if structural and RuntimeProvision.objects.filter(instance=instance).exists():
        raise serializers.ValidationError("Runtime schema is reserved; structural edits require a migration.")
    return instance


def add_model(actor, instance, data):
    require_manage(actor, instance)
    values = validated(ModelInput, data)
    with transaction.atomic():
        instance = _lock_instance(instance)
        receipt = schema_evolution.ready_receipt(instance)
        if receipt is not None:
            schema_evolution.require_addition(actor, instance)
            schema_evolution.mark_addition_transaction()
        if instance.models.count() >= 100:
            raise serializers.ValidationError("Model limit reached.")
        unique_key(instance.models, values["key"])
        model = ModelDefinition.objects.create(
            instance=instance, position=instance.models.count(), **values
        )
        if receipt is not None:
            with transaction.atomic(using="tenant"):
                schema_evolution.add_model_to_runtime(receipt, model, actor)
        event(actor, instance, "model.create", model.id, live=receipt is not None)
    return model


def add_field(actor, model, data):
    instance = model.instance
    require_manage(actor, instance)
    values = validated(FieldInput, data)
    with transaction.atomic():
        _lock_instance(instance)
        receipt = schema_evolution.ready_receipt(instance)
        if receipt is not None:
            schema_evolution.require_addition(actor, instance)
            schema_evolution.mark_addition_transaction()
        if model.fields.count() >= 100:
            raise serializers.ValidationError("Field limit reached.")
        unique_key(model.fields, values["key"])
        field = FieldDefinition.objects.create(model=model, position=model.fields.count(), **values)
        if receipt is not None:
            with transaction.atomic(using="tenant"):
                schema_evolution.add_field_to_runtime(receipt, field, actor)
        event(actor, instance, "field.create", field.id, live=receipt is not None)
    return field


def add_relationship(actor, instance, data):
    require_manage(actor, instance)
    values = validated(RelationshipInput, data)
    with transaction.atomic():
        instance = _lock_instance(instance)
        receipt = schema_evolution.ready_receipt(instance)
        if receipt is not None:
            schema_evolution.require_addition(actor, instance)
            schema_evolution.mark_addition_transaction()
        if instance.relationships.count() >= 500:
            raise serializers.ValidationError("Relationship limit reached.")
        unique_key(instance.relationships, values["key"])
        for key in ("source_model", "target_model"):
            try:
                values[key] = instance.models.get(pk=values[key])
            except ModelDefinition.DoesNotExist as exc:
                raise serializers.ValidationError(
                    "Relationship models must belong to this instance."
                ) from exc
        relation = RelationshipDefinition.objects.create(
            instance=instance, position=instance.relationships.count(), **values
        )
        if receipt is not None:
            with transaction.atomic(using="tenant"):
                schema_evolution.add_relationship_to_runtime(receipt, relation, actor)
        event(actor, instance, "relationship.create", relation.id, live=receipt is not None)
    return relation


def add_constraint(actor, model, data):
    """Declares a composite UNIQUE constraint over >=2 of `model`'s own
    fields -- pre-provision this is a pure metadata write (nothing
    physical exists yet to constrain); once provisioned it needs the
    exact same bar as any other live schema change
    (schema_evolution.require_addition) and runs real DDL via
    schema_evolution.add_constraint_to_runtime against the model's
    already-materialized table, populated or not (a genuine duplicate
    combination fails safely -- see that function's own docstring)."""
    instance = model.instance
    require_manage(actor, instance)
    values = validated(ConstraintInput, data)
    with transaction.atomic():
        _lock_instance(instance)
        receipt = schema_evolution.ready_receipt(instance)
        if receipt is not None:
            schema_evolution.require_addition(actor, instance)
            schema_evolution.mark_addition_transaction()
        if model.constraints.count() >= 20:
            raise serializers.ValidationError("Constraint limit reached.")
        unique_key(model.constraints, values["key"])
        fields = []
        for field_id in values["field_ids"]:
            try:
                fields.append(model.fields.get(pk=field_id))
            except FieldDefinition.DoesNotExist as exc:
                raise serializers.ValidationError(
                    "Constraint fields must belong to this model."
                ) from exc
        constraint = ConstraintDefinition.objects.create(
            model=model, key=values["key"], label=values["label"], position=model.constraints.count()
        )
        constraint.fields.set(fields)
        if receipt is not None:
            with transaction.atomic(using="tenant"):
                schema_evolution.add_constraint_to_runtime(receipt, constraint, actor)
        event(actor, instance, "constraint.create", constraint.id, live=receipt is not None)
    return constraint


def mark_field_unique(actor, field):
    """Retrofits uniqueness onto an EXISTING field -- Post-Phase-3
    Integration Enablement, Part 3. Pre-provision this is a pure metadata
    edit (nothing physical exists yet to constrain); once provisioned it
    needs the exact same bar as any other live schema change
    (schema_evolution.require_addition: org-wide database.schema.manage,
    never just a resource-scoped app grant) and runs real DDL against the
    field's already-materialized column. A dedicated action rather than a
    new case in update_definition's generic PATCH -- entangling a
    sometimes-safe-when-provisioned attribute with that endpoint's
    existing "anything beyond label/position is structural, full stop"
    rule would make BOTH harder to reason about."""
    instance = field.model.instance
    require_manage(actor, instance)
    with transaction.atomic():
        _lock_instance(instance)
        receipt = schema_evolution.ready_receipt(instance)
        field = FieldDefinition.objects.select_for_update().get(pk=field.pk)
        if receipt is not None:
            schema_evolution.require_addition(actor, instance)
            schema_evolution.mark_addition_transaction()
            with transaction.atomic(using="tenant"):
                schema_evolution.set_field_unique(receipt, field, actor)
        elif not field.unique:
            field.unique = True
            field.save(update_fields=["unique"])
        event(actor, instance, "field.unique", field.id, live=receipt is not None)
    return field


def mark_field_indexed(actor, field):
    """See mark_field_unique above -- identical reasoning, no uniqueness
    constraint so nothing to reject once provisioned."""
    instance = field.model.instance
    require_manage(actor, instance)
    with transaction.atomic():
        _lock_instance(instance)
        receipt = schema_evolution.ready_receipt(instance)
        field = FieldDefinition.objects.select_for_update().get(pk=field.pk)
        if receipt is not None:
            schema_evolution.require_addition(actor, instance)
            schema_evolution.mark_addition_transaction()
            with transaction.atomic(using="tenant"):
                schema_evolution.set_field_indexed(receipt, field, actor)
        elif not field.indexed:
            field.indexed = True
            field.save(update_fields=["indexed"])
        event(actor, instance, "field.indexed", field.id, live=receipt is not None)
    return field


def update_instance(actor, instance, data):
    require_manage(actor, instance, schema=False)
    values = validated(InstanceInput, data)
    with transaction.atomic():
        instance = AppInstance.objects.select_for_update().get(pk=instance.pk)
        for key, value in values.items():
            setattr(instance, key, value)
        instance.save()
        event(actor, instance, "archive" if values.get("archived") else "update", instance.id)
    return instance


def update_definition(actor, obj, data):
    model_scoped = isinstance(obj, (FieldDefinition, ConstraintDefinition))
    instance = obj.model.instance if model_scoped else obj.instance
    require_manage(actor, instance)
    serializer_type = (
        FieldPatch
        if isinstance(obj, FieldDefinition)
        else RelationshipPatch
        if isinstance(obj, RelationshipDefinition)
        else LabelInput
    )
    values = validated(serializer_type, data)
    if isinstance(obj, FieldDefinition) and "default_value" in values:
        values["default_value"] = validate_field_default(obj.data_type, values["default_value"])
    with transaction.atomic():
        lock_active(instance, structural=bool(set(values) - {"label", "position"}))
        obj = type(obj).objects.select_for_update().get(pk=obj.pk)
        for key, value in values.items():
            setattr(obj, key, value)
        obj.save()
        event(actor, instance, f"{obj._meta.model_name}.update", obj.id)
    return obj


def unique_key(queryset, key):
    if queryset.filter(key=key).exists():
        raise serializers.ValidationError({"key": "Already exists in this scope."})


def event(actor, instance, action, definition_id, **context):
    audit.record(
        actor=actor,
        organization_id=instance.organization_id,
        action=f"app_instance.{action}",
        resource_type="app_instance",
        resource_id=instance.id,
        context={"definition_id": str(definition_id), **context},
    )
