import { describe, expect, it } from "vitest";
import { limitPercent, limitText, parseLimit } from "./DailyLimit";

describe("daily request limit", () => {
  it("reads at a glance, with or without a limit", () => {
    expect(limitText(5000, 120)).toBe("120 of 5,000 today");
    expect(limitText(null, 7)).toBe("7 today, no limit");
    expect(limitText(undefined, undefined)).toBe("0 today, no limit");
  });
  it("shows the share used, capped at 100, and none without a limit", () => {
    expect(limitPercent(200, 50)).toBe(25);
    expect(limitPercent(10, 25)).toBe(100);
    expect(limitPercent(null, 25)).toBeNull();
  });
  it("accepts empty (no limit) or a whole number 1..10,000,000, with commas", () => {
    expect(parseLimit("")).toEqual({ value: null });
    expect(parseLimit("5,000")).toEqual({ value: 5000 });
    for (const bad of ["0", "-3", "1.5", "lots", "10000001"]) expect("error" in parseLimit(bad)).toBe(true);
  });
});
