"""Read-only, deterministic relational plan for an installed application.

The planner produces validated catalog inputs, never executable SQL. It does
not provision tables or make a metadata-only installation runnable.
"""

import hashlib
import json
import uuid

from django.db import transaction
from rest_framework.exceptions import ValidationError

from databases.identifiers import validate_identifier

from .definitions import validate_definition
from .instances import require_manage
from .models import AppInstance


def physical_name(prefix: str, identity: str) -> str:
    return validate_identifier(f"{prefix}_{uuid.UUID(identity).hex}")


def compile_plan(instance_id, definition):
    """Compile an already installed definition; revalidate even internal input."""
    definition = validate_definition(definition)
    if not definition["models"]:
        raise ValidationError("Add at least one model before planning a runtime.")
    instance_id = uuid.UUID(str(instance_id))
    database_id = uuid.uuid5(instance_id, "intraforge:app-runtime:v1")
    models = []
    for model in sorted(definition["models"], key=lambda item: item["id"]):
        columns = []
        for field in sorted(model["fields"], key=lambda item: item["id"]):
            columns.append(
                {
                    "definition_id": field["id"],
                    "name": physical_name("f", field["id"]),
                    "data_type": field["data_type"],
                    "is_nullable": not field["required"],
                    "precision": 18 if field["data_type"] == "decimal" else None,
                    "scale": 4 if field["data_type"] == "decimal" else None,
                    "default": field.get("default_value"),
                }
            )
        models.append(
            {
                "definition_id": model["id"],
                "name": physical_name("m", model["id"]),
                "primary_key": {"name": "id", "data_type": "uuid", "generated": True},
                "columns": columns,
            }
        )
    relationships = []
    for relation in sorted(definition["relationships"], key=lambda item: item["id"]):
        relationships.append(
            {
                "definition_id": relation["id"],
                "source_model": relation["source_model"],
                "target_model": relation["target_model"],
                "column": physical_name("r", relation["id"]),
                "data_type": "uuid",
                "is_nullable": True,
                "on_delete": relation["deletion_policy"],
            }
        )
    plan = {
        "format_version": 1,
        "instance_id": str(instance_id),
        "database_id": str(database_id),
        "schema_name": physical_name("db", str(database_id)),
        "models": models,
        "relationships": relationships,
    }
    encoded = json.dumps(plan, sort_keys=True, separators=(",", ":")).encode()
    return {**plan, "fingerprint": hashlib.sha256(encoded).hexdigest()}


def plan_runtime(actor, instance):
    require_manage(actor, instance)
    # Metadata mutation services take this same lock. A plan cannot mix an
    # old model list with a concurrently edited field/relationship set.
    with transaction.atomic():
        instance = AppInstance.objects.select_for_update().get(pk=instance.pk)
        if instance.archived:
            raise ValidationError("Archived instances cannot start a runtime.")
        definition = {
            "schema_version": 1,
            "models": [
                {
                    "id": str(model.id),
                    "key": model.key,
                    "label": model.label,
                    "fields": [
                        {
                            "id": str(field.id),
                            "key": field.key,
                            "label": field.label,
                            "data_type": field.data_type,
                            "required": field.required,
                            "default_value": field.default_value,
                        }
                        for field in model.fields.all()
                    ],
                }
                for model in instance.models.prefetch_related("fields")
            ],
            "relationships": [
                {
                    "id": str(relation.id),
                    "key": relation.key,
                    "label": relation.label,
                    "source_model": str(relation.source_model_id),
                    "target_model": str(relation.target_model_id),
                    "kind": relation.kind,
                    "deletion_policy": relation.deletion_policy,
                }
                for relation in instance.relationships.all()
            ],
        }
        return compile_plan(instance.id, definition)
