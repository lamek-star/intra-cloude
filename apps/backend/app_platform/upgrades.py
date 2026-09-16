"""Phase 9 -- template versioning and upgrades
(docs/implementation/APP_PLATFORM_ROADMAP.md,
docs/implementation/APP_PLATFORM_PHASE9.md).

A three-way comparison, exactly as `docs/APP_PLATFORM_ARCHITECTURE.md`
scoped it when Phase 1 preserved the lineage this needs: "source
snapshot, installed configuration, new version."

- **Base** -- `_base_version(instance).definition`: the published
  template snapshot this instance was last fully reconciled against --
  `instance.source_version` (permanent install provenance, immutable at
  the DB level -- see `_base_version`'s own docstring) until an upgrade
  has ever applied, and that upgrade's own `AppInstanceUpgrade.to_version`
  after.
- **Live** -- the instance's own real `ModelDefinition`/`FieldDefinition`/
  `RelationshipDefinition`/`ConstraintDefinition` rows. A row with
  `source_definition_id=None` has no template lineage at all -- a pure
  customer addition made directly through the App Builder (Phase 3) --
  and is invisible to this module by construction: the diff never reads,
  compares against, or touches it. That *is* "customer overrides":
  preserved simply by never being in scope.
- **Target** -- a newer, published `AppTemplateVersion.definition` of the
  *same* template.

For every stable item id (assigned once, at template-draft time, and
preserved across republication per the architecture doc's own "authors
must retain returned UUIDs to retain lineage" rule):

- In target but not live -> **add**. Applied by calling the exact same
  `instances.add_model`/`add_field`/`add_relationship`/`add_constraint`
  the App Builder itself uses (this module never duplicates their
  validation, capability checks, or `schema_evolution.py` DDL calls),
  just with the stable id threaded through via each function's new
  `source_definition_id=` keyword so the new row's lineage is preserved
  for the *next* upgrade.
- In base, live, and target, only the **label** differs, and live's
  label still matches base (customer never touched it locally) ->
  **label_sync**: safe to auto-apply (a label is presentation only, never
  physical -- the same reason `instances.update_definition` already lets
  a label change on a locked, already-provisioned instance without
  involving `schema_evolution.py` at all).
- In base, live, and target, but live's label was independently changed
  by the customer to something *other* than what target now says ->
  **conflict** (`reason: "label_conflict"`). Never auto-applied, never
  silently overwritten -- reported for a human to reconcile by hand
  (edit the live label to whatever they want; the next preview/apply
  re-evaluates fresh).
- In base and target, but any *structural* attribute differs (a field's
  `data_type`/`required`/`default_value`/`unique`/`indexed`, a
  relationship's `kind`/`deletion_policy`/endpoints, a constraint's
  membership, or any kind's own `key`) -> **manual_review**
  (`reason: "structural_change_unsupported"`), regardless of whether the
  customer also changed it locally. There is no safe DDL path anywhere
  in this codebase for altering an already-materialized column/
  relationship/constraint -- `schema_evolution.py`'s own module docstring
  draws this exact line for live App Builder edits ("never a rename,
  type change, deletion, or any edit to something that already exists
  physically"), and this module holds the identical line for upgrades.
- In base but not target (the template removed it upstream) ->
  **manual_review** (`reason: "removed_upstream_unsupported"`) if it is
  still live -- this platform has no definition-deletion capability
  anywhere, so there is nothing to apply either way; reported so the
  admin at least knows the template moved on without them.

Business data is preserved for the same reason Phase 3's additive-only
schema evolution already preserves it: every `add_*` operation only ever
creates a new table/column/join-table/index, never touches an existing
one, and every physical name is derived from the *live* definition's own
freshly-generated id (`runtime_plan.physical_name`), never from a label
or a template-draft id -- so nothing here can ever collide with, rename,
or drop an existing row's storage.
"""

from django.db import transaction
from django.http import Http404
from rest_framework import serializers

from . import instances
from .access import check, require_manage
from .models import (
    AppInstance,
    AppInstanceUpgrade,
    AppTemplateVersion,
    ConstraintDefinition,
    FieldDefinition,
)

_MODEL_STRUCTURAL_KEYS = ("key",)
_FIELD_STRUCTURAL_KEYS = ("key", "data_type", "required", "default_value", "unique", "indexed")
_RELATIONSHIP_STRUCTURAL_KEYS = ("key", "kind", "deletion_policy", "source_model", "target_model")
_CONSTRAINT_STRUCTURAL_KEYS = ("key", "field_ids", "relationship_ids")


