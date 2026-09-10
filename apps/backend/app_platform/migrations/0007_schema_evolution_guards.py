"""Teaches the 0004 control-plane triggers about Phase 3 step 3:

- `app_runtime_definition_guard` (app_platform's own model/field/
  relationship tables): `position` is now exempt from the "reserved
  runtime" block on UPDATE, same as `label` already was -- closing a real
  gap (step 2 exempted position at the Python layer but never updated this
  trigger, so reordering an already-provisioned instance's definitions was
  still silently rejected at the database level).
- `app_runtime_catalog_guard` (databases' own table/column/foreign-key/
  index/tenant-database tables): a new column/table/foreign-key row is
  what a live additive change actually creates, so this needed the exact
  same treatment.
- `app_runtime_receipt_guard` (`app_platform_runtimeprovision` itself):
  its UPDATE branch blocks *any* change at all once `completed_at IS NOT
  NULL`, which is stricter than the other two guards and doesn't
  distinguish "the plan/fingerprint/database identity is being rewritten"
  (never legitimate post-publication) from "`bindings` is being extended
  with one more model/field/relationship mapping" (exactly what a live
  addition does, and the only column `schema_evolution.py` ever touches --
  `plan` stays frozen by `app_platform_identity_guard`, by design, as the
  record of what the original fingerprint produced). Exempted narrowly:
  only when the session flag is set AND no column other than `bindings`
  actually changed: control falls through to the existing plan/
  fingerprint/database-boundary checks below rather than returning early,
  so those invariants still apply in full to the (unchanged) plan and
  database columns -- this isn't a second, weaker copy of them.

All three now exempt their respective operation only within a transaction
that has explicitly announced itself via
`SET LOCAL app_platform.schema_evolution = 'on'` -- set solely by
`app_platform.schema_evolution`'s own capability-checked, additive-only
code path (see that module), never by a bare INSERT/UPDATE. This keeps
every guard a real backstop against a buggy or malicious write bypassing
that path, rather than opening them unconditionally. DELETE is unchanged
in all three: nothing in this codebase deletes a definition, catalog, or
receipt row through this path, provisioned or not, and this step doesn't
add that capability."""

from django.db import migrations

FORWARD = """
CREATE OR REPLACE FUNCTION app_runtime_receipt_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE project_id uuid; database_project uuid;
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'Runtime receipts cannot be deleted' USING ERRCODE = '23514';
    END IF;
    IF TG_OP = 'UPDATE' AND OLD.completed_at IS NOT NULL THEN
        IF current_setting('app_platform.schema_evolution', true) = 'on'
            AND (to_jsonb(NEW) - 'bindings') = (to_jsonb(OLD) - 'bindings') THEN
            -- Sanctioned bindings-only extension: an unset/off session flag
            -- makes this inner condition NULL (not false), which PL/pgSQL's
            -- IF already treats as "don't take this branch" -- so falling
            -- through to RAISE below is the correct, safe default without
            -- needing a separate NULL-coalescing check.
            NULL;
        ELSE
            RAISE EXCEPTION 'Published runtime receipts are immutable' USING ERRCODE = '23514';
        END IF;
    END IF;
    SELECT a.project_id INTO project_id FROM app_platform_appinstance a
        WHERE a.id = NEW.instance_id FOR UPDATE;
    IF NEW.plan->>'instance_id' IS DISTINCT FROM NEW.instance_id::text
        OR NEW.plan->>'fingerprint' IS DISTINCT FROM NEW.fingerprint THEN
        RAISE EXCEPTION 'Runtime plan identity mismatch' USING ERRCODE = '23514';
    END IF;
    IF TG_OP = 'INSERT' AND NEW.database_id IS NOT NULL THEN
        RAISE EXCEPTION 'Runtime must be reserved before publication' USING ERRCODE = '23514';
    END IF;
    IF NEW.database_id IS NOT NULL THEN
        SELECT d.project_id INTO database_project FROM databases_tenantdatabase d
            WHERE d.id = NEW.database_id AND d.schema_name = NEW.plan->>'schema_name';
        IF database_project IS DISTINCT FROM project_id
            OR NEW.database_id::text IS DISTINCT FROM NEW.plan->>'database_id' THEN
            RAISE EXCEPTION 'Runtime database boundary mismatch' USING ERRCODE = '23514';
        END IF;
    END IF;
    RETURN NEW;
END;
$$;

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

REVERSE = """
CREATE OR REPLACE FUNCTION app_runtime_receipt_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE project_id uuid; database_project uuid;
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'Runtime receipts cannot be deleted' USING ERRCODE = '23514';
    END IF;
    IF TG_OP = 'UPDATE' AND OLD.completed_at IS NOT NULL THEN
        RAISE EXCEPTION 'Published runtime receipts are immutable' USING ERRCODE = '23514';
    END IF;
    SELECT a.project_id INTO project_id FROM app_platform_appinstance a
        WHERE a.id = NEW.instance_id FOR UPDATE;
    IF NEW.plan->>'instance_id' IS DISTINCT FROM NEW.instance_id::text
        OR NEW.plan->>'fingerprint' IS DISTINCT FROM NEW.fingerprint THEN
        RAISE EXCEPTION 'Runtime plan identity mismatch' USING ERRCODE = '23514';
    END IF;
    IF TG_OP = 'INSERT' AND NEW.database_id IS NOT NULL THEN
        RAISE EXCEPTION 'Runtime must be reserved before publication' USING ERRCODE = '23514';
    END IF;
    IF NEW.database_id IS NOT NULL THEN
        SELECT d.project_id INTO database_project FROM databases_tenantdatabase d
            WHERE d.id = NEW.database_id AND d.schema_name = NEW.plan->>'schema_name';
        IF database_project IS DISTINCT FROM project_id
            OR NEW.database_id::text IS DISTINCT FROM NEW.plan->>'database_id' THEN
            RAISE EXCEPTION 'Runtime database boundary mismatch' USING ERRCODE = '23514';
        END IF;
    END IF;
    RETURN NEW;
END;
$$;

CREATE OR REPLACE FUNCTION app_runtime_definition_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE payload jsonb; owner_id uuid;
BEGIN
    IF TG_OP = 'UPDATE' AND (to_jsonb(NEW) - 'label') = (to_jsonb(OLD) - 'label') THEN
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
    dependencies = [("app_platform", "0006_ordering_and_defaults")]
    operations = [migrations.RunSQL(FORWARD, REVERSE)]
