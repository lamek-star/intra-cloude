"""Strict, bounded, non-executable template format shared by API and services."""

import json
import uuid
from urllib.parse import urlparse

from rest_framework import serializers

from databases.connectors import UnsafeHost, assert_host_is_safe
from databases.ddl import DDLValidationError, default_clause_sql
from databases.identifiers import IdentifierError, validate_column_name
from databases.values import RowValueError, validate_and_convert

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


def validate_action_value(data_type, value):
    """A workflow transition's field-action value must be a literal
    already-safe to hand to databases.rows.update_row_if for this field's
    real data type -- the same conversion/validation update_row/insert_row
    already run on any ordinary record write, just performed at
    definition time too (like validate_field_default above) so a value
    that will be rejected when the transition is actually applied is
    caught here instead."""
    try:
        return validate_and_convert(value, data_type)
    except RowValueError as exc:
        raise serializers.ValidationError({"value": str(exc)}) from exc


def validate_notify_url(url):
    """A workflow transition's notification target must be a real http(s)
    URL whose host isn't an SSRF pivot -- reuses the exact same guard
    ConnectedDatabase.host already relies on (Section 30 of the master
    prompt), not a second implementation. Re-checked again immediately
    before every delivery attempt (app_platform/tasks.py), since DNS can
    rebind between definition time and send time."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise serializers.ValidationError({"notify_url": "Must be an http:// or https:// URL."})
    try:
        assert_host_is_safe(parsed.hostname)
    except UnsafeHost as exc:
        raise serializers.ValidationError({"notify_url": str(exc)}) from exc
    return url


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
    unique = serializers.BooleanField(default=False)  # type: ignore[assignment]  # DRF declarative field, removed by its metaclass
    indexed = serializers.BooleanField(default=False)  # type: ignore[assignment]  # DRF declarative field, removed by its metaclass

    def validate(self, data):
        data["default_value"] = validate_field_default(data["data_type"], data.get("default_value"))
        return data


class SnapshotField(FieldInput):
    id = serializers.UUIDField(default=uuid.uuid4)


class ConstraintInput(StrictSerializer):
    """A model-level composite UNIQUE constraint. `field_ids`/
    `relationship_ids` reference stable AppField/AppRelationship
    definition ids, never display labels or physical column/table names --
    reused as-is for both a draft/template snapshot (where the ids are
    other elements of the same unpublished definition) and a live
    instance's add-constraint action (instances.add_constraint, where they
    must resolve to real FieldDefinition/RelationshipDefinition rows on
    the same model -- checked there, not here, since this serializer has
    no access to a live model's fields/relationships)."""

    key = KeyField()
    label = serializers.CharField(max_length=200)  # type: ignore[assignment]  # DRF declarative field, removed by its metaclass
    field_ids = serializers.ListField(
        child=serializers.UUIDField(), required=False, default=list, max_length=32
    )  # type: ignore[assignment]
    relationship_ids = serializers.ListField(
        child=serializers.UUIDField(), required=False, default=list, max_length=32
    )  # type: ignore[assignment]

    def validate(self, data):
        combined = data["field_ids"] + data["relationship_ids"]
        if len(combined) < 2:
            raise serializers.ValidationError(
                "A constraint needs at least two fields or relationships combined."
            )
        if len(set(combined)) != len(combined):
            raise serializers.ValidationError(
                {"field_ids": "A field or relationship cannot be repeated in one constraint."}
            )
        return data


class SnapshotConstraint(ConstraintInput):
    id = serializers.UUIDField(default=uuid.uuid4)


class StateInput(StrictSerializer):
    key = KeyField()
    label = serializers.CharField(max_length=200)  # type: ignore[assignment]  # DRF declarative field, removed by its metaclass


class SnapshotState(StateInput):
    id = serializers.UUIDField(default=uuid.uuid4)


class ConditionInput(StrictSerializer):
    """One ANDed check against one of the workflow's own model's fields --
    deliberately as narrow as databases/rows.py's own exact-match-only
    filtering (Section 12), not a general expression language."""

    field_id = serializers.UUIDField()
    operator = serializers.ChoiceField(choices=["eq", "ne", "is_null", "is_not_null"])
    value = serializers.JSONField(required=False, allow_null=True, default=None)

    def validate(self, data):
        if data["operator"] in ("is_null", "is_not_null"):
            if data.get("value") is not None:
                raise serializers.ValidationError({"value": "Not used for is_null/is_not_null."})
        elif data.get("value") is None:
            raise serializers.ValidationError({"value": "Required for eq/ne."})
        return data


class ActionInput(StrictSerializer):
    """A literal field write applied in the same compare-and-swap UPDATE
    as the state change (databases.rows.update_row_if) -- literal-only,
    never a calculated/derived value, which is also what makes a replayed
    apply naturally idempotent (setting a column to a fixed value twice is
    a no-op the second time)."""

    field_id = serializers.UUIDField()
    value = serializers.JSONField(allow_null=True)


class TransitionInput(StrictSerializer):
    key = KeyField()
    label = serializers.CharField(max_length=200)  # type: ignore[assignment]  # DRF declarative field, removed by its metaclass
    from_state = serializers.UUIDField(required=False, allow_null=True, default=None)
    to_state = serializers.UUIDField()
    conditions = serializers.ListField(  # type: ignore[assignment]
        child=ConditionInput(), required=False, default=list, max_length=20
    )
    field_actions = serializers.ListField(  # type: ignore[assignment]
        child=ActionInput(), required=False, default=list, max_length=20
    )
    requires_approval = serializers.BooleanField(default=False)  # type: ignore[assignment]  # DRF declarative field, removed by its metaclass
    notify_url = serializers.CharField(  # type: ignore[assignment]  # DRF declarative field, removed by its metaclass
        max_length=2000, required=False, allow_blank=True, default=""
    )

    def validate(self, data):
        if data["notify_url"]:
            validate_notify_url(data["notify_url"])
        return data


