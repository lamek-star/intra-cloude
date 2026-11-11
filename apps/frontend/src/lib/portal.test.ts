import { afterEach, describe, expect, it, vi } from "vitest";
import { ordinal, portalApi, rulesInWords } from "./portal";

describe("the customer portal helpers", () => {
  afterEach(() => vi.restoreAllMocks());

  it("says the shop's rewards in plain words, leaving out the ones that are off", () => {
    expect(rulesInWords({ welcome_points: 30, referral_points: 0, birthday_points: 25, every_nth_free: 10 })).toEqual([
      "30 points when the shop approves you",
      "Every 10th title free",
      "25 points in your birthday month",
    ]);
    expect(rulesInWords({ welcome_points: 0, referral_points: 0, birthday_points: 0, every_nth_free: 0 })).toEqual([]);
  });

  it("writes ordinals", () => {
    expect([1, 2, 3, 4, 11, 12, 13, 21, 22, 103].map(ordinal)).toEqual(["1st", "2nd", "3rd", "4th", "11th", "12th", "13th", "21st", "22nd", "103rd"]);
  });

  it("marks every change with the portal header and never sends IntraForge's CSRF token", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({ ok: true }), { status: 200 }));
    await portalApi.signOut("shop-1");
    await portalApi.categories("shop-1");
    const [postUrl, post] = fetchMock.mock.calls[0];
    const [, get] = fetchMock.mock.calls[1];
    expect(postUrl).toBe("/api/v1/portal/shop-1/logout/");
    expect((post?.headers as Record<string, string>)["X-Portal-Request"]).toBe("1");
    expect((post?.headers as Record<string, string>)["X-CSRFToken"]).toBeUndefined();
    expect((get?.headers as Record<string, string>)["X-Portal-Request"]).toBeUndefined();
  });

  it("turns a refusal into an error carrying the server's words", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({ detail: "Wrong phone number or password." }), { status: 401 }));
    await expect(portalApi.signIn("shop-1", "0911", "x")).rejects.toThrow("Wrong phone number or password.");
  });
});
