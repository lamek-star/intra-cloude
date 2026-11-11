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
  can_sell: boolean;
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
  kind: "movie" | "series" | "music" | "album";
  size_bytes: number;
  episodes: number;
  has_cover: boolean;
  /** The owner chose this poster; a re-scan never replaces it. */
  cover_locked?: boolean;
  cover_version?: string;
  price: number;
  own_price: number | null;
  hidden: boolean;
  description: string;
};

export type AgentDrive = { root: string; label: string; kind: MovieLibrary["kind"]; total_bytes: number | null; free_bytes: number | null; folders: string[] };
export type AgentReport = { agent_seen_at: string | null; drives: AgentDrive[]; computer?: string; agent_version?: string };

export type SaleLine = {
  id: string;
  title: string;
  title_id: string | null;
  category: string;
  kind: MovieTitle["kind"];
  price: number;
  size_bytes: number;
  copy_status: "waiting" | "copying" | "copied" | "failed";
  copied_bytes: number;
  copy_message: string;
  free: boolean;
};

export type Sale = {
  id: string;
  shop: string;
  number: string;
  status: "ordered" | "awaiting_payment" | "paid" | "done" | "cancelled";
  method: "ifpay" | "cash";
  customer_name: string;
  total: number;
  destination: string;
  folder: string;
  pay: { code: string; qr_svg: string; expires_at: string | null } | null;
  receipt_number: string;
  paid_at: string | null;
  created_at: string;
  lines: SaleLine[];
  /** The portal customer a sale is for (their points and free titles apply). */
  customer: { id: string; name: string; phone: string } | null;
  use_points: boolean;
  points_used: number;
  discount: number;
};

export type PortalSettings = {
  portal_open: boolean;
  welcome_points: number;
  referral_points: number;
  birthday_points: number;
  every_nth_free: number;
  path: string;
  waiting: number;
};

export type ShopCustomer = {
  id: string;
  name: string;
  phone: string;
  status: "pending" | "approved" | "rejected" | "blocked";
  points: number;
  referral_code: string | null;
  birthday: string | null;
  created_at: string;
  pay_username: string;
  has_wallet: boolean;
  referred_by: string | null;
  approved_at: string | null;
  /** The customer asked for a new password on the portal. */
  reset_requested_at: string | null;
};

export type ShopAd = {
  id: string;
  title: string;
  text: string;
  advertiser: string;
  film: string | null;
  film_title: string | null;
  link: string;
  has_picture: boolean;
  picture_version: string;
  starts_on: string | null;
  ends_on: string | null;
  active: boolean;
  position: number;
  views: number;
  taps: number;
  showing: boolean;
  created_at: string;
};

export type AdInput = Partial<Pick<ShopAd, "title" | "text" | "advertiser" | "film" | "link" | "starts_on" | "ends_on" | "active" | "position">>;

export type ApprovedWallet = { username: string | null; created: boolean; first_password: string | null; path: string | null };

