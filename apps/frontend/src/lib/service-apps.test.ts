import { describe, expect, it } from "vitest";
import { appHealthLines, type ServiceApp, type ServiceAppState } from "./service-apps";

function app(name: string, state: ServiceAppState | null, extra: Partial<ServiceApp> = {}): ServiceApp {
  return {
    id: name,
    app_type: "spare_parts",
    name: "Spare Parts",
    display_name: name,
    organization: { id: "o1", name: "Shop" },
    version: "1.4.0",
    enabled: true,
    removed: false,
    launch: { path: "/apps/spare-parts/", requires: "spareparts.view" },
    required_capabilities: [],
    config: null,
    health: state ? { state, reachable: state === "running", checked_at: "2026-11-03T10:00:00Z" } : null,
    can_open: true,
    can_configure: false,
    can_manage: false,
    created_at: "2026-10-31T10:00:00Z",
    ...extra,
  } as ServiceApp;
}

describe("appHealthLines", () => {
  it("maps running, degraded and stopped to healthy, warning and unavailable", () => {
    const lines = appHealthLines([app("Spare", "running"), app("Pharmacy", "degraded"), app("Pay", "stopped")]);
    expect(lines.map((l) => [l.name, l.status])).toEqual([
      ["Spare", "healthy"],
      ["Pharmacy", "warning"],
      ["Pay", "unavailable"],
    ]);
    expect(lines.every((l) => l.detail.length > 0)).toBe(true);
  });

  it("leaves out applications that are off by choice", () => {
    const lines = appHealthLines([
      app("Disabled", "disabled", { enabled: false }),
      app("Removed", "removed", { removed: true }),
      app("No probe", null),
    ]);
    expect(lines).toEqual([]);
  });

  it("reports an app whose service is missing from this installation as unavailable", () => {
    expect(appHealthLines([app("Ghost", "not_configured")])[0].status).toBe("unavailable");
  });
});
