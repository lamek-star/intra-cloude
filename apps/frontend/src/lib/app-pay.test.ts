import { describe, expect, it } from "vitest";
import type { ResourceGrant } from "./api";
import { appPayAccess } from "./app-pay";
import type { ServiceApp } from "./service-apps";

const ORG = "org-1";

function pay(id: string, org = ORG, removed = false): ServiceApp {
  return { id, app_type: "intraforge_pay", removed, organization: { id: org, name: "Shop" } } as ServiceApp;
}

function grant(resourceId: string, extra: Partial<ResourceGrant> = {}): ResourceGrant {
  return {
    id: `g-${resourceId}`,
    permission: "ifpay.checkout",
    resource_type: "service_app",
    resource_id: resourceId,
    granted_by: null,
    expires_at: null,
    created_at: "2026-11-04T00:00:00Z",
    ...extra,
  };
}

describe("appPayAccess", () => {
  it("says when the organization has no Pay, ignoring other organizations' and removed ones", () => {
    expect(appPayAccess(ORG, [pay("p2", "org-2"), pay("p3", ORG, true)], []).state).toBe("no_pay");
  });

  it("refuses to pick when more than one Pay is installed", () => {
    expect(appPayAccess(ORG, [pay("p1"), pay("p2")], [])).toEqual({ state: "several_pays", count: 2 });
  });

  it("is allowed only by an active ifpay.checkout grant on this Pay", () => {
    const apps = [pay("p1")];
    expect(appPayAccess(ORG, apps, []).state).toBe("not_allowed");
    expect(appPayAccess(ORG, apps, [grant("other-pay")]).state).toBe("not_allowed");
    expect(appPayAccess(ORG, apps, [grant("p1", { permission: "ifpay.view" })]).state).toBe("not_allowed");
    expect(appPayAccess(ORG, apps, [grant("p1", { expires_at: "2020-01-01T00:00:00Z" })]).state).toBe("not_allowed");
    const allowed = appPayAccess(ORG, apps, [grant("p1")]);
    expect(allowed.state).toBe("allowed");
    expect(allowed.state === "allowed" && allowed.grants.map((g) => g.id)).toEqual(["g-p1"]);
  });
});
