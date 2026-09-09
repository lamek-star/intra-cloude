"""Independent installation and serialized metadata edits; no tenant DDL."""

from django.db import transaction
from rest_framework import serializers

from audit import services as audit

from .access import check, get_owned
from .definitions import FieldInput, ModelInput, RelationshipInput, StrictSerializer, validate_definition
from .models import (
    AppInstance,
    AppTemplateVersion,
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


class FieldPatch(LabelInput):
    required = serializers.BooleanField(required=False)  # type: ignore[assignment]  # DRF declarative field, removed by its metaclass


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
        for item in definition["models"]:
            model = ModelDefinition.objects.create(
                instance=instance,
                key=item["key"],
                label=item["label"],
                source_definition_id=item["id"],
            )
            models[item["id"]] = model
            for field in item["fields"]:
                values = {key: value for key, value in field.items() if key != "id"}
                FieldDefinition.objects.create(model=model, source_definition_id=field["id"], **values)
        for item in definition["relationships"]:
            RelationshipDefinition.objects.create(
                instance=instance,
                source_definition_id=item["id"],
                key=item["key"],
                label=item["label"],
                source_model=models[item["source_model"]],
                target_model=models[item["target_model"]],
                kind=item["kind"],
                deletion_policy=item["deletion_policy"],
            )
        event(actor, instance, "install", instance.id)
    return instance


def validated(serializer_type, data):
    serializer = serializer_type(data=data)
    serializer.is_valid(raise_exception=True)
    return serializer.validated_data


def require_manage(actor, instance, schema=True):
    check(
        actor,
        instance.organization_id,
        "app_instance.schema.manage" if schema else "app_instance.manage",
        ("app_instance", instance.id),
    )


def lock_active(instance, *, structural=True):
    instance = AppInstance.objects.select_for_update().get(pk=instance.pk)
    if instance.archived:
        raise serializers.ValidationError("Archived instance definitions cannot be changed.")
    if structural and RuntimeProvision.objects.filter(instance=instance).exists():
        raise serializers.ValidationError("Runtime schema is reserved; structural edits require a migration.")
    return instance


def add_model(actor, instance, data):
    require_manage(actor, instance)
    values = validated(ModelInput, data)
    with transaction.atomic():
        instance = lock_active(instance)
        if instance.models.count() >= 100:
            raise serializers.ValidationError("Model limit reached.")
        unique_key(instance.models, values["key"])
        model = ModelDefinition.objects.create(instance=instance, **values)
        event(actor, instance, "model.create", model.id)
    return model


def add_field(actor, model, data):
    instance = model.instance
    require_manage(actor, instance)
    values = validated(FieldInput, data)
    with transaction.atomic():
        lock_active(instance)
        if model.fields.count() >= 100:
            raise serializers.ValidationError("Field limit reached.")
        unique_key(model.fields, values["key"])
        field = FieldDefinition.objects.create(model=model, **values)
        event(actor, instance, "field.create", field.id)
    return field


def add_relationship(actor, instance, data):
    require_manage(actor, instance)
    values = validated(RelationshipInput, data)
    with transaction.atomic():
        instance = lock_active(instance)
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
        relation = RelationshipDefinition.objects.create(instance=instance, **values)
        event(actor, instance, "relationship.create", relation.id)
    return relation


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
    instance = obj.model.instance if isinstance(obj, FieldDefinition) else obj.instance
    require_manage(actor, instance)
    serializer_type = (
        FieldPatch
        if isinstance(obj, FieldDefinition)
        else RelationshipPatch
        if isinstance(obj, RelationshipDefinition)
        else LabelInput
    )
    values = validated(serializer_type, data)
    with transaction.atomic():
        lock_active(instance, structural=bool(set(values) - {"label"}))
        obj = type(obj).objects.select_for_update().get(pk=obj.pk)
        for key, value in values.items():
            setattr(obj, key, value)
        obj.save()
        event(actor, instance, f"{obj._meta.model_name}.update", obj.id)
    return obj


def unique_key(queryset, key):
    if queryset.filter(key=key).exists():
        raise serializers.ValidationError({"key": "Already exists in this scope."})


def event(actor, instance, action, definition_id):
    audit.record(
        actor=actor,
        organization_id=instance.organization_id,
        action=f"app_instance.{action}",
        resource_type="app_instance",
        resource_id=instance.id,
        context={"definition_id": str(definition_id)},
    )
