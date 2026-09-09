"""Fixed control-plane guards; tenant DDL continues through validated services."""

from django.db import migrations

FORWARD = """
CREATE FUNCTION app_runtime_receipt_guard() RETURNS trigger LANGUAGE plpgsql AS $$
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
CREATE TRIGGER app_runtime_receipt BEFORE INSERT OR UPDATE OR DELETE ON app_platform_runtimeprovision
FOR EACH ROW EXECUTE FUNCTION app_runtime_receipt_guard();
CREATE TRIGGER app_runtime_identity BEFORE UPDATE ON app_platform_runtimeprovision
FOR EACH ROW EXECUTE FUNCTION app_platform_identity_guard(
    'instance_id', 'plan', 'fingerprint', 'created_by_id', 'created_at');

CREATE FUNCTION app_runtime_definition_guard() RETURNS trigger LANGUAGE plpgsql AS $$
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
CREATE TRIGGER app_runtime_model_guard BEFORE INSERT OR UPDATE OR DELETE ON app_platform_modeldefinition
FOR EACH ROW EXECUTE FUNCTION app_runtime_definition_guard();
CREATE TRIGGER app_runtime_field_guard BEFORE INSERT OR UPDATE OR DELETE ON app_platform_fielddefinition
FOR EACH ROW EXECUTE FUNCTION app_runtime_definition_guard();
CREATE TRIGGER app_runtime_relation_guard BEFORE INSERT OR UPDATE OR DELETE ON app_platform_relationshipdefinition
FOR EACH ROW EXECUTE FUNCTION app_runtime_definition_guard();

CREATE FUNCTION app_runtime_catalog_owned(kind text, payload jsonb) RETURNS boolean LANGUAGE sql AS $$
    SELECT EXISTS (
        SELECT 1 FROM app_platform_runtimeprovision WHERE database_id = CASE kind
            WHEN 'databases_tenantdatabase' THEN (payload->>'id')::uuid
            WHEN 'databases_dbtable' THEN (payload->>'tenant_database_id')::uuid
            WHEN 'databases_dbcolumn' THEN (
                SELECT tenant_database_id FROM databases_dbtable WHERE id = (payload->>'table_id')::uuid)
            WHEN 'databases_dbforeignkey' THEN (
                SELECT t.tenant_database_id FROM databases_dbtable t JOIN databases_dbcolumn c ON c.table_id=t.id
                WHERE c.id = (payload->>'column_id')::uuid)
            WHEN 'databases_dbindex' THEN (
                SELECT tenant_database_id FROM databases_dbtable WHERE id = (payload->>'table_id')::uuid)
        END
    );
$$;
CREATE FUNCTION app_runtime_catalog_guard() RETURNS trigger LANGUAGE plpgsql AS $$
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
CREATE TRIGGER app_runtime_database_catalog BEFORE UPDATE OR DELETE ON databases_tenantdatabase
FOR EACH ROW EXECUTE FUNCTION app_runtime_catalog_guard();
CREATE TRIGGER app_runtime_table_catalog BEFORE INSERT OR UPDATE OR DELETE ON databases_dbtable
FOR EACH ROW EXECUTE FUNCTION app_runtime_catalog_guard();
CREATE TRIGGER app_runtime_column_catalog BEFORE INSERT OR UPDATE OR DELETE ON databases_dbcolumn
FOR EACH ROW EXECUTE FUNCTION app_runtime_catalog_guard();
CREATE TRIGGER app_runtime_fk_catalog BEFORE INSERT OR UPDATE OR DELETE ON databases_dbforeignkey
FOR EACH ROW EXECUTE FUNCTION app_runtime_catalog_guard();
CREATE TRIGGER app_runtime_index_catalog BEFORE INSERT OR UPDATE OR DELETE ON databases_dbindex
FOR EACH ROW EXECUTE FUNCTION app_runtime_catalog_guard();
"""

REVERSE = """
DROP TRIGGER app_runtime_index_catalog ON databases_dbindex;
DROP TRIGGER app_runtime_fk_catalog ON databases_dbforeignkey;
DROP TRIGGER app_runtime_column_catalog ON databases_dbcolumn;
DROP TRIGGER app_runtime_table_catalog ON databases_dbtable;
DROP TRIGGER app_runtime_database_catalog ON databases_tenantdatabase;
DROP FUNCTION app_runtime_catalog_guard();
DROP FUNCTION app_runtime_catalog_owned(text, jsonb);
DROP TRIGGER app_runtime_relation_guard ON app_platform_relationshipdefinition;
DROP TRIGGER app_runtime_field_guard ON app_platform_fielddefinition;
DROP TRIGGER app_runtime_model_guard ON app_platform_modeldefinition;
DROP FUNCTION app_runtime_definition_guard();
DROP TRIGGER app_runtime_identity ON app_platform_runtimeprovision;
DROP TRIGGER app_runtime_receipt ON app_platform_runtimeprovision;
DROP FUNCTION app_runtime_receipt_guard();
"""


class Migration(migrations.Migration):
    dependencies = [("app_platform", "0003_runtime_provision")]
    operations = [migrations.RunSQL(FORWARD, REVERSE)]
