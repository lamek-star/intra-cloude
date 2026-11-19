import { describe, expect, it } from "vitest";
import { isStale, keyStatus } from "./_client";

const NOW = Date.parse("2026-11-18T12:00:00Z");
const key = (over: Partial<Parameters<typeof keyStatus>[0]> = {}) => ({
  id: "k1",
  created_at: "2026-11-17T12:00:00Z",
  last_used_at: null,
  expires_at: null,
  revoked_at: null,
  ...over,
});

describe("API key status", () => {
  it("is active, revoked or expired, revoked winning", () => {
    expect(keyStatus(key(), NOW).label).toBe("Active");
    expect(keyStatus(key({ expires_at: "2026-11-01T00:00:00Z" }), NOW).label).toBe("Expired");
    expect(keyStatus(key({ revoked_at: "2026-11-02T00:00:00Z", expires_at: "2026-11-01T00:00:00Z" }), NOW).label).toBe("Revoked");
  });

  it("flags an active key unused for over 30 days, counting from creation when never used", () => {
    expect(isStale(key(), NOW)).toBe(false);
    expect(isStale(key({ created_at: "2026-10-01T00:00:00Z" }), NOW)).toBe(true);
    expect(isStale(key({ created_at: "2026-10-01T00:00:00Z", last_used_at: "2026-11-15T00:00:00Z" }), NOW)).toBe(false);
    expect(isStale(key({ created_at: "2026-10-01T00:00:00Z", revoked_at: "2026-10-02T00:00:00Z" }), NOW)).toBe(false);
  });
});