class SnapshotTransition(TransitionInput):
    id = serializers.UUIDField(default=uuid.uuid4)


class WorkflowInput(StrictSerializer):
    key = KeyField()
    label = serializers.CharField(max_length=200)  # type: ignore[assignment]  # DRF declarative field, removed by its metaclass
    state_field = serializers.UUIDField()


class SnapshotWorkflow(WorkflowInput):
    id = serializers.UUIDField(default=uuid.uuid4)
    states = serializers.ListField(child=SnapshotState(), max_length=50)  # type: ignore[assignment]
    transitions = serializers.ListField(  # type: ignore[assignment]
        child=SnapshotTransition(), max_length=200, required=False, default=list
    )


class ModelInput(StrictSerializer):
    key = KeyField()
    label = serializers.CharField(max_length=200)  # type: ignore[assignment]  # DRF declarative field, removed by its metaclass


class SnapshotModel(ModelInput):
    id = serializers.UUIDField(default=uuid.uuid4)
    fields = serializers.ListField(child=SnapshotField(), max_length=100)  # type: ignore[assignment]
    constraints = serializers.ListField(  # type: ignore[assignment]
        child=SnapshotConstraint(), max_length=20, required=False, default=list
    )
    workflows = serializers.ListField(  # type: ignore[assignment]
        child=SnapshotWorkflow(), max_length=10, required=False, default=list
    )


class RelationshipInput(ModelInput):
    source_model = serializers.UUIDField()
    target_model = serializers.UUIDField()
    kind = serializers.ChoiceField(choices=["many_to_one", "many_to_many"], default="many_to_one")
    deletion_policy = serializers.ChoiceField(choices=["restrict", "set_null"], default="restrict")

    def validate(self, data):
        # deletion_policy is meaningless for a many_to_many relationship
        # (see RelationshipDefinition.deletion_policy's own docstring) --
        # normalized rather than rejected, so a client that doesn't
        # know/care doesn't need to omit or guess a value.
        if data["kind"] == "many_to_many":
            data["deletion_policy"] = "restrict"
        return data


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
            unique(model.get("constraints", []))
            field_ids = {field["id"] for field in model["fields"]}
            field_by_id = {field["id"]: field for field in model["fields"]}
            for constraint in model.get("constraints", []):
                if not set(constraint["field_ids"]).issubset(field_ids):
                    raise serializers.ValidationError(
                        "Constraint fields must belong to the same model."
                    )

            unique(model.get("workflows", []))
            for workflow in model.get("workflows", []):
                if workflow["state_field"] not in field_ids:
                    raise serializers.ValidationError(
                        "A workflow's state field must belong to the same model."
                    )
                if field_by_id[workflow["state_field"]]["data_type"] != "text":
                    raise serializers.ValidationError("A workflow's state field must be a text field.")
                unique(workflow["states"])
                unique(workflow["transitions"])
                state_ids = {state["id"] for state in workflow["states"]}
                for transition in workflow["transitions"]:
                    if transition["to_state"] not in state_ids:
                        raise serializers.ValidationError(
                            "A transition's to_state must belong to its own workflow."
                        )
                    if transition["from_state"] is not None and transition["from_state"] not in state_ids:
                        raise serializers.ValidationError(
                            "A transition's from_state must belong to its own workflow."
                        )
                    for condition in transition["conditions"]:
                        if condition["field_id"] not in field_ids:
                            raise serializers.ValidationError(
                                "A condition's field must belong to the workflow's own model."
                            )
                    for action in transition["field_actions"]:
                        if action["field_id"] not in field_ids:
                            raise serializers.ValidationError(
                                "An action's field must belong to the workflow's own model."
                            )
                        action["value"] = validate_action_value(
                            field_by_id[action["field_id"]]["data_type"], action["value"]
                        )
        unique(data["relationships"])
        model_ids = {model["id"] for model in data["models"]}
        for relation in data["relationships"]:
            if relation["source_model"] not in model_ids or relation["target_model"] not in model_ids:
                raise serializers.ValidationError("Relationship models must belong to this definition.")

        # A constraint's relationship members must be a many_to_one
        # relationship whose own FK column lives on the constrained
        # model's table -- i.e. that relationship's source_model. A
        # many_to_many relationship has no such column (it's a join
        # table) and is never eligible. Checked here, once relationships
        # are known, rather than inside ConstraintInput itself.
        relations_by_id = {relation["id"]: relation for relation in data["relationships"]}
        for model in data["models"]:
            for constraint in model.get("constraints", []):
                for relationship_id in constraint["relationship_ids"]:
                    relation = relations_by_id.get(relationship_id)
                    if (
                        relation is None
                        or relation["source_model"] != model["id"]
                        or relation["kind"] != "many_to_one"
                    ):
                        raise serializers.ValidationError(
                            "Constraint relationships must be a many-to-one relationship "
                            "owned by the same model."
                        )
        return data


def validate_definition(value):
    if len(json.dumps(value, default=str).encode()) > 2_000_000:
        raise serializers.ValidationError("Definition exceeds 2 MB.")
    serializer = DefinitionInput(data=value)
    serializer.is_valid(raise_exception=True)
    return json.loads(json.dumps(serializer.validated_data, default=str))
