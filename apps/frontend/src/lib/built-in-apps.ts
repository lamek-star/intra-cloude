// The customer application gallery's view of the backend catalog (app_platform/built_in_apps.py).
// The backend decides what is offered and what its release status is; the UI only presents that
// honestly. A preview is never dressed up as production-ready.

export type CatalogStatus = "qualified" | "partially_qualified" | "experimental";
export type RuntimeState = "ready" | "failed" | "pending" | "not_provisioned";

export type InstalledApp = { id: string; label: string; runtime: RuntimeState };

export type CatalogApp = {
  key: string;
  label: string;
  summary: string;
  highlights: string[];
  status: CatalogStatus;
  status_label: string;
  evidence: string[];
  installed: InstalledApp[];
};

/** Anything not fully qualified is a preview and must be labelled and acknowledged as one. */
export function isPreview(app: Pick<CatalogApp, "status">): boolean {
  return app.status !== "qualified";
}

export function statusTone(status: CatalogStatus): "success" | "warning" | "default" {
  if (status === "qualified") return "success";
  return status === "partially_qualified" ? "warning" : "default";
}

/** Where "Open" goes. The flagship has its own customer screens; a preview of any other built-in
 * application opens the generic app view. */
export function openHref(appKey: string, instanceId: string): string {
  return appKey === "spare_parts" ? `/apps/${instanceId}` : `/app-instances/${instanceId}`;
}

export function isReady(installed: InstalledApp): boolean {
  return installed.runtime === "ready";
}

export function runtimeLabel(state: RuntimeState): string {
  return state === "ready" ? "Ready" : "Setup incomplete";
}
