"""Fixed SQL guards for published snapshots, identity, and ownership boundaries."""

from django.db import migrations

FORWARD = """
CREATE FUNCTION app_platform_immutable_version() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'Published app template versions are immutable' USING ERRCODE = '23514';
END;
$$;
CREATE TRIGGER app_version_immutable BEFORE UPDATE OR DELETE ON app_platform_apptemplateversion
FOR EACH ROW EXECUTE FUNCTION app_platform_immutable_version();

CREATE FUNCTION app_platform_identity_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE field_name text;
BEGIN
    FOREACH field_name IN ARRAY TG_ARGV LOOP
        IF to_jsonb(NEW)->field_name IS DISTINCT FROM to_jsonb(OLD)->field_name THEN
            RAISE EXCEPTION 'App definition identity/ownership is immutable' USING ERRCODE = '23514';
        END IF;
    END LOOP;
    RETURN NEW;
END;
$$;
CREATE TRIGGER app_template_identity BEFORE UPDATE ON app_platform_apptemplate
FOR EACH ROW EXECUTE FUNCTION app_platform_identity_guard('id', 'organization_id', 'created_by_id');
CREATE TRIGGER app_instance_identity BEFORE UPDATE ON app_platform_appinstance
FOR EACH ROW EXECUTE FUNCTION app_platform_identity_guard(
    'id', 'organization_id', 'project_id', 'source_version_id', 'created_by_id');
CREATE TRIGGER app_model_identity BEFORE UPDATE ON app_platform_modeldefinition
FOR EACH ROW EXECUTE FUNCTION app_platform_identity_guard('id', 'instance_id', 'key', 'source_definition_id');
CREATE TRIGGER app_field_identity BEFORE UPDATE ON app_platform_fielddefinition
FOR EACH ROW EXECUTE FUNCTION app_platform_identity_guard(
    'id', 'model_id', 'key', 'data_type', 'source_definition_id');
CREATE TRIGGER app_relationship_identity BEFORE UPDATE ON app_platform_relationshipdefinition
FOR EACH ROW EXECUTE FUNCTION app_platform_identity_guard(
    'id', 'instance_id', 'key', 'source_definition_id', 'source_model_id', 'target_model_id', 'kind');

CREATE FUNCTION app_platform_instance_boundary() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE project_org uuid; template_org uuid;
BEGIN
    SELECT w.organization_id INTO project_org FROM workspaces_project p
        JOIN workspaces_workspace w ON p.workspace_id = w.id WHERE p.id = NEW.project_id;
    SELECT t.organization_id INTO template_org FROM app_platform_apptemplateversion v
        JOIN app_platform_apptemplate t ON v.template_id = t.id WHERE v.id = NEW.source_version_id;
    IF project_org IS DISTINCT FROM NEW.organization_id OR template_org IS DISTINCT FROM NEW.organization_id THEN
        RAISE EXCEPTION 'App instance ownership boundary violation' USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER app_instance_boundary BEFORE INSERT OR UPDATE ON app_platform_appinstance
FOR EACH ROW EXECUTE FUNCTION app_platform_instance_boundary();

CREATE FUNCTION app_platform_relationship_boundary() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE source_instance uuid; target_instance uuid;
BEGIN
    SELECT instance_id INTO source_instance FROM app_platform_modeldefinition WHERE id = NEW.source_model_id;
    SELECT instance_id INTO target_instance FROM app_platform_modeldefinition WHERE id = NEW.target_model_id;
    IF source_instance IS DISTINCT FROM NEW.instance_id OR target_instance IS DISTINCT FROM NEW.instance_id THEN
        RAISE EXCEPTION 'App relationship boundary violation' USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER app_relationship_boundary BEFORE INSERT OR UPDATE ON app_platform_relationshipdefinition
FOR EACH ROW EXECUTE FUNCTION app_platform_relationship_boundary();
"""

REVERSE = """
DROP TRIGGER app_relationship_boundary ON app_platform_relationshipdefinition;
DROP FUNCTION app_platform_relationship_boundary();
DROP TRIGGER app_instance_boundary ON app_platform_appinstance;
DROP FUNCTION app_platform_instance_boundary();
DROP TRIGGER app_relationship_identity ON app_platform_relationshipdefinition;
DROP TRIGGER app_field_identity ON app_platform_fielddefinition;
DROP TRIGGER app_model_identity ON app_platform_modeldefinition;
DROP TRIGGER app_instance_identity ON app_platform_appinstance;
DROP TRIGGER app_template_identity ON app_platform_apptemplate;
DROP FUNCTION app_platform_identity_guard();
DROP TRIGGER app_version_immutable ON app_platform_apptemplateversion;
DROP FUNCTION app_platform_immutable_version();
"""


class Migration(migrations.Migration):
    dependencies = [("app_platform", "0001_initial")]
    operations = [migrations.RunSQL(FORWARD, REVERSE)]
