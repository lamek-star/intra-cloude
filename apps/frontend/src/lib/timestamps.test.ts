import { describe, expect, it } from "vitest";
import { buildReceiveOperations, buildSaleOperations, platformTimestamp } from "./business";
import { formatDateTime } from "./format";
import { testSchema } from "./test-schema";

// Found by the real-stack browser journey: the API refuses `Date.toISOString()` ("...T13:35:00.646Z")
// with "expected an ISO datetime string". The platform's contract (databases/formats.py, shared with
// the CSV importer) is naive UTC, whole seconds. Backend side of this contract:
// app_platform/tests/test_transactions.py::MovementTimestampContractTests.

describe("platformTimestamp (the API's datetime contract)", () => {
  it("is naive UTC with whole seconds, never the form the API refuses", () => {
    const stamp = platformTimestamp(new Date("2026-09-19T13:35:00.646Z"));
    expect(stamp).toBe("2026-09-19T13:35:00");
    expect(stamp).toMatch(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$/);
    expect(stamp).not.toMatch(/[.Z]/);
  });

  it("is what every movement operation carries as occurred_at", () => {
    const now = new Date("2026-09-19T10:30:00.999Z");
    const schema = testSchema();
    const receive = buildReceiveOperations(schema, { partId: "p1", warehouseId: "w1", quantity: 1, now });
    const sale = buildSaleOperations(schema, {
      customerId: "c1",
      lines: [{ partId: "p1", warehouseId: "w1", quantity: 1, unitPriceCents: 100 }],
      invoiceNumber: "INV-1",
      now,
    });
    const movements = [...receive, ...sale].filter((o) => o.model === "M:stock_movement");
    expect(movements).toHaveLength(2);
    for (const op of movements) expect(op.data["F:stock_movement.occurred_at"]).toBe("2026-09-19T10:30:00");
  });
});

describe("formatDateTime", () => {
  it("shows a naive platform timestamp as UTC, not as the browser's local time", () => {
    // The same instant whether written naive (the platform's form) or with an explicit Z.
    expect(formatDateTime("2026-09-19T13:35:00")).toBe(formatDateTime("2026-09-19T13:35:00Z"));
    expect(formatDateTime("2026-09-19 13:35:00")).toBe(formatDateTime("2026-09-19T13:35:00Z"));
  });

  it("leaves an explicit offset alone and returns unparseable text unchanged", () => {
    expect(formatDateTime("2026-09-19T13:35:00+04:00")).not.toBe(formatDateTime("2026-09-19T13:35:00Z"));
    expect(formatDateTime("not a date")).toBe("not a date");
    expect(formatDateTime(null)).toBe("");
  });
});
