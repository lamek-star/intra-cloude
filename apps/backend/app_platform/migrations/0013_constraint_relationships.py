"""Relationship-backed composite constraints: ConstraintDefinition can now
also reference a model's own many_to_one relationships (their FK columns),
alongside its existing scalar-field membership -- closing the real gap
docs/SPARE_PARTS_INTEGRATION_READINESS.md's Inventory (Part x Warehouse) row
described but the code never actually supported (ConstraintDefinition.fields
was FieldDefinition-only).

- `ConstraintDefinition.relationships`, a new parallel M2M to
  RelationshipDefinition (see models.py's updated docstring for the
  eligibility rule: relationship.source_model == the constraint's own
  model, relationship.kind == "many_to_one" -- many_to_many stays
  completely untouched by this feature).
- A new trigger, `app_runtime_constraint_relationships_guard`, on the new
  M2M through table `app_platform_constraintdefinition_relationships` --
  identical shape and reasoning to 0012's `app_runtime_constraint_fields_
  guard` for `app_platform_constraintdefinition_fields`: once a
  constraint's model's instance has a completed runtime provision, this
  membership must never change through this path either, with the same
  sanctioned-INSERT-during-schema_evolution exemption (instances.
  add_constraint calls `constraint.relationships.set(...)` inside the same
  `mark_addition_transaction` scope as the ConstraintDefinition row's own
  INSERT)."""

from django.db import migrations, models

FORWARD = """
CREATE FUNCTION app_runtime_constraint_relationships_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE row_id uuid; owner_id uuid;
BEGIN
    IF TG_OP = 'INSERT' AND current_setting('app_platform.schema_evolution', true) = 'on' THEN
        RETURN NEW;
    END IF;
    IF TG_OP = 'DELETE' THEN row_id := OLD.constraintdefinition_id; ELSE row_id := NEW.constraintdefinition_id; END IF;
    SELECT mo.instance_id INTO owner_id FROM app_platform_constraintdefinition cd
        JOIN app_platform_modeldefinition mo ON mo.id = cd.model_id
        WHERE cd.id = row_id;
    PERFORM id FROM app_platform_appinstance WHERE id = owner_id FOR UPDATE;
    IF EXISTS (SELECT 1 FROM app_platform_runtimeprovision WHERE instance_id = owner_id) THEN
        RAISE EXCEPTION 'Reserved runtime constraint relationships require a schema migration' USING ERRCODE = '23514';
    END IF;
    IF TG_OP = 'DELETE' THEN RETURN OLD; ELSE RETURN NEW; END IF;
END;
$$;
CREATE TRIGGER app_runtime_constraint_relationships_guard BEFORE INSERT OR UPDATE OR DELETE
ON app_platform_constraintdefinition_relationships
FOR EACH ROW EXECUTE FUNCTION app_runtime_constraint_relationships_guard();
"""

REVERSE = """
DROP TRIGGER app_runtime_constraint_relationships_guard ON app_platform_constraintdefinition_relationships;
DROP FUNCTION app_runtime_constraint_relationships_guard();
"""


class Migration(migrations.Migration):

    dependencies = [
        ("app_platform", "0012_composite_unique_constraint_guards"),
    ]

    operations = [
        migrations.AddField(
            model_name="constraintdefinition",
            name="relationships",
            field=models.ManyToManyField(
                related_name="unique_constraints", to="app_platform.relationshipdefinition"
            ),
        ),
        migrations.RunSQL(FORWARD, REVERSE),
    ]
