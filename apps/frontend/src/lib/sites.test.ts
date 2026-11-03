import { describe, expect, it } from "vitest";
import { runtimeLabel, siteAddress, suggestSlug } from "./sites";

describe("sites helpers", () => {
  it("builds the address from the host IntraForge is opened on, or from the site's own name", () => {
    const site = { hostname: null, path: "/price-list/", public_port: 8445 };
    expect(siteAddress(site, "192.168.1.20")).toBe("https://192.168.1.20:8445/price-list/");
    expect(siteAddress({ ...site, hostname: "myshop.lan" }, "localhost")).toBe("https://myshop.lan:8445/");
  });

  it("suggests an address the backend accepts", () => {
    expect(suggestSlug("Shop Price List!")).toBe("shop-price-list");
    expect(suggestSlug("  --Café 2026-- ")).toBe("cafe-2026");
  });

  it("describes a Node.js app's state and nothing for a website", () => {
    expect(runtimeLabel({ kind: "static", status: "active", runtime_state: "" })).toBeNull();
    expect(runtimeLabel({ kind: "node", status: "active", runtime_state: "running" })).toBe("Running");
    expect(runtimeLabel({ kind: "node", status: "active", runtime_state: "failed" })).toBe("Failed to start");
    expect(runtimeLabel({ kind: "node", status: "disabled", runtime_state: "running" })).toBe("Stopped (offline)");
  });
});
