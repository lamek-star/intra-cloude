"""Post-Phase-3 Integration Enablement, Part 2/3: teaches two of the
control-plane trigger guards about the new field `unique`/`indexed`
retrofit path (instances.mark_field_unique/mark_field_indexed ->
schema_evolution.set_field_unique/set_field_indexed), the same class of
gap 0007 already found and fixed once for step 3's add_model/add_field/
add_relationship additions -- these are UPDATEs to something that already
exists, not INSERTs, so 0007's own fixes don't cover them:

- `app_runtime_definition_guard`: its UPDATE branch exempts only a
  label/position-only change, unconditionally. Retrofitting uniqueness/
  indexing onto an existing, already-provisioned field updates
  `unique`/`indexed` on `app_platform_fielddefinition` -- previously
  blocked outright ("Reserved runtime definitions require a schema
  migration"), regardless of going through the properly capability-
  checked schema_evolution.py path. Exempted narrowly: only when the
  session flag is set (set solely by
  schema_evolution.mark_addition_transaction(), same as every other
  sanctioned write in this file) AND no column other than label/
  position/unique/indexed actually changed.
- `app_runtime_catalog_guard`: retrofitting uniqueness also updates
  `databases_dbcolumn.is_unique` on an already-existing (not just-
  inserted) column -- the INSERT-only exemption 0007 added doesn't cover
  this either. Exempted the same way, narrowed to `is_unique` being the
  only thing that changed.

Both new exemptions are positive gates on an early RETURN (`IF ... AND
current_setting(...) = 'on' AND ... THEN RETURN NEW`), not a negation --
deliberately avoiding the exact NULL-propagation trap 0007's own
app_runtime_receipt_guard fix hit and had to correct (an unset session
flag makes `current_setting(..., true)` return SQL NULL, not 'off'; used
as a positive AND-gate here, PL/pgSQL's IF already treats that NULL as
"don't take this branch" -- the safe, correct default -- with no risk of
the earlier bug's NOT()-inversion trap)."""

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

CREATE OR REPLACE FUNCTION app_runtime_catalog_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP = 'INSERT' AND current_setting('app_platform.schema_evolution', true) = 'on' THEN
        RETURN NEW;
    END IF;
    IF TG_TABLE_NAME = 'databases_tenantdatabase' AND TG_OP = 'UPDATE'
        AND (to_jsonb(NEW) - ARRAY['name','environment_id']) = (to_jsonb(OLD) - ARRAY['name','environment_id']) THEN
        RETURN NEW;
    END IF;
    IF TG_TABLE_NAME = 'databases_dbcolumn' AND TG_OP = 'UPDATE'
        AND current_setting('app_platform.schema_evolution', true) = 'on'
        AND (to_jsonb(NEW) - 'is_unique') = (to_jsonb(OLD) - 'is_unique') THEN
        RETURN NEW;
    END IF;
    IF (TG_OP <> 'INSERT' AND app_runtime_catalog_owned(TG_TABLE_NAME, to_jsonb(OLD)))
        OR (TG_OP <> 'DELETE' AND app_runtime_catalog_owned(TG_TABLE_NAME, to_jsonb(NEW))) THEN
        RAISE EXCEPTION 'Managed runtime catalog requires a schema migration' USING ERRCODE = '23514';
    END IF;
    IF TG_OP = 'DELETE' THEN RETURN OLD; ELSE RETURN NEW; END IF;
END;
$$;
"""

REVERSE = """
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

CREATE OR REPLACE FUNCTION app_runtime_catalog_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP = 'INSERT' AND current_setting('app_platform.schema_evolution', true) = 'on' THEN
        RETURN NEW;
    END IF;
    IF TG_TABLE_NAME = 'databases_tenantdatabase' AND TG_OP = 'UPDATE'
        AND (to_jsonb(NEW) - ARRAY['name','environment_id']) = (to_jsonb(OLD) - ARRAY['name','environment_id']) THEN
        RETURN NEW;
    END IF;
    IF (TG_OP <> 'INSERT' AND app_runtime_catalog_owned(TG_TABLE_NAME, to_jsonb(OLD)))
        OR (TG_OP <> 'DELETE' AND app_runtime_catalog_owned(TG_TABLE_NAME, to_jsonb(NEW))) THEN
        RAISE EXCEPTION 'Managed runtime catalog requires a schema migration' USING ERRCODE = '23514';
    END IF;
    IF TG_OP = 'DELETE' THEN RETURN OLD; ELSE RETURN NEW; END IF;
END;
$$;
"""


class Migration(migrations.Migration):
    dependencies = [("app_platform", "0008_field_indexing_and_uniqueness")]
    operations = [migrations.RunSQL(FORWARD, REVERSE)]
