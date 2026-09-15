from rest_framework import serializers

from .models import (
    AppInstance,
    AppTemplate,
    AppTemplateVersion,
    ConstraintDefinition,
    FieldDefinition,
    ModelDefinition,
    RelationshipDefinition,
)


class TemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = AppTemplate
        fields = ["id", "organization", "label", "description", "draft", "archived", "created_at"]
        read_only_fields = fields


class VersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AppTemplateVersion
        fields = ["id", "template", "number", "definition", "checksum_sha256", "created_at"]
        read_only_fields = fields


class InstanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = AppInstance
        fields = ["id", "organization", "project", "source_version", "label", "archived", "created_at"]
        read_only_fields = fields


class FieldSerializer(serializers.ModelSerializer):
    class Meta:
        model = FieldDefinition
        fields = [
            "id",
            "model",
            "key",
            "label",
            "data_type",
            "required",
            "default_value",
            "unique",
            "indexed",
            "position",
            "source_definition_id",
        ]
        read_only_fields = fields


class ModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = ModelDefinition
        fields = ["id", "instance", "key", "label", "position", "source_definition_id"]
        read_only_fields = fields


class ConstraintSerializer(serializers.ModelSerializer):
    # Field membership is exposed as stable AppField ids only, in their
    # current display order -- never a physical constraint/index name
    # (see databases.services.add_field_set_unique_constraint's own
    # naming, which is deliberately internal).
    field_ids: serializers.PrimaryKeyRelatedField = serializers.PrimaryKeyRelatedField(
        source="fields", many=True, read_only=True
    )

    class Meta:
        model = ConstraintDefinition
        fields = ["id", "model", "key", "label", "position", "source_definition_id", "field_ids"]
        read_only_fields = fields


class RelationshipSerializer(serializers.ModelSerializer):
    class Meta:
        model = RelationshipDefinition
        fields = [
            "id",
            "instance",
            "key",
            "label",
            "position",
            "source_definition_id",
            "source_model",
            "target_model",
            "kind",
            "deletion_policy",
        ]
        read_only_fields = fields
