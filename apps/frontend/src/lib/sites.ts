/** Hosted websites and Node.js apps (ADR-0019 / ADR-0020), served by the proxy on their own port. */

export type SiteVersion = {
  id: string;
  number: number;
  original_filename: string;
  file_count: number;
  total_bytes: number;
  notes: string;
  uploaded_by_email: string;
  created_at: string;
};

export type Site = {
  id: string;
  organization: string;
  name: string;
  slug: string;
  status: "active" | "disabled";
  single_page_app: boolean;
  hostname: string | null;
  internet_hostname: string | null;
  lan_address: string;
  kind: "static" | "node";
  runtime_state: string;
  runtime_log: string;
  application: string | null;
  active_version: SiteVersion | null;
  path: string;
  public_port: number;
  created_at: string;
  updated_at: string;
  versions?: SiteVersion[];
};

export type InternetGateway = {
  enabled: boolean;
  can_manage: boolean;
  changed_at?: string | null;
  tunnel?: { state: string; log?: string };
  published?: {
    site: string;
    name: string;
    organization: string;
    internet_hostname: string;
    published_at: string | null;
  }[];
  /** Online sites without a public name, from every organization (Super Administrator only). */
  publishable?: { site: string; name: string; organization: string }[];
};

/** Where a site opens, built from the host the browser already uses for IntraForge (the backend gives only
 * the port, sites/serializers.py). A site with its own name on the shop network opens at that name. */
export function siteAddress(site: Pick<Site, "hostname" | "path" | "public_port">, currentHost: string): string {
  if (site.hostname) return `https://${site.hostname}:${site.public_port}/`;
  return `https://${currentHost}:${site.public_port}${site.path}`;
}

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

/** The runtime state a Node.js app's runner reports, in words. Websites have none. */
export function runtimeLabel(site: Pick<Site, "kind" | "status" | "runtime_state">): string | null {
  if (site.kind !== "node") return null;
  if (site.status === "disabled") return "Stopped (offline)";
  switch (site.runtime_state) {
    case "running":
      return "Running";
    case "failed":
      return "Failed to start";
    case "":
      return "Not started yet";
    default:
      return site.runtime_state.charAt(0).toUpperCase() + site.runtime_state.slice(1);
  }
}

/** A website address: lowercase letters, digits and hyphens, starting with a letter or digit. */
export function suggestSlug(name: string): string {
  return name
    .toLowerCase()
    .normalize("NFKD")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 50);
}
