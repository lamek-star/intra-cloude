// A miniature Spare Parts schema for component tests: ids are opaque and resolved from keys, exactly
// as `loadSchema` does from an instance's own metadata. Test support only -- never imported by the app.
import type { AppFieldDefinition, AppModelDefinition, AppRelationshipDefinition } from "./api";
import { makeSchema } from "./business";

const FIELDS: Record<string, string[]> = {
  part: ["name", "list_price"],
  part_number: ["number", "source"],
  inventory: ["quantity_on_hand"],
  stock_movement: ["quantity_delta", "movement_type", "reference", "occurred_at"],
  purchase_order: ["status", "order_date", "total_amount"],
  purchase_order_line: ["quantity", "unit_cost", "line_total"],
  sales_order: ["status", "order_date", "total_amount"],
  sales_order_line: ["quantity", "unit_price", "line_total"],
  invoice: ["invoice_number", "invoice_date", "amount_due", "status"],
  warehouse: ["name"],
  supplier: ["name"],
  customer: ["name"],
};
const RELS: [string, string][] = [
  ["inventory", "part"],
  ["part_number", "part_number_part"],
  ["inventory", "warehouse"],
  ["stock_movement", "stock_movement_part"],
  ["stock_movement", "stock_movement_warehouse"],
  ["purchase_order", "supplier"],
  ["purchase_order_line", "purchase_order"],
  ["purchase_order_line", "purchase_order_line_part"],
  ["sales_order", "customer"],
  ["sales_order_line", "sales_order_line_sales_order"],
  ["sales_order_line", "sales_order_line_part"],
  ["invoice", "invoice_sales_order"],
];

// The Pharmacy edition's extra product fields (app_platform/reference_templates/pharmacy.py).
const MEDICINE_FIELDS = [
  "generic_name", "pack", "manufacturer", "country_of_origin", "prescription_required", "used_for",
  "storage_location", "reference_price", "reference_currency", "image_links", "source_url", "standard_cost",
];

export function testSchema({ pharmacy = false }: { pharmacy?: boolean } = {}) {
  const FIELDS_: Record<string, string[]> = pharmacy ? { ...FIELDS, part: [...FIELDS.part, ...MEDICINE_FIELDS] } : FIELDS;
  const keys = Object.keys(FIELDS_);
  const models: AppModelDefinition[] = keys.map((key) => ({
    id: `M:${key}`, instance: "i1", key, label: key, position: 0, source_definition_id: null,
  }));
  const fieldsByModelId: Record<string, AppFieldDefinition[]> = {};
  for (const [model, fields] of Object.entries(FIELDS_)) {
    fieldsByModelId[`M:${model}`] = fields.map((key) => ({
      id: `F:${model}.${key}`, model: `M:${model}`, key, label: key, data_type: "text", required: false,
      default_value: null, position: 0, source_definition_id: null,
    }));
  }
  const rels: AppRelationshipDefinition[] = RELS.map(([source, key]) => ({
    id: `R:${key}`, instance: "i1", key, label: key, position: 0, source_definition_id: null,
    source_model: `M:${source}`, target_model: "M:part", kind: "many_to_one", deletion_policy: "restrict",
  }));
  return makeSchema("i1", models, fieldsByModelId, rels);
}
