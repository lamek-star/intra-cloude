import { api } from "@/lib/api";

/** Separately deployed applications IntraForge registers and serves (ADR-0018). */
export type ServiceAppState = "running" | "degraded" | "stopped" | "disabled" | "removed" | "not_configured";

export type ServiceAppConfig = {
  shopName: string;
  address: string;
  phone: string;
  email: string;
  taxRegistration: string;
  currency: string;
  defaultTaxBp: number;
  quotationValidityDays: number;
  invoiceDueDays: number;
  quotationTerms: string;
  invoiceNotes: string;
};

export type ServiceApp = {
  id: string;
  app_type: string;
  name: string;
  display_name: string;
  organization: { id: string; name: string };
  version: string;
  enabled: boolean;
  removed: boolean;
  launch: { path: string | null; requires: string };
  required_capabilities: string[];
  config: ServiceAppConfig | null;
  health: {
    state: ServiceAppState;
    reachable: boolean | null;
    checked_at: string;
    last_seen_at?: string | null;
    detail?: string;
  } | null;
  can_open: boolean;
  can_configure: boolean;
  can_manage: boolean;
  created_at: string;
};

export type InstallableApp = {
  deployment: string;
  app_type: string;
  product_name: string;
  description: string;
  organizations: string[];
};

export type ServiceAppList = { results: ServiceApp[]; available: InstallableApp[] };

export const STATE_LABEL: Record<ServiceAppState, string> = {
  running: "Running",
  degraded: "Not responding",
  stopped: "Stopped",
  disabled: "Disabled",
  removed: "Removed (data kept)",
  not_configured: "Service missing",
};

export const STATE_TONE: Record<ServiceAppState, "success" | "warning" | "danger" | "default"> = {
  running: "success",
  degraded: "warning",
  stopped: "danger",
  disabled: "default",
  removed: "default",
  not_configured: "danger",
};

export const STATE_HELP: Partial<Record<ServiceAppState, string>> = {
  degraded: "It answered recently but not just now. Wait a moment, or restart services from the IntraForge Control Center.",
  stopped: "Its service is not running. Start or restart IntraForge from the Control Center.",
  not_configured: "This installation does not include this application's service.",
};

/** "Open": IntraForge mints the application session (an HttpOnly cookie on the application's
 * path) and the browser goes there. Nothing about the user travels in the address. */
export async function openServiceApp(id: string): Promise<void> {
  const { url } = await api.post<{ url: string }>(`/service-apps/${id}/launch/`);
  window.location.assign(url);
}
