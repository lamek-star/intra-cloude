"""Composite uniqueness (App Model constraints): teaches the control-plane
guards about the two new tables 0011 created.

- `app_runtime_definition_guard`: `app_platform_constraintdefinition` has
  the exact same shape as `app_platform_fielddefinition` for this
  function's purposes -- no `instance_id` column of its own, only a
  `model_id` FK -- so it joins the same branch that already resolves
  `owner_id` via `app_platform_modeldefinition`. Once that branch covers
  it, the function's existing label/position UPDATE exemption and
  sanctioned-INSERT-during-schema_evolution exemption both already apply
  to it for free (they're keyed on the session flag/column diff, not the
  table name).
- A brand-new trigger, `app_runtime_constraint_fields_guard`, for the M2M
  through table `app_platform_constraintdefinition_fields` -- a genuine
  new mutable surface 0011 introduced that the existing guard functions
  don't shape-match (its rows carry `constraintdefinition_id`/
  `fielddefinition_id`, not `model_id`/`instance_id`). Once a constraint's
  model's instance has a completed runtime provision, its field
  membership must never change through this path either (the field set
  is immutable after creation -- see ConstraintDefinition's own
  docstring), so this trigger blocks any INSERT/UPDATE/DELETE here the
  same way `app_runtime_definition_guard` blocks writes to the definition
  tables themselves, with the identical sanctioned-INSERT-during-
  schema_evolution exemption (instances.add_constraint calls
  `constraint.fields.set(...)` inside the same `mark_addition_transaction`
  scope as the ConstraintDefinition row's own INSERT)."""

from django.db import migrations

FORWARD = """
CREATE OR REPLACE FUNCTION app_runtime_definition_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE payload jsonb; owner_id uuid;
BEGIN
    IF TG_OP = 'INSERT' AND current_setting('app_platform.schema_evolution', true) = 'on' THEN
        RETURN NEW;
    END IF;
    IF TG_OP = 'UPDATE'
        AND (to_jsonb(NEW) - ARRAY['label', 'position']) = (to_jsonb(OLD) - ARRAY['label', 'position']) THEN
        RETURN NEW;
    END IF;
    IF TG_OP = 'UPDATE' AND current_setting('app_platform.schema_evolution', true) = 'on'
        AND (to_jsonb(NEW) - ARRAY['label', 'position', 'unique', 'indexed'])
            = (to_jsonb(OLD) - ARRAY['label', 'position', 'unique', 'indexed']) THEN
        RETURN NEW;
    END IF;
    IF TG_OP = 'DELETE' THEN payload := to_jsonb(OLD); ELSE payload := to_jsonb(NEW); END IF;
    IF TG_TABLE_NAME IN ('app_platform_fielddefinition', 'app_platform_constraintdefinition') THEN
        SELECT instance_id INTO owner_id FROM app_platform_modeldefinition
            WHERE id = (payload->>'model_id')::uuid;
    ELSE owner_id := (payload->>'instance_id')::uuid;
    END IF;
    PERFORM id FROM app_platform_appinstance WHERE id = owner_id FOR UPDATE;
    IF EXISTS (SELECT 1 FROM app_platform_runtimeprovision WHERE instance_id = owner_id) THEN
        RAISE EXCEPTION 'Reserved runtime definitions require a schema migration' USING ERRCODE = '23514';
    END IF;
    IF TG_OP = 'DELETE' THEN RETURN OLD; ELSE RETURN NEW; END IF;
END;
$$;
CREATE TRIGGER app_runtime_constraint_guard BEFORE INSERT OR UPDATE OR DELETE
ON app_platform_constraintdefinition
FOR EACH ROW EXECUTE FUNCTION app_runtime_definition_guard();

CREATE FUNCTION app_runtime_constraint_fields_guard() RETURNS trigger LANGUAGE plpgsql AS $$
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
        RAISE EXCEPTION 'Reserved runtime constraint fields require a schema migration' USING ERRCODE = '23514';
    END IF;
    IF TG_OP = 'DELETE' THEN RETURN OLD; ELSE RETURN NEW; END IF;
END;
$$;
CREATE TRIGGER app_runtime_constraint_fields_guard BEFORE INSERT OR UPDATE OR DELETE
ON app_platform_constraintdefinition_fields
FOR EACH ROW EXECUTE FUNCTION app_runtime_constraint_fields_guard();
"""

REVERSE = """
DROP TRIGGER app_runtime_constraint_fields_guard ON app_platform_constraintdefinition_fields;
DROP FUNCTION app_runtime_constraint_fields_guard();
DROP TRIGGER app_runtime_constraint_guard ON app_platform_constraintdefinition;

CREATE OR REPLACE FUNCTION app_runtime_definition_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE payload jsonb; owner_id uuid;
BEGIN
    IF TG_OP = 'INSERT' AND current_setting('app_platform.schema_evolution', true) = 'on' THEN
        RETURN NEW;
    END IF;
    IF TG_OP = 'UPDATE'
        AND (to_jsonb(NEW) - ARRAY['label', 'position']) = (to_jsonb(OLD) - ARRAY['label', 'position']) THEN
        RETURN NEW;
    END IF;
    IF TG_OP = 'UPDATE' AND current_setting('app_platform.schema_evolution', true) = 'on'
        AND (to_jsonb(NEW) - ARRAY['label', 'position', 'unique', 'indexed'])
            = (to_jsonb(OLD) - ARRAY['label', 'position', 'unique', 'indexed']) THEN
        RETURN NEW;
    END IF;
    IF TG_OP = 'DELETE' THEN payload := to_jsonb(OLD); ELSE payload := to_jsonb(NEW); END IF;
    IF TG_TABLE_NAME = 'app_platform_fielddefinition' THEN
        SELECT instance_id INTO owner_id FROM app_platform_modeldefinition
            WHERE id = (payload->>'model_id')::uuid;
    ELSE owner_id := (payload->>'instance_id')::uuid;
    END IF;
    PERFORM id FROM app_platform_appinstance WHERE id = owner_id FOR UPDATE;
    IF EXISTS (SELECT 1 FROM app_platform_runtimeprovision WHERE instance_id = owner_id) THEN
        RAISE EXCEPTION 'Reserved runtime definitions require a schema migration' USING ERRCODE = '23514';
    END IF;
    IF TG_OP = 'DELETE' THEN RETURN OLD; ELSE RETURN NEW; END IF;
END;
$$;
"""


class Migration(migrations.Migration):
    dependencies = [("app_platform", "0011_constraintdefinition")]
    operations = [migrations.RunSQL(FORWARD, REVERSE)]
