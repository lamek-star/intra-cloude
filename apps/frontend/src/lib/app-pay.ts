import type { ResourceGrant } from "@/lib/api";
import type { ServiceApp } from "@/lib/service-apps";

/** IntraForge Pay for an Application (ADR-0020 decision 2, service_apps/app_pay.py): its credential may ask
 * Pay for a payment once its service account holds ``ifpay.checkout`` on its own organization's Pay. */
export const PAY_CHECKOUT = "ifpay.checkout";
export const SERVICE_APP_RESOURCE = "service_app";

export type AppPayAccess =
  | { state: "no_pay" }
  | { state: "several_pays"; count: number }
  | { state: "allowed" | "not_allowed"; pay: ServiceApp; grants: ResourceGrant[] };

function isActive(g: ResourceGrant): boolean {
  return !g.expires_at || new Date(g.expires_at) > new Date();
}

/** Whether this application may take Pay payments. Only the Pay installed in the application's own
 * organization counts (the backend picks that one, and refuses when there is more than one). */
export function appPayAccess(organizationId: string, apps: ServiceApp[], grants: ResourceGrant[]): AppPayAccess {
  const pays = apps.filter((a) => a.app_type === "intraforge_pay" && !a.removed && a.organization.id === organizationId);
  if (pays.length === 0) return { state: "no_pay" };
  if (pays.length > 1) return { state: "several_pays", count: pays.length };
  const pay = pays[0];
  const held = grants.filter(
    (g) => g.permission === PAY_CHECKOUT && g.resource_type === SERVICE_APP_RESOURCE && g.resource_id === pay.id && isActive(g),
  );
  return { state: held.length > 0 ? "allowed" : "not_allowed", pay, grants: held };
}