export type Destination = { root: string; label: string; kind: MovieLibrary["kind"]; total_bytes: number | null; free_bytes: number | null };

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
  coverUrl: (titleId: string, version = "") => `/api/v1/movie-titles/${titleId}/cover/${version ? `?v=${version}` : ""}`,
  setPoster: (titleId: string, file: File) => {
    const form = new FormData();
    form.append("file", file);
    return api.postForm<MovieTitle>(`/movie-titles/${titleId}/cover/`, form);
  },
  clearPoster: (titleId: string) => api.del<MovieTitle>(`/movie-titles/${titleId}/cover/`),
  renameShop: (id: string, name: string) => api.patch<MovieShop>(`/movie-shops/${id}/`, { name }),
  renameLibrary: (libraryId: string, name: string) => api.patch<MovieLibrary>(`/movie-libraries/${libraryId}/`, { name }),
  destinations: (id: string) => api.get<{ agent_seen_at: string | null; drives: Destination[] }>(`/movie-shops/${id}/destinations/`),
  createSale: (id: string, body: { titles: string[]; destination: string; method: Sale["method"]; customer_name: string }) =>
    api.post<Sale>(`/movie-shops/${id}/sales/`, body),
  sales: (id: string, offset = 0) => api.get<Paginated<Sale>>(`/movie-shops/${id}/sales/?limit=25&offset=${offset}`),
  sale: (saleId: string) => api.get<Sale>(`/movie-sales/${saleId}/`),
  saleAction: (saleId: string, action: "cash" | "cancel" | "retry") => api.post<Sale>(`/movie-sales/${saleId}/${action}/`),
  charge: (saleId: string, destination: string, method: Sale["method"]) =>
    api.post<Sale>(`/movie-sales/${saleId}/charge/`, { destination, method }),
  portal: (id: string) => api.get<PortalSettings>(`/movie-shops/${id}/portal/`),
  setPortal: (id: string, body: Partial<Omit<PortalSettings, "path" | "waiting">>) => api.put<PortalSettings>(`/movie-shops/${id}/portal/`, body),
  customers: (id: string, status?: ShopCustomer["status"]) =>
    api.get<Paginated<ShopCustomer>>(`/movie-shops/${id}/customers/?limit=100${status ? `&status=${status}` : ""}`),
  approve: (customerId: string) => api.post<{ customer: ShopCustomer; wallet: ApprovedWallet }>(`/movie-customers/${customerId}/approve/`),
  customerAction: (customerId: string, action: "reject" | "block" | "unblock") =>
    api.post<{ customer: ShopCustomer }>(`/movie-customers/${customerId}/${action}/`),
  editCustomer: (customerId: string, body: { name?: string; phone?: string; birthday?: string | null }) =>
    api.patch<{ customer: ShopCustomer }>(`/movie-customers/${customerId}/`, body),
  resetCode: (customerId: string) => api.post<{ customer: ShopCustomer; code: string; minutes: number }>(`/movie-customers/${customerId}/reset-code/`),
  resetWallet: (customerId: string) =>
    api.post<{ customer: ShopCustomer; wallet: { username: string | null; first_password: string | null } }>(`/movie-customers/${customerId}/wallet-password/`),
  ads: (id: string) => api.get<ShopAd[]>(`/movie-shops/${id}/ads/`),
  createAd: (id: string, body: AdInput) => api.post<ShopAd>(`/movie-shops/${id}/ads/`, body),
  updateAd: (adId: string, body: AdInput) => api.patch<ShopAd>(`/movie-ads/${adId}/`, body),
  deleteAd: (adId: string) => api.del(`/movie-ads/${adId}/`),
  uploadAdPicture: (adId: string, file: File) => {
    const form = new FormData();
    form.append("file", file);
    return api.postForm<ShopAd>(`/movie-ads/${adId}/picture/`, form);
  },
  adPictureUrl: (adId: string, version = "") => `/api/v1/movie-ads/${adId}/picture/${version ? `?v=${version}` : ""}`,
  adjustPoints: (customerId: string, delta: number, note: string) =>
    api.post<{ customer: ShopCustomer }>(`/movie-customers/${customerId}/points/`, { delta, note }),
};

/** "1 title", "4 titles". */
/** "6 episodes" for a series, "12 songs" for an album; nothing for a single film or song. */
export function partsLabel(t: { kind: MovieTitle["kind"]; episodes: number }, short = false): string | null {
  if (t.kind === "series") return short ? `${t.episodes} ep.` : `${t.episodes} episodes`;
  if (t.kind === "album") return `${t.episodes} ${t.episodes === 1 ? "song" : "songs"}`;
  if (t.kind === "music") return "Song";
  return null;
}

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

/** Pay's QR code as a picture source, drawn from an <img> so nothing in it can run as part of this page. Pay sends
 * it as a base64 SVG data URL; a bare SVG document is encoded here. Anything else gives no picture. */
export function qrDataUrl(qr: string): string | null {
  const prefix = "data:image/svg+xml;base64,";
  if (qr.startsWith(prefix)) return /^[A-Za-z0-9+/]+={0,2}$/.test(qr.slice(prefix.length)) ? qr : null;
  if (!/^\s*(<\?xml|<svg)/i.test(qr)) return null;
  let binary = "";
  new TextEncoder().encode(qr).forEach((b) => (binary += String.fromCharCode(b)));
  return `${prefix}${btoa(binary)}`;
}

/** How far a sale's copying has got, 0..1. */
export function copyProgress(sale: Sale): number {
  const total = sale.lines.reduce((a, l) => a + Math.max(l.size_bytes, 1), 0);
  const done = sale.lines.reduce((a, l) => a + (l.copy_status === "copied" ? Math.max(l.size_bytes, 1) : Math.min(l.copied_bytes, l.size_bytes)), 0);
  return total ? done / total : 0;
}

export const SALE_STATUS: Record<Sale["status"], string> = {
  ordered: "Ordered on the portal",
  awaiting_payment: "Waiting for payment",
  paid: "Paid · copying",
  done: "Copied",
  cancelled: "Cancelled",
};