def _index_target(definition):
    """A published (or draft-shaped) definition JSON blob -> four
    {stable_id: json_safe_dict} maps, one per kind. Every dict carries its
    own `"id"` (redundant with its map key, but convenient once flattened
    into a plain list for `apply_upgrade`) and, for fields/constraints, a
    `"_model_id"` back-reference to their owning model's own stable id."""
    models_by_id, fields_by_id, constraints_by_id = {}, {}, {}
    for m in definition["models"]:
        models_by_id[m["id"]] = {"id": m["id"], "key": m["key"], "label": m["label"]}
        for f in m["fields"]:
            fields_by_id[f["id"]] = {
                "id": f["id"], "_model_id": m["id"], "key": f["key"], "label": f["label"],
                "data_type": f["data_type"], "required": f["required"],
                "default_value": f.get("default_value"),
                "unique": f.get("unique", False), "indexed": f.get("indexed", False),
            }
        for c in m.get("constraints", []):
            constraints_by_id[c["id"]] = {
                "id": c["id"], "_model_id": m["id"], "key": c["key"], "label": c["label"],
                "field_ids": tuple(sorted(c["field_ids"])),
                "relationship_ids": tuple(sorted(c["relationship_ids"])),
            }
    relationships_by_id = {
        r["id"]: {
            "id": r["id"], "key": r["key"], "label": r["label"],
            "source_model": r["source_model"], "target_model": r["target_model"],
            "kind": r["kind"], "deletion_policy": r["deletion_policy"],
        }
        for r in definition["relationships"]
    }
    return models_by_id, fields_by_id, relationships_by_id, constraints_by_id


def _live_snapshot(instance):
    """Same four-map shape as `_index_target`, sourced from the instance's
    real, currently-live rows, keyed by `source_definition_id` -- a row
    with no lineage (a customer addition) is simply never a key here, so
    the diff below can never see it."""
    models_qs = list(instance.models.all())
    fields_qs = list(FieldDefinition.objects.filter(model__instance=instance).select_related("model"))
    relationships_qs = list(
        instance.relationships.all().select_related("source_model", "target_model")
    )
    constraints_qs = list(
        ConstraintDefinition.objects.filter(model__instance=instance)
        .select_related("model")
        .prefetch_related("fields", "relationships")
    )

    # `source_definition_id` is a Django UUIDField -- real `uuid.UUID`
    # instances, not strings. `_index_target` above keys/compares using
    # the plain strings a draft/version JSON blob always stores UUIDs as
    # (`str(uuid.uuid4())`); `uuid.UUID(...) != "..."` even for the same
    # value, so every id used as a dict key or compared against a target/
    # base value here must be `str()`-cast, or every live lookup silently
    # misses and everything looks brand new.
    models_by_id = {
        str(m.source_definition_id): {"key": m.key, "label": m.label}
        for m in models_qs if m.source_definition_id is not None
    }
    fields_by_id = {
        str(f.source_definition_id): {
            "key": f.key, "label": f.label, "data_type": f.data_type, "required": f.required,
            "default_value": f.default_value, "unique": f.unique, "indexed": f.indexed,
        }
        for f in fields_qs if f.source_definition_id is not None
    }
    relationships_by_id = {
        str(r.source_definition_id): {
            "key": r.key, "label": r.label,
            "source_model": (
                str(r.source_model.source_definition_id)
                if r.source_model.source_definition_id is not None else None
            ),
            "target_model": (
                str(r.target_model.source_definition_id)
                if r.target_model.source_definition_id is not None else None
            ),
            "kind": r.kind, "deletion_policy": r.deletion_policy,
        }
        for r in relationships_qs if r.source_definition_id is not None
    }
    constraints_by_id = {
        str(c.source_definition_id): {
            "key": c.key, "label": c.label,
            "field_ids": tuple(sorted(
                str(fld.source_definition_id)
                for fld in c.fields.all() if fld.source_definition_id is not None
            )),
            "relationship_ids": tuple(sorted(
                str(rel.source_definition_id)
                for rel in c.relationships.all() if rel.source_definition_id is not None
            )),
        }
        for c in constraints_qs if c.source_definition_id is not None
    }
    return models_by_id, fields_by_id, relationships_by_id, constraints_by_id


