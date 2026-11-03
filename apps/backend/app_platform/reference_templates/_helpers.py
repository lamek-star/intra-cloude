"""Shared, pure, DB-free builder helpers for every reference-template
module in this package (docs/implementation/APP_PLATFORM_PHASE4.md,
APP_PLATFORM_PHASE8.md). Each template module produces a
`DefinitionInput`-shaped dict using only these three helpers plus
Phases 1-3/6's existing field/relationship vocabulary -- no
industry-specific concept is ever added to `app_platform` itself."""

import uuid


def _field(key, label, data_type, **kwargs):
    field_id = str(uuid.uuid4())
    return field_id, {"id": field_id, "key": key, "label": label, "data_type": data_type, **kwargs}


def _model(model_id, key, label, fields, constraints=None):
    return {
        "id": model_id,
        "key": key,
        "label": label,
        "fields": [field for _id, field in fields],
        "constraints": constraints or [],
    }


def _relationship(key, label, source_model, target_model, *, kind="many_to_one", deletion_policy="restrict"):
    return {
        "id": str(uuid.uuid4()),
        "key": key,
        "label": label,
        "source_model": source_model,
        "target_model": target_model,
        "kind": kind,
        "deletion_policy": deletion_policy,
    }
