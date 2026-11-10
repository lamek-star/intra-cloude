/** Movie Shop (ADR-0022): types and calls for the owner's catalogue. The films stay on the shop's drives; IntraForge
 * keeps their names, sizes, covers and prices. */
import { api, type Paginated } from "./api";

export type MovieShop = {
  id: string;
  organization: string;
  project: string;
  name: string;
  default_price: number;
  category_prices: Record<string, number>;
  agent_seen_at: string | null;
  agent: { computer: string; version: string };
  titles: number;
  can_manage: boolean;
  created_at: string;
};

export type MovieLibrary = {
  id: string;
  name: string;
  path: string;
  kind: "fixed" | "removable" | "network";
  total_bytes: number | null;
  free_bytes: number | null;
  titles: number;
  scan_requested: boolean;
  last_scan_at: string | null;
  last_scan_message: string;
};

export type MovieCategory = { name: string; count: number; size_bytes: number };

export type MovieTitle = {
  id: string;
  library: string;
  relative_path: string;
  category: string;
  title: string;
  year: number | null;
  kind: "movie" | "series";
  size_bytes: number;
  episodes: number;
  has_cover: boolean;
  price: number;
  own_price: number | null;
  hidden: boolean;
  description: string;
};

export type AgentDrive = { root: string; label: string; kind: MovieLibrary["kind"]; total_bytes: number | null; free_bytes: number | null; folders: string[] };
export type AgentReport = { agent_seen_at: string | null; drives: AgentDrive[]; computer?: string; agent_version?: string };

export const movies = {
  shops: (orgId: string) => api.get<MovieShop[]>(`/organizations/${orgId}/movie-shops/`),
  createShop: (orgId: string, name: string, project: string) => api.post<MovieShop>(`/organizations/${orgId}/movie-shops/`, { name, project }),
  shop: (id: string) => api.get<MovieShop>(`/movie-shops/${id}/`),
  libraries: (id: string) => api.get<MovieLibrary[]>(`/movie-shops/${id}/libraries/`),
  addLibrary: (id: string, path: string, name: string, kind: MovieLibrary["kind"]) =>
    api.post<MovieLibrary>(`/movie-shops/${id}/libraries/`, { path, name, kind }),
  removeLibrary: (libraryId: string) => api.del(`/movie-libraries/${libraryId}/`),
  scan: (libraryId: string) => api.post<MovieLibrary>(`/movie-libraries/${libraryId}/scan/`),
  categories: (id: string, library?: string) =>
    api.get<MovieCategory[]>(`/movie-shops/${id}/categories/${library ? `?library=${encodeURIComponent(library)}` : ""}`),
  titles: (id: string, params: { library?: string; category?: string; q?: string; limit?: number; offset?: number; sort?: string }) => {
    const qs = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => v !== undefined && v !== "" && qs.set(k, String(v)));
    return api.get<Paginated<MovieTitle>>(`/movie-shops/${id}/titles/?${qs.toString()}`);
  },
  editTitle: (titleId: string, data: Partial<Pick<MovieTitle, "title" | "year" | "category" | "hidden" | "description">> & { price?: number | null }) =>
    api.patch<MovieTitle>(`/movie-titles/${titleId}/`, data),
  setPrices: (id: string, default_price: number, categories: Record<string, number>) => api.put<MovieShop>(`/movie-shops/${id}/prices/`, { default_price, categories }),
  agentCredential: (id: string) => api.post<{ token: string }>(`/movie-shops/${id}/agent-credential/`),
  drives: (id: string) => api.get<AgentReport>(`/movie-shops/${id}/drives/`),
  coverUrl: (titleId: string) => `/api/v1/movie-titles/${titleId}/cover/`,
};

/** "1 title", "4 titles". */
export function titlesLabel(n: number): string {
  return `${n.toLocaleString()} ${n === 1 ? "title" : "titles"}`;
}

/** 2_100_000_000 -> "2.1 GB". */
export function formatBytes(bytes: number | null | undefined): string {
  if (bytes == null) return "—";
  const units = ["B", "KB", "MB", "GB", "TB"];
  let n = bytes;
  let i = 0;
  while (n >= 1000 && i < units.length - 1) {
    n /= 1000;
    i++;
  }
  return `${n >= 100 || i === 0 ? Math.round(n) : n.toFixed(1)} ${units[i]}`;
}

/** Whether the media agent reported in the last two minutes (it reports every 15 seconds while running). */
export function agentOnline(seenAt: string | null, now = Date.now()): boolean {
  return !!seenAt && now - new Date(seenAt).getTime() < 120_000;
}

/** The command the owner runs once on the shop PC to connect the media agent. */
export function pairCommand(token: string, origin: string): string {
  const address = origin.replace(/^http:/, "https:");
  return `"C:\\IntraForge\\IntraForgeMediaAgent.exe" pair ${address} ${token}`;
}

const PALETTES: [string, string, string][] = [
  ["#f59e0b", "#7c2d12", "#fde68a"],
  ["#0ea5e9", "#0c1e3e", "#7dd3fc"],
  ["#ef4444", "#3b0a0a", "#fca5a5"],
  ["#6366f1", "#0b0b2e", "#fbbf24"],
  ["#10b981", "#032b22", "#6ee7b7"],
  ["#8b5cf6", "#140a2e", "#e9d5ff"],
  ["#ec4899", "#2a0517", "#fbcfe8"],
  ["#14b8a6", "#042f2e", "#99f6e4"],
  ["#d97706", "#1c1007", "#fcd34d"],
  ["#64748b", "#0f172a", "#e2e8f0"],
];
export const MOTIFS = ["sun", "mountain", "wave", "city", "moon", "road", "circle"] as const;

/** A title without a cover picture gets a drawn one: colours and a motif chosen from its name, always the same. */
export function drawnCover(title: string): { from: string; to: string; accent: string; motif: (typeof MOTIFS)[number] } {
  let h = 2166136261;
  for (const ch of title) h = Math.imul(h ^ ch.charCodeAt(0), 16777619) >>> 0;
  const [from, to, accent] = PALETTES[h % PALETTES.length];
  return { from, to, accent, motif: MOTIFS[(h >>> 8) % MOTIFS.length] };
}