def _diff_kind(base_by_id, live_by_id, target_by_id, structural_keys):
    to_add, label_sync, manual_review = [], [], []
    for item_id, target_item in target_by_id.items():
        live_item = live_by_id.get(item_id)
        base_item = base_by_id.get(item_id)
        if live_item is None:
            # Brand new in target (the common case), or -- impossible
            # today, since nothing can delete a live definition -- base
            # had it but live somehow doesn't. Either way: add it.
            to_add.append(target_item)
            continue
        if base_item is None:
            # Live already has it (a prior upgrade must have added it)
            # but this diff's own base doesn't know about it. Can only
            # happen if base is stale relative to what's actually live,
            # which apply_upgrade never allows (source_version always
            # advances to exactly the version an upgrade completes to).
            # Nothing to compare against -- treat as already reconciled.
            continue
        structural_changed = sorted(
            key for key in structural_keys if target_item[key] != base_item[key]
        )
        if structural_changed:
            manual_review.append({
                "id": item_id, "key": target_item["key"], "reason": "structural_change_unsupported",
                "changed_fields": structural_changed,
            })
            continue
        if target_item["label"] != base_item["label"] and live_item["label"] != target_item["label"]:
            if live_item["label"] == base_item["label"]:
                label_sync.append({
                    "id": item_id, "key": target_item["key"],
                    "from": live_item["label"], "to": target_item["label"],
                })
            else:
                manual_review.append({
                    "id": item_id, "key": target_item["key"], "reason": "label_conflict",
                    "template_label": target_item["label"], "live_label": live_item["label"],
                })
    manual_review += [
        {"id": item_id, "key": base_item["key"], "reason": "removed_upstream_unsupported"}
        for item_id, base_item in base_by_id.items()
        if item_id not in target_by_id and item_id in live_by_id
    ]
    return {"add": to_add, "label_sync": label_sync, "manual_review": manual_review}


def _base_version(instance):
    """`AppInstance.source_version` is permanent install provenance, not
    a moving pointer -- the `app_instance_identity` DB trigger (migration
    0002) makes `source_version_id` immutable after creation, by design,
    the same way `id`/`organization_id`/`project_id` are. The *base* a
    diff should actually compare against is therefore not always
    `instance.source_version`: once an upgrade has applied, the instance
    is now reconciled against that upgrade's own target, and the next
    upgrade's diff must use *that* as its base, or every already-applied
    change would show up as a fresh "add" (or worse, a duplicate-key
    conflict) forever. `AppInstanceUpgrade` rows carry that forward
    pointer instead: the most recent one's `to_version`, or -- before any
    upgrade has ever been applied -- `instance.source_version` itself."""
    latest = instance.upgrades.first()
    return latest.to_version if latest is not None else instance.source_version


def _resolve_target_version(actor, instance, version_id, base):
    try:
        version = AppTemplateVersion.objects.select_related("template").get(
            pk=version_id, template__organization_id=instance.organization_id
        )
    except AppTemplateVersion.DoesNotExist as exc:
        raise Http404 from exc
    # Reading the target version's content requires the same capability
    # `instances.install` itself requires before ever reading a version.
    check(actor, instance.organization_id, "app_template.read", ("app_template", version.template_id))
    if version.template_id != instance.source_version.template_id:
        raise serializers.ValidationError(
            "The target version must belong to the same template this instance was installed from."
        )
    if version.number <= base.number:
        raise serializers.ValidationError(
            "The target version must be newer than the instance's current version."
        )
    return version


def _compute_diff(instance, base, target_version):
    base_models, base_fields, base_rels, base_constraints = _index_target(base.definition)
    target_models, target_fields, target_rels, target_constraints = _index_target(target_version.definition)
    live_models, live_fields, live_rels, live_constraints = _live_snapshot(instance)
    return {
        "models": _diff_kind(base_models, live_models, target_models, _MODEL_STRUCTURAL_KEYS),
        "fields": _diff_kind(base_fields, live_fields, target_fields, _FIELD_STRUCTURAL_KEYS),
        "relationships": _diff_kind(base_rels, live_rels, target_rels, _RELATIONSHIP_STRUCTURAL_KEYS),
        "constraints": _diff_kind(
            base_constraints, live_constraints, target_constraints, _CONSTRAINT_STRUCTURAL_KEYS
        ),
    }


