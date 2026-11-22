"use client";

import Link from "next/link";
import { useEffect, useState, useSyncExternalStore, type FormEvent } from "react";
import { CheckCircle2, Fingerprint, MailCheck } from "lucide-react";
import { ApiError } from "@/lib/api";
import { confirmLink, confirmLinkWithPasskey, inspectLink, tokenFromHash, type LinkInfo } from "@/lib/access";
import { passkeyErrorMessage, passkeysSupported } from "@/lib/passkeys";
import { Button, ErrorBanner, Input, Label, PageLoading } from "@/components/ui";

const noSubscription = () => () => undefined;

/** The single-use confirmation link (ADR-0026). The token is in the fragment (#t=...), read here and sent in a
 * request body only: it never reaches a server log. Nothing secret is ever shown on this page. */
export default function ConfirmPage() {
  // Read once in the browser (null while rendering on the server, so both first renders show the loading page).
  const [token] = useState<string | null>(() =>
    typeof window === "undefined" ? null : tokenFromHash(window.location.hash),
  );
  const [info, setInfo] = useState<LinkInfo | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState<null | "password" | "passkey">(null);
  const canUsePasskey = useSyncExternalStore(noSubscription, passkeysSupported, () => false);

  useEffect(() => {
    // Take the token out of the address bar and the history once it is read.
    window.history.replaceState(null, "", window.location.pathname);
    if (!token) return;
    inspectLink(token)
      .then(setInfo)
      .catch((err) => setError(err instanceof ApiError ? err.message : "This link does not work."));
  }, [token]);

  async function confirm(e?: FormEvent) {
    e?.preventDefault();
    if (!token) return;
    setBusy(true);
    setError(null);
    try {
      await confirmLink(token, info?.needs_sign_in_method ? password : undefined);
      setDone("password");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong.");
    } finally {
      setBusy(false);
    }
  }

  async function addPhonePasskey() {
    if (!token) return;
    setBusy(true);
    setError(null);
    try {
      await confirmLinkWithPasskey(token, "Phone");
      setDone("passkey");
    } catch (err) {
      setError(passkeyErrorMessage(err) ?? (err instanceof ApiError ? err.message : "Something went wrong."));
    } finally {
      setBusy(false);
    }
  }

  if (token === null || (token && !info && !error)) return <PageLoading />;
  const shownError = token ? error : "This link is incomplete. Open the whole link you received.";

  return (
    <div className="flex min-h-screen items-center justify-center bg-white px-4 py-10">
      <div className="w-full max-w-sm space-y-4">
        <div className="flex flex-col items-center text-center">
          <span className="mb-3 flex h-11 w-11 items-center justify-center rounded-xl bg-brand-50 text-brand-600">
            <MailCheck size={24} aria-hidden="true" />
          </span>
          <h1 className="text-lg font-semibold text-text-primary">Activate your account</h1>
          {info && <p className="mt-1 text-sm text-slate-500">{info.email}</p>}
        </div>

        {shownError && <ErrorBanner message={shownError} />}

        {done ? (
          <div className="space-y-3 rounded-xl border border-slate-200 bg-white p-6 text-center">
            <CheckCircle2 className="mx-auto h-8 w-8 text-green-600" aria-hidden="true" />
            <p className="text-sm text-text-primary">
              {done === "passkey"
                ? "Your account is active. It signs in with the passkey on your phone only: on the sign-in page choose Sign in with a passkey and scan the QR code."
                : "Your email is confirmed and your account is active. You can sign in now."}
            </p>
            <Link href="/login" className="text-sm text-brand-600 underline underline-offset-4">
              Go to sign in
            </Link>
          </div>
        ) : info && !info.needs_sign_in_method ? (
          <div className="space-y-3 rounded-xl border border-slate-200 bg-white p-6">
            <p className="text-sm text-text-muted">
              Confirm that this is your email to activate the account. You then sign in with the password you chose
              when you asked for access.
            </p>
            <Button className="w-full" onClick={() => void confirm()} disabled={busy}>
              {busy ? "..." : "Confirm and activate"}
            </Button>
          </div>
        ) : info ? (
          <div className="space-y-4 rounded-xl border border-slate-200 bg-white p-6">
            <p className="text-sm text-text-muted">
              This account has no way to sign in yet. Choose one: only you will know it.
            </p>
            {canUsePasskey && (
              <div className="space-y-2">
                <Button className="w-full" onClick={() => void addPhonePasskey()} disabled={busy}>
                  <Fingerprint size={16} aria-hidden="true" />
                  Add a passkey on my phone
                </Button>
                <p className="text-xs text-text-muted">
                  Scan the QR code with your phone and confirm with your fingerprint or face. The passkey stays in
                  your phone (for example Google Password Manager); the account then has no password at all.
                </p>
              </div>
            )}
            <form onSubmit={confirm} className="space-y-2 border-t border-slate-100 pt-4">
              <Label htmlFor="password">Or choose a password</Label>
              <Input
                id="password"
                type="password"
                autoComplete="new-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="At least 12 characters"
              />
              <Button type="submit" variant="secondary" className="w-full" disabled={busy || !password}>
                Use this password
              </Button>
            </form>
          </div>
        ) : null}
      </div>
    </div>
  );
}
