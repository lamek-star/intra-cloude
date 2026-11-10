// The Movie Shop customer portal (ADR-0022 phase 3), at /portal/<shop>. Customers are not IntraForge users: the portal
// API takes only its own HttpOnly cookie (set by sign-up / sign-in), and every change carries X-Portal-Request, which
// another site cannot send. Nothing here uses IntraForge's session or CSRF token.

import { ApiError } from "./api";

export type PortalRules = { welcome_points: number; referral_points: number; birthday_points: number; every_nth_free: number };

export type PortalMe = {
  id: string;
  name: string;
  phone: string;
  status: "pending" | "approved" | "rejected" | "blocked";
  points: number;
  referral_code: string | null;
  birthday: string | null;
  created_at: string;
  wallet?: { username: string; balance: number | null; path: string | null; must_change_password: boolean } | null;
  points_history?: { delta: number; reason: string; note: string; at: string }[];
};

export type PortalHome = { shop: { id: string; name: string; rules: PortalRules }; customer: PortalMe | null };

export type PortalTitle = {
  id: string;
  category: string;
  title: string;
  year: number | null;
  kind: "movie" | "series";
  size_bytes: number;
  episodes: number;
  has_cover: boolean;
  price: number;
  description: string;
};

export type PortalOrder = {
  id: string;
  number: string;
  status: "ordered" | "awaiting_payment" | "paid" | "done" | "cancelled";
  total: number;
  discount: number;
  points_used: number;
  use_points: boolean;
  created_at: string;
  lines: { title: string; category: string; price: number; free: boolean }[];
};

export type OrderPreview = { subtotal: number; discount: number; points_used: number; total: number; free_titles: string[] };

type Page<T> = { count: number; next: string | null; previous: string | null; results: T[] };

async function call<T>(method: "GET" | "POST", path: string, body?: unknown): Promise<T> {
  const headers: Record<string, string> = { Accept: "application/json" };
  if (method !== "GET") headers["X-Portal-Request"] = "1";
  if (body !== undefined) headers["Content-Type"] = "application/json";
  const res = await fetch(`/api/v1/portal/${path}`, {
    method,
    headers,
    credentials: "same-origin",
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const data = res.status === 204 ? null : await res.json().catch(() => null);
  if (!res.ok) throw new ApiError(res.status, data);
  return data as T;
}

export const portalApi = {
  home: (shop: string) => call<PortalHome>("GET", `${shop}/`),
  signUp: (shop: string, body: { name: string; phone: string; password: string; birthday?: string; referral_code?: string }) =>
    call<PortalMe>("POST", `${shop}/signup/`, body),
  signIn: (shop: string, phone: string, password: string) => call<PortalMe>("POST", `${shop}/login/`, { phone, password }),
  signOut: (shop: string) => call<{ ok: boolean }>("POST", `${shop}/logout/`),
  me: (shop: string) => call<PortalMe>("GET", `${shop}/me/`),
  categories: (shop: string) => call<{ name: string; count: number }[]>("GET", `${shop}/categories/`),
  titles: (shop: string, params: { category?: string; q?: string; limit?: number }) => {
    const qs = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => v !== undefined && v !== "" && qs.set(k, String(v)));
    return call<Page<PortalTitle>>("GET", `${shop}/titles/?${qs.toString()}`);
  },
  coverUrl: (shop: string, titleId: string) => `/api/v1/portal/${shop}/titles/${titleId}/cover/`,
  orders: (shop: string) => call<PortalOrder[]>("GET", `${shop}/orders/`),
  preview: (shop: string, titles: string[], use_points: boolean) =>
    call<OrderPreview>("POST", `${shop}/orders/`, { titles, use_points, preview: true }),
  order: (shop: string, titles: string[], use_points: boolean) => call<PortalOrder>("POST", `${shop}/orders/`, { titles, use_points }),
  cancelOrder: (shop: string, orderId: string) => call<PortalOrder>("POST", `${shop}/orders/${orderId}/cancel/`),
};

/** The reward rules in plain words, for the sign-up page and the points page. */
export function rulesInWords(rules: PortalRules): string[] {
  const out: string[] = [];
  if (rules.welcome_points) out.push(`${rules.welcome_points} points when the shop approves you`);
  if (rules.every_nth_free) out.push(`Every ${ordinal(rules.every_nth_free)} title free`);
  if (rules.referral_points) out.push(`${rules.referral_points} points for each friend you invite`);
  if (rules.birthday_points) out.push(`${rules.birthday_points} points in your birthday month`);
  return out;
}

export function ordinal(n: number): string {
  const tens = n % 100;
  if (tens >= 11 && tens <= 13) return `${n}th`;
  return `${n}${{ 1: "st", 2: "nd", 3: "rd" }[n % 10] ?? "th"}`;
}

export const POINT_REASONS: Record<string, string> = {
  welcome: "Welcome",
  referral: "Friend invited",
  birthday: "Birthday",
  redeem: "Used on a purchase",
  returned: "Purchase cancelled, points back",
  adjust: "From the shop",
};