def preview_upgrade(actor, instance, target_version_id):
    """Read-only -- never mutates anything. `apply_upgrade` recomputes
    this exact same diff itself immediately before applying it, so a
    preview can never drift from what an apply actually does."""
    require_manage(actor, instance, schema=False)
    base = _base_version(instance)
    target_version = _resolve_target_version(actor, instance, target_version_id, base)
    return _compute_diff(instance, base, target_version)


def apply_upgrade(actor, instance, target_version_id):
    require_manage(actor, instance)
    with transaction.atomic():
        instance = AppInstance.objects.select_for_update().select_related("source_version__template").get(
            pk=instance.pk
        )
        if instance.archived:
            raise serializers.ValidationError("Archived instance definitions cannot be changed.")
        from_version = _base_version(instance)
        target_version = _resolve_target_version(actor, instance, target_version_id, from_version)
        diff = _compute_diff(instance, from_version, target_version)

        # Same str()-cast requirement `_live_snapshot` documents above --
        # `source_definition_id` is a real `uuid.UUID`, but every id in
        # `diff` (built from JSON) is a plain string.
        model_map = {
            str(m.source_definition_id): m
            for m in instance.models.all() if m.source_definition_id is not None
        }
        field_map = {
            str(f.source_definition_id): f
            for f in FieldDefinition.objects.filter(model__instance=instance)
            if f.source_definition_id is not None
        }
        relationship_map = {
            str(r.source_definition_id): r
            for r in instance.relationships.all() if r.source_definition_id is not None
        }
        constraint_map = {
            str(c.source_definition_id): c
            for c in ConstraintDefinition.objects.filter(model__instance=instance)
            if c.source_definition_id is not None
        }

        with transaction.atomic(using="tenant"):
            # Same dependency order instances.install() itself uses:
            # models, then fields/relationships (either can now reference
            # a model just added above), then constraints (may reference
            # a relationship just added below).
            for item in diff["models"]["add"]:
                model_map[item["id"]] = instances.add_model(
                    actor, instance, {"key": item["key"], "label": item["label"]},
                    source_definition_id=item["id"],
                )
            for item in diff["fields"]["add"]:
                field_map[item["id"]] = instances.add_field(
                    actor, model_map[item["_model_id"]],
                    {
                        "key": item["key"], "label": item["label"], "data_type": item["data_type"],
                        "required": item["required"], "default_value": item["default_value"],
                        "unique": item["unique"], "indexed": item["indexed"],
                    },
                    source_definition_id=item["id"],
                )
            for item in diff["relationships"]["add"]:
                relationship_map[item["id"]] = instances.add_relationship(
                    actor, instance,
                    {
                        "key": item["key"], "label": item["label"],
                        "source_model": str(model_map[item["source_model"]].id),
                        "target_model": str(model_map[item["target_model"]].id),
                        "kind": item["kind"], "deletion_policy": item["deletion_policy"],
                    },
                    source_definition_id=item["id"],
                )
            for item in diff["constraints"]["add"]:
                constraint_map[item["id"]] = instances.add_constraint(
                    actor, model_map[item["_model_id"]],
                    {
                        "key": item["key"], "label": item["label"],
                        "field_ids": [str(field_map[fid].id) for fid in item["field_ids"]],
                        "relationship_ids": [
                            str(relationship_map[rid].id) for rid in item["relationship_ids"]
                        ],
                    },
                    source_definition_id=item["id"],
                )
            for kind, live_map in (
                ("models", model_map), ("fields", field_map),
                ("relationships", relationship_map), ("constraints", constraint_map),
            ):
                for entry in diff[kind]["label_sync"]:
                    obj = live_map[entry["id"]]
                    obj.label = entry["to"]
                    obj.save(update_fields=["label"])

        # `instance.source_version` itself never changes -- it is
        # permanent install provenance, immutable at the DB level (see
        # `_base_version`'s docstring above). This `AppInstanceUpgrade`
        # row's own `to_version` is what the *next* call's `_base_version`
        # will use instead.
        upgrade = AppInstanceUpgrade.objects.create(
            instance=instance, from_version=from_version, to_version=target_version,
            summary=diff, created_by=actor,
        )
        instances.event(
            actor, instance, "upgrade.apply", upgrade.id,
            from_version=from_version.number, to_version=target_version.number,
        )
    return upgrade
