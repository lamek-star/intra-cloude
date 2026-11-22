/** Access requests from each app and single-use confirmation links (ADR-0026). */
import { api, ensureCsrfCookie } from "@/lib/api";
import { credentialToJson, toCreationOptions } from "@/lib/passkeys";

type Json = Record<string, unknown>;

export type AppJob = { slug: string; name: string; summary: string };
export type AppAccess = { product_name: string; display_name: string; roles: AppJob[]; accepts_requests: boolean };

export type AccessRequest = {
  id: string;
  status: "pending" | "approved" | "rejected";
  email: string;
  name: string;
  phone: string;
  app: { id: string; name: string; type: string } | null;
  requested_role: string;
  requested_role_name: string;
  granted_role: string;
  message: string;
  new_account: boolean;
  activated: boolean;
  decision_note: string;
  decided_by: string | null;
  decided_at: string | null;
  created_at: string;
};

export type Decision = { request?: AccessRequest; link: string | null; emailed: boolean };

export type NewPerson = {
  email: string;
  password: string;
  first_name: string;
  last_name: string;
  phone: string;
  requested_role: string;
  message: string;
};

export function getAppAccess(appId: string): Promise<AppAccess> {
  return api.get<AppAccess>(`/access/apps/${appId}/`);
}

/** Signed out: asks as a new person (an inactive account until confirmed). Signed in: asks for this account. */
export async function requestAccess(appId: string, body: Partial<NewPerson>): Promise<{ detail: string }> {
  await ensureCsrfCookie();
  return api.post<{ detail: string }>(`/access/apps/${appId}/`, body);
}

export function listAccessRequests(
  orgId: string,
  status?: string,
): Promise<{ results: AccessRequest[]; email_enabled: boolean }> {
  const query = status ? `?status=${encodeURIComponent(status)}` : "";
  return api.get(`/organizations/${orgId}/access-requests/${query}`);
}

export function decideAccessRequest(
  orgId: string,
  requestId: string,
  decision: "approve" | "reject" | "link",
  body: { role_slug?: string; note?: string } = {},
): Promise<Decision> {
  return api.post<Decision>(`/organizations/${orgId}/access-requests/${requestId}/${decision}/`, body);
}

export type LinkInfo = { email: string; first_name: string; needs_sign_in_method: boolean; expires_at: string };

export function inspectLink(token: string): Promise<LinkInfo> {
  return api.post<LinkInfo>("/auth/links/inspect/", { token });
}

export function confirmLink(token: string, password?: string): Promise<{ email: string; activated: boolean }> {
  return api.post("/auth/links/confirm/", password ? { token, password } : { token });
}

/** A system-made account: makes its passkey on the phone (QR code) and becomes passkey-only. */
export async function confirmLinkWithPasskey(token: string, name: string): Promise<{ email: string }> {
  const options = await api.post<Json>("/auth/links/passkey/options/", { token, where: "phone" });
  const credential = (await navigator.credentials.create({
    publicKey: toCreationOptions(options),
  })) as PublicKeyCredential | null;
  if (!credential) throw new DOMException("No passkey was made.", "NotAllowedError");
  return api.post("/auth/links/passkey/verify/", { token, credential: credentialToJson(credential), name });
}

/** The token from /confirm#t=... (a fragment: it never reached any server log). */
export function tokenFromHash(hash: string): string {
  const match = /(?:^#|&)t=([A-Za-z0-9_-]{10,100})/.exec(hash);
  return match ? match[1] : "";
}
