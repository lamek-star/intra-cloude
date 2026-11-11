import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { ApiError, type AppFieldDefinition, type AppModelDefinition, type AppRelationshipDefinition } from "./api";
import {
  buildReceiveIntent,
  buildSaleIntent,
  explainOperationError,
  formatMoney,
  makeSchema,
  newInvoiceNumber,
  normalizeSearchKey,
  parseMoney,
  parseQuantity,
  saleTotalCents,
  toPayload,
} from "./business";

// A miniature of the Spare Parts template's shape: ids are opaque and resolved from keys, exactly
// as loadSchema does from the instance's own metadata.
const MODELS = ["part", "warehouse", "supplier", "customer", "stock_movement", "purchase_order", "purchase_order_line", "sales_order", "sales_order_line", "invoice"];
const FIELDS: Record<string, string[]> = {
  part: ["name"],
  stock_movement: ["quantity_delta", "movement_type", "reference", "occurred_at"],
  purchase_order: ["status", "order_date", "total_amount"],
  purchase_order_line: ["quantity", "unit_cost", "line_total"],
  sales_order: ["status", "order_date", "total_amount"],
  sales_order_line: ["quantity", "unit_price", "line_total"],
  invoice: ["invoice_number", "invoice_date", "amount_due", "status"],
};
const RELS: [string, string][] = [
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

function schema() {
  const models: AppModelDefinition[] = MODELS.map((key) => ({
    id: `M:${key}`, instance: "i1", key, label: key, position: 0, source_definition_id: null,
  }));
  const fieldsByModelId: Record<string, AppFieldDefinition[]> = {};
  for (const [model, keys] of Object.entries(FIELDS)) {
    fieldsByModelId[`M:${model}`] = keys.map((key) => ({
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

const NOW = new Date("2026-09-19T10:30:00.000Z");

describe("schema", () => {
  it("resolves model, field and relationship ids from keys", () => {
    const s = schema();
    expect(s.modelId("part")).toBe("M:part");
    expect(s.id("part", "name")).toBe("F:part.name");
    expect(s.id("stock_movement", "stock_movement_part")).toBe("R:stock_movement_part");
  });

  it("fails loudly for an unknown section or field instead of guessing an id", () => {
    const s = schema();
    expect(() => s.modelId("nope")).toThrow(/no "nope" section/);
    expect(() => s.id("part", "nope")).toThrow(/no "nope"/);
  });

  it("drops undefined values from a payload and keys the rest by id", () => {
    expect(toPayload(schema(), "part", { name: "Oil Filter", ghost: undefined } as Record<string, unknown>)).toEqual({
      "F:part.name": "Oil Filter",
    });
  });
});

describe("money and quantities", () => {
  it("parses money to cents and rejects everything else", () => {
    expect(parseMoney("15")).toBe(1500);
    expect(parseMoney("15.5")).toBe(1550);
    expect(parseMoney("15.05")).toBe(1505);
    expect(parseMoney(" 0.99 ")).toBe(99);
    for (const bad of ["", "-1", "1.234", "abc", "1,5", "1e3"]) expect(parseMoney(bad)).toBeNull();
  });

  it("formats cents with two decimals without floating-point drift", () => {
    expect(formatMoney(7500)).toBe("75.00");
    expect(formatMoney(5)).toBe("0.05");
    expect(formatMoney(1505 * 3)).toBe("45.15");
  });

  it("accepts only whole quantities of at least 1", () => {
    expect(parseQuantity("100")).toBe(100);
    for (const bad of ["", "0", "-5", "1.5", "abc", "1234567890"]) expect(parseQuantity(bad)).toBeNull();
  });

  it("builds a dated, readable invoice number", () => {
    expect(newInvoiceNumber(NOW, () => 0)).toBe("INV-20260919-00000");
    expect(newInvoiceNumber(NOW)).toMatch(/^INV-20260919-[0-9A-Z]{5}$/);
  });
});

describe("receive stock", () => {
  it("without a supplier is one intent carrying the received quantity", () => {
    const intent = buildReceiveIntent({ partId: "p1", warehouseId: "w1", quantity: 100, now: NOW });
    expect(intent).toEqual({ part: "p1", warehouse: "w1", quantity: 100, occurred_at: "2026-09-19T10:30:00" });
  });

  it("with a supplier names the supplier and the unit cost in dollars, and trims the reference", () => {
    const intent = buildReceiveIntent({
      partId: "p1", warehouseId: "w1", quantity: 10, supplierId: "s1", unitCostCents: 250, reference: " GRN-7 ", now: NOW,
    });
    expect(intent).toMatchObject({ supplier: "s1", unit_cost: "2.50", reference: "GRN-7", quantity: 10 });
  });

  it("never sends a stock level or a movement: the browser only states the intent", () => {
    const intent = buildReceiveIntent({ partId: "p1", warehouseId: "w1", quantity: 5, now: NOW });
    expect(JSON.stringify(intent)).not.toMatch(/quantity_on_hand|inventory|quantity_delta|movement_type/);
  });
});

describe("sell stock", () => {
  const line = { partId: "p1", warehouseId: "w1", quantity: 5, unitPriceCents: 1500 };

  it("is the customer, the invoice number and one entry per item -- nothing the server should decide", () => {
    const intent = buildSaleIntent({ customerId: "c1", lines: [line], invoiceNumber: "INV-1", now: NOW });
    expect(intent).toEqual({
      customer: "c1",
      invoice_number: "INV-1",
      occurred_at: "2026-09-19T10:30:00",
      lines: [{ part: "p1", warehouse: "w1", quantity: 5, unit_price: "15.00" }],
    });
    expect(JSON.stringify(intent)).not.toMatch(/quantity_delta|movement_type|amount_due|total_amount/);
  });

  it("handles several items and totals them in cents", () => {
    const lines = [line, { partId: "p2", warehouseId: "w2", quantity: 3, unitPriceCents: 199 }];
    expect(saleTotalCents(lines)).toBe(7500 + 597);
    const intent = buildSaleIntent({ customerId: "c1", lines, invoiceNumber: "INV-2", now: NOW });
    expect(intent.lines).toHaveLength(2);
    expect(intent.lines[1]).toEqual({ part: "p2", warehouse: "w2", quantity: 3, unit_price: "1.99" });
  });
});

describe("explainOperationError", () => {
  const err = (status: number, body: unknown) => new ApiError(status, body);

  it("explains an oversell in plain words and says nothing changed", () => {
    const text = explainOperationError(err(400, { detail: "this quantity ledger balance would go negative (-1)", operation: 2 }));
    expect(text).toContain("not enough stock");
    expect(text).toContain("Nothing was changed");
    expect(text).not.toMatch(/ledger|negative|operation/i);
  });

  it("maps permission, conflict and server errors without leaking internals", () => {
    expect(explainOperationError(err(403, {}))).toContain("permission");
    expect(explainOperationError(err(409, { error: { message: { detail: "Idempotency-Key ..." } } }))).toContain("different details");
    expect(explainOperationError(err(500, "Traceback"))).toContain("try again");
    expect(explainOperationError(new Error("boom"))).not.toContain("boom");
  });
});

describe("normalizeSearchKey (ranking only; the server does the search)", () => {
  it("treats the flagship examples as one key", () => {
    for (const v of ["04465-0K290", "044650K290", "04465 0K290", " 04465\u00a00k290 "]) {
      expect(normalizeSearchKey(v)).toBe("044650K290");
    }
  });
});

// The same vectors the backend runs against Python and PostgreSQL (databases/tests/
// test_normalization_vectors.py). One rule, three implementations, one fixture.
describe("normalizeSearchKey against the shared cross-language vectors", () => {
  const fixture = resolve(process.cwd(), "../../tests/fixtures/part-number-normalization.json");
  const { vectors } = JSON.parse(readFileSync(fixture, "utf-8")) as {
    vectors: { input: string; key: string; why: string }[];
  };

  it("loads the fixture", () => {
    expect(vectors.length).toBeGreaterThanOrEqual(15);
  });

  for (const vector of vectors) {
    it(vector.why, () => {
      expect(normalizeSearchKey(vector.input)).toBe(vector.key);
    });
  }
});
