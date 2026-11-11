/**
 * Passkeys (ADR-0019) with the browser's own WebAuthn API -- no library. The server sends the options as JSON
 * (binary fields base64url-encoded) and checks the answer; this file only converts between JSON and the
 * ArrayBuffers `navigator.credentials` wants, and back.
 */
import { api, ensureCsrfCookie, type User } from "@/lib/api";

/** Where the browser should look for (or make) the passkey. "phone" shows the QR code to scan first. */
export type PasskeyWhere = "phone" | "this_device" | "security_key";

export type Passkey = {
  id: string;
  name: string;
  rp_id: string;
  backed_up: boolean;
  transports: string[];
  created_at: string;
  last_used_at: string | null;
};

export type PasskeyList = { passkey_only: boolean; this_address: string | null; passkeys: Passkey[] };

type Json = Record<string, unknown>;

export function passkeysSupported(): boolean {
  return typeof window !== "undefined" && typeof window.PublicKeyCredential === "function";
}

export function base64urlToBuffer(value: string): ArrayBuffer {
  const base64 = value.replace(/-/g, "+").replace(/_/g, "/").padEnd(Math.ceil(value.length / 4) * 4, "=");
  const binary = atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
  return bytes.buffer;
}

export function bufferToBase64url(value: ArrayBuffer | ArrayBufferView): string {
  const bytes = value instanceof ArrayBuffer ? new Uint8Array(value) : new Uint8Array(value.buffer, value.byteOffset, value.byteLength);
  let binary = "";
  for (const b of bytes) binary += String.fromCharCode(b);
  return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

function descriptors(list: unknown): PublicKeyCredentialDescriptor[] | undefined {
  if (!Array.isArray(list)) return undefined;
  return list.map((d: Json) => ({ ...d, id: base64urlToBuffer(String(d.id)) }) as PublicKeyCredentialDescriptor);
}

export function toCreationOptions(json: Json): PublicKeyCredentialCreationOptions {
  const user = json.user as Json;
  return {
    ...(json as object),
    challenge: base64urlToBuffer(String(json.challenge)),
    user: { ...(user as object), id: base64urlToBuffer(String(user.id)) } as PublicKeyCredentialUserEntity,
    excludeCredentials: descriptors(json.excludeCredentials),
  } as PublicKeyCredentialCreationOptions;
}

export function toRequestOptions(json: Json): PublicKeyCredentialRequestOptions {
  return {
    ...(json as object),
    challenge: base64urlToBuffer(String(json.challenge)),
    allowCredentials: descriptors(json.allowCredentials),
  } as PublicKeyCredentialRequestOptions;
}

/** The answer as the JSON the server's `webauthn` library reads. */
export function credentialToJson(credential: PublicKeyCredential): Json {
  const r = credential.response as AuthenticatorResponse & {
    attestationObject?: ArrayBuffer;
    authenticatorData?: ArrayBuffer;
    signature?: ArrayBuffer;
    userHandle?: ArrayBuffer | null;
    getTransports?: () => string[];
  };
  const response: Json = { clientDataJSON: bufferToBase64url(r.clientDataJSON) };
  if (r.attestationObject) {
    response.attestationObject = bufferToBase64url(r.attestationObject);
    response.transports = typeof r.getTransports === "function" ? r.getTransports() : [];
  }
  if (r.authenticatorData) response.authenticatorData = bufferToBase64url(r.authenticatorData);
  if (r.signature) response.signature = bufferToBase64url(r.signature);
  if (r.userHandle) response.userHandle = bufferToBase64url(r.userHandle);
  return {
    id: credential.id,
    rawId: bufferToBase64url(credential.rawId),
    type: credential.type,
    response,
    clientExtensionResults: credential.getClientExtensionResults?.() ?? {},
  };
}

/** A browser refusal (the person closed the dialog, the time ran out) as a sentence, not a stack trace. */
export function passkeyErrorMessage(err: unknown): string | null {
  if (err instanceof DOMException) {
    if (err.name === "NotAllowedError") return "The passkey request was closed or timed out. Nothing was changed.";
    if (err.name === "InvalidStateError") return "This passkey is already added to your account.";
    if (err.name === "SecurityError")
      return "This address cannot use passkeys. Open IntraForge by its name (for example https://localhost) instead of a number.";
    return `The browser refused the passkey (${err.name}).`;
  }
  return null;
}

export async function addPasskey(input: {
  password: string;
  code?: string;
  name: string;
  where: PasskeyWhere;
}): Promise<Passkey> {
  await ensureCsrfCookie();
  const options = await api.post<Json>("/auth/passkeys/register/options/", {
    password: input.password,
    code: input.code ?? "",
    where: input.where,
  });
  const credential = (await navigator.credentials.create({ publicKey: toCreationOptions(options) })) as PublicKeyCredential | null;
  if (!credential) throw new DOMException("No passkey was made.", "NotAllowedError");
  return api.post<Passkey>("/auth/passkeys/register/verify/", { credential: credentialToJson(credential), name: input.name });
}

/** Signed out: signs in with a passkey. Signed in: a fresh check with one of the user's own passkeys. */
export async function checkWithPasskey(where: PasskeyWhere = "phone"): Promise<User> {
  await ensureCsrfCookie();
  const options = await api.post<Json>("/auth/passkeys/check/options/", { where });
  const credential = (await navigator.credentials.get({ publicKey: toRequestOptions(options) })) as PublicKeyCredential | null;
  if (!credential) throw new DOMException("No passkey was chosen.", "NotAllowedError");
  return api.post<User>("/auth/passkeys/check/verify/", { credential: credentialToJson(credential) });
}
