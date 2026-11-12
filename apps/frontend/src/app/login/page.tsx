"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState, useSyncExternalStore, type FormEvent } from "react";
import { Fingerprint, Package } from "lucide-react";
import { ApiError } from "@/lib/api";
import { isMfaRequired, useAuth } from "@/lib/auth-context";
import { passkeyErrorMessage, passkeysSupported } from "@/lib/passkeys";
import { isSafeNextPath } from "@/lib/safe-next";
import { appIdFromOpenPath, getSignInBranding, type SignInBranding } from "@/lib/service-apps";
import { Button, ErrorBanner, Input, Label, PageLoading } from "@/components/ui";

const noSubscription = () => () => undefined;

export default function LoginPage() {
  return (
    <Suspense fallback={<PageLoading />}>
      <LoginPageInner />
    </Suspense>
  );
}

function LoginPageInner() {
  const { login, verifyMfa, signInWithPasskey } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const next = searchParams.get("next");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [code, setCode] = useState("");
  const [needsMfa, setNeedsMfa] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  // Known only in the browser; false while rendering on the server.
  const canUsePasskey = useSyncExternalStore(noSubscription, passkeysSupported, () => false);
  // Sent here by an application (its "open" page): show that application's own sign-in.
  const appId = isSafeNextPath(next) ? appIdFromOpenPath(next) : null;
  const [branding, setBranding] = useState<SignInBranding | null>(null);
  // Until the application's name has arrived, show neither header (no flash of "IntraForge" first).
  const [brandingSettled, setBrandingSettled] = useState(!appId);

  useEffect(() => {
    if (!appId) return;
    let live = true;
    getSignInBranding(appId)
      .then((b) => live && setBranding(b))
      .catch(() => undefined) // unknown or unavailable: the ordinary IntraForge sign-in
      .finally(() => live && setBrandingSettled(true));
    return () => {
      live = false;
    };
  }, [appId]);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      if (needsMfa) {
        await verifyMfa(code);
      } else {
        const result = await login(email, password);
        if (isMfaRequired(result)) {
          setNeedsMfa(true);
          setSubmitting(false);
          return;
        }
      }
      goOn();
    } catch (err) {
      if (err instanceof ApiError && (err.body as { passkey_only?: boolean } | null)?.passkey_only) {
        setError("This account signs in with a passkey only. Use the passkey button below.");
      } else {
        setError(err instanceof ApiError ? err.message : "Something went wrong.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  function goOn() {
    if (isSafeNextPath(next)) {
      // A real, full navigation -- `next` may point outside the
      // Next.js app entirely (e.g. back into /oauth/authorize on the
      // same origin, for an external application's sign-in flow),
      // which router.push() cannot reach.
      window.location.assign(next);
    } else {
      router.push("/dashboard");
    }
  }

  async function passkeySignIn() {
    setError(null);
    setSubmitting(true);
    try {
      await signInWithPasskey("phone");
      goOn();
    } catch (err) {
      setError(passkeyErrorMessage(err) ?? (err instanceof ApiError ? err.message : "Something went wrong."));
    } finally {
      setSubmitting(false);
    }
  }

  const registerHref = isSafeNextPath(next) ? `/register?next=${encodeURIComponent(next)}` : "/register";

  return (
    <div className="flex min-h-screen items-center justify-center bg-white px-4">
      <div className="w-full max-w-sm">
        {!brandingSettled ? (
          <div className="mb-8 h-[108px]" aria-hidden="true" />
        ) : branding ? (
          <div className="mb-8 flex flex-col items-center text-center">
            <span className="mb-3 flex h-11 w-11 items-center justify-center rounded-xl bg-brand-50 text-brand-600">
              <Package size={24} aria-hidden="true" />
            </span>
            <h1 className="text-lg font-semibold text-text-primary">{branding.product_name}</h1>
            <p className="mt-0.5 text-sm font-medium text-text-primary">{branding.display_name}</p>
            <p className="mt-1 text-sm text-slate-500">Sign in with your staff account</p>
          </div>
        ) : (
          <div className="mb-8 flex flex-col items-center">
            {/* eslint-disable-next-line @next/next/no-img-element -- fixed-size static brand asset */}
            <img src="/brand/icon-96.png" alt="IntraForge" width={44} height={44} className="mb-3 h-11 w-11" />
            <h1 className="text-lg font-semibold text-text-primary">IntraForge</h1>
            <p className="mt-1 text-sm text-slate-500">Sign in to your account</p>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4 rounded-xl border border-slate-200 bg-white p-6">
          {error && <ErrorBanner message={error} />}

          {!needsMfa ? (
            <>
              <div>
                <Label htmlFor="email">Email</Label>
                <Input
                  id="email"
                  type="email"
                  autoComplete="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@example.com"
                />
              </div>
              <div>
                <Label htmlFor="password">Password</Label>
                <Input
                  id="password"
                  type="password"
                  autoComplete="current-password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                />
              </div>
            </>
          ) : (
            <div>
              <Label htmlFor="code">Authenticator code</Label>
              <Input
                id="code"
                autoComplete="one-time-code"
                autoFocus
                maxLength={12}
                required
                value={code}
                onChange={(e) => setCode(e.target.value)}
                placeholder="123456"
              />
              <p className="mt-1.5 text-xs text-slate-500">
                This account uses two-step sign-in. Enter the six-digit code from your authenticator app, or one of
                your recovery codes if you no longer have the app.
              </p>
            </div>
          )}

          <Button type="submit" className="w-full" disabled={submitting}>
            {submitting ? "..." : needsMfa ? "Verify" : "Sign in"}
          </Button>
        </form>

        {canUsePasskey && !needsMfa && (
          <div className="mt-4">
            <div className="mb-4 flex items-center gap-3 text-xs text-text-muted" aria-hidden="true">
              <span className="h-px flex-1 bg-slate-200" />
              or
              <span className="h-px flex-1 bg-slate-200" />
            </div>
            <Button variant="secondary" className="w-full" onClick={() => void passkeySignIn()} disabled={submitting}>
              <Fingerprint size={16} aria-hidden="true" />
              Sign in with a passkey
            </Button>
            <p className="mt-2 text-center text-xs text-text-muted">
              Scan the QR code with your phone and confirm with your fingerprint or face.
            </p>
          </div>
        )}

        {branding && (
          <p className="mt-4 text-center text-xs text-text-muted">Staff accounts are managed in IntraForge.</p>
        )}
        <p className="mt-5 text-center text-sm text-slate-500">
          Don&apos;t have an account?{" "}
          <Link href={registerHref} className="text-brand-600 underline underline-offset-4 hover:text-brand-500">
            Create one
          </Link>
        </p>
      </div>
    </div>
  );
}
