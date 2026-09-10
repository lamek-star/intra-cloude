"""Strict, bounded, non-executable template format shared by API and services."""

import json
import uuid

from rest_framework import serializers

from databases.ddl import DDLValidationError, default_clause_sql
from databases.identifiers import IdentifierError, validate_column_name

from .models import FieldDefinition


class StrictSerializer(serializers.Serializer):
    def to_internal_value(self, data):
        if not isinstance(data, dict):
            raise serializers.ValidationError("Expected an object.")
        unknown = set(data) - set(self.fields)
        if unknown:
            raise serializers.ValidationError(dict.fromkeys(sorted(unknown), "Unknown field."))
        return super().to_internal_value(data)


class KeyField(serializers.CharField):
    def __init__(self, **kwargs):
        super().__init__(max_length=63, trim_whitespace=False, **kwargs)

    def to_internal_value(self, data):
        value = super().to_internal_value(data)
        try:
            return validate_column_name(value)
        except IdentifierError as exc:
            raise serializers.ValidationError(str(exc)) from exc


def validate_field_default(data_type, value):
    """A field default must be one of Section 9's approved, type-matched
    defaults -- the same "safe set" `databases.services.add_column` enforces
    before generating real DDL, reused here (not reimplemented) so a
    default that will be rejected at provisioning time is caught at
    definition time instead."""
    if value is None:
        return None
    try:
        default_clause_sql(data_type, value)
    except DDLValidationError as exc:
        raise serializers.ValidationError({"default_value": str(exc)}) from exc
    return value


class FieldInput(StrictSerializer):
    key = KeyField()
    label = serializers.CharField(max_length=200)  # type: ignore[assignment]  # DRF declarative field, removed by its metaclass
    data_type = serializers.ChoiceField(choices=FieldDefinition.DataType.values)
    required = serializers.BooleanField(default=False)  # type: ignore[assignment]  # DRF declarative field, removed by its metaclass
    default_value = serializers.JSONField(required=False, allow_null=True, default=None)

    def validate(self, data):
        data["default_value"] = validate_field_default(data["data_type"], data.get("default_value"))
        return data


class SnapshotField(FieldInput):
    id = serializers.UUIDField(default=uuid.uuid4)


class ModelInput(StrictSerializer):
    key = KeyField()
    label = serializers.CharField(max_length=200)  # type: ignore[assignment]  # DRF declarative field, removed by its metaclass


class SnapshotModel(ModelInput):
    id = serializers.UUIDField(default=uuid.uuid4)
    fields = serializers.ListField(child=SnapshotField(), max_length=100)  # type: ignore[assignment]


class RelationshipInput(ModelInput):
    source_model = serializers.UUIDField()
    target_model = serializers.UUIDField()
    kind = serializers.ChoiceField(choices=["many_to_one"], default="many_to_one")
    deletion_policy = serializers.ChoiceField(choices=["restrict", "set_null"], default="restrict")


class SnapshotRelationship(RelationshipInput):
    id = serializers.UUIDField(default=uuid.uuid4)


class DefinitionInput(StrictSerializer):
    schema_version = serializers.ChoiceField(choices=[1])
    models = serializers.ListField(child=SnapshotModel(), max_length=100)
    relationships = serializers.ListField(child=SnapshotRelationship(), max_length=500)

    def validate(self, data):
        seen = set()

        def unique(items):
            keys = set()
            for item in items:
                if item["id"] in seen or item["key"] in keys:
                    raise serializers.ValidationError("Duplicate definition UUID or key.")
                seen.add(item["id"])
                keys.add(item["key"])

        unique(data["models"])
        for model in data["models"]:
            unique(model["fields"])
        unique(data["relationships"])
        model_ids = {model["id"] for model in data["models"]}
        for relation in data["relationships"]:
            if relation["source_model"] not in model_ids or relation["target_model"] not in model_ids:
                raise serializers.ValidationError("Relationship models must belong to this definition.")
        return data


def validate_definition(value):
    if len(json.dumps(value, default=str).encode()) > 2_000_000:
        raise serializers.ValidationError("Definition exceeds 2 MB.")
    serializer = DefinitionInput(data=value)
    serializer.is_valid(raise_exception=True)
    return json.loads(json.dumps(serializer.validated_data, default=str))
