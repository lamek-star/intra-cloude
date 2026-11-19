import { describe, expect, it } from "vitest";
import { errorRate, fillDays } from "./_client";
import { statusHint, statusTone } from "../api-logs/_client";

describe("usage helpers", () => {
  it("error rate has one decimal and a dash for no requests", () => {
    expect(errorRate(0, 0)).toBe("—");
    expect(errorRate(3, 1)).toBe("33.3%");
  });
  it("fills every day of the window, quiet days as zero", () => {
    const days = fillDays([{ date: "2026-11-17", requests: 4, errors: 1 }], 3, "2026-11-15T12:00:00Z");
    expect(days.map((d) => d.date)).toEqual(["2026-11-16", "2026-11-17", "2026-11-18"]);
    expect(days.map((d) => d.requests)).toEqual([0, 4, 0]);
  });
});

describe("log status", () => {
  it("colours and explains answers for an owner", () => {
    expect([statusTone(200), statusTone(403), statusTone(502)]).toEqual(["success", "warning", "danger"]);
    expect(statusHint(403)).toMatch(/permissions/);
    expect(statusHint(200)).toBe("");
  });
});
