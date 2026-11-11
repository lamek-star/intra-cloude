import { useEffect, useState } from "react";
import {
  api,
  type AppFieldDefinition,
  type AppModelDefinition,
  type AppRelationshipDefinition,
} from "@/lib/api";

/** An installed application's runtime database is created as "App runtime <instance id>"
 * (app_platform/runtime_build.py), and its tables and columns are named after the definitions
 * they hold: m_<model id>, f_<field id>, r_<relationship id>, j_<join relationship id>, each id
 * without dashes (app_platform/runtime_plan.py physical_name). Those names are unique and safe, but
 * unreadable to the person managing the database. */
const RUNTIME_DATABASE = /^App runtime ([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})$/i;

export function runtimeInstanceId(databaseName: string): string | null {
  return RUNTIME_DATABASE.exec(databaseName)?.[1] ?? null;
}

type RuntimeSchema = {
  models: (AppModelDefinition & { fields: AppFieldDefinition[] })[];
  relationships: AppRelationshipDefinition[];
};

const hex = (id: string) => id.replaceAll("-", "").toLowerCase();

/** Physical name -> the label people gave it in the application's definition. */
export function runtimeLabels(schema: RuntimeSchema): Record<string, string> {
  const labels: Record<string, string> = {};
  for (const model of schema.models) {
    labels[`m_${hex(model.id)}`] = model.label;
    for (const field of model.fields) labels[`f_${hex(field.id)}`] = field.label;
  }
  for (const relation of schema.relationships) {
    labels[`r_${hex(relation.id)}`] = relation.label;
    labels[`j_${hex(relation.id)}`] = relation.label;
  }
  return labels;
}

/** Labels for a runtime database's tables and columns; empty for any other database, or when the
 * application's definition can't be read (the physical names still show). */
export function useRuntimeLabels(databaseName: string | null | undefined): Record<string, string> {
  const [labels, setLabels] = useState<Record<string, string>>({});
  const instanceId = databaseName ? runtimeInstanceId(databaseName) : null;

  useEffect(() => {
    if (!instanceId) return;
    let cancelled = false;
    api
      .get<RuntimeSchema>(`/app-instances/${instanceId}/schema/`)
      .then((schema) => !cancelled && setLabels(runtimeLabels(schema)))
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, [instanceId]);

  return labels;
}
