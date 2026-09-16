from rest_framework import serializers

from .models import (
    AppInstance,
    AppInstanceUpgrade,
    AppTemplate,
    AppTemplateVersion,
    ConstraintDefinition,
    FieldDefinition,
    ModelDefinition,
    RelationshipDefinition,
    UnitScopedGrant,
    WorkflowDefinition,
    WorkflowState,
    WorkflowTransition,
    WorkflowTransitionAttempt,
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


class UpgradeSerializer(serializers.ModelSerializer):
    class Meta:
        model = AppInstanceUpgrade
        fields = ["id", "instance", "from_version", "to_version", "summary", "created_at"]
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
    # Membership is exposed as stable AppField/AppRelationship ids only,
    # in their current display order -- never a physical constraint/index
    # name (see databases.services.add_field_set_unique_constraint's own
    # naming, which is deliberately internal).
    field_ids: serializers.PrimaryKeyRelatedField = serializers.PrimaryKeyRelatedField(
        source="fields", many=True, read_only=True
    )
    relationship_ids: serializers.PrimaryKeyRelatedField = serializers.PrimaryKeyRelatedField(
        source="relationships", many=True, read_only=True
    )

    class Meta:
        model = ConstraintDefinition
        fields = [
            "id",
            "model",
            "key",
            "label",
            "position",
            "source_definition_id",
            "field_ids",
            "relationship_ids",
        ]
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


class WorkflowSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkflowDefinition
        fields = ["id", "model", "key", "label", "position", "source_definition_id", "state_field"]
        read_only_fields = fields


class StateSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkflowState
        fields = ["id", "workflow", "key", "label", "position", "source_definition_id"]
        read_only_fields = fields


class TransitionSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkflowTransition
        fields = [
            "id",
            "workflow",
            "key",
            "label",
            "position",
            "source_definition_id",
            "from_state",
            "to_state",
            "conditions",
            "field_actions",
            "requires_approval",
            "notify_url",
        ]
        read_only_fields = fields


class UnitScopedGrantSerializer(serializers.ModelSerializer):
    class Meta:
        model = UnitScopedGrant
        fields = ["id", "model", "unit", "user", "level", "granted_by", "expires_at", "created_at"]
        read_only_fields = fields


class UnitScopeGrantCreateSerializer(serializers.Serializer):
    user_id = serializers.UUIDField()
    unit_id = serializers.UUIDField()
    level = serializers.ChoiceField(choices=UnitScopedGrant.Level.values)
    expires_at = serializers.DateTimeField(required=False, allow_null=True, default=None)


class AttemptSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkflowTransitionAttempt
        fields = [
            "id",
            "transition",
            "record_id",
            "state_before",
            "state_after",
            "completed_at",
            "last_error",
            "created_at",
        ]
        read_only_fields = fields
