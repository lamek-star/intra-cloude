"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState, type FormEvent } from "react";
import { ApiError } from "@/lib/api";
import { isMfaRequired, useAuth } from "@/lib/auth-context";
import { isSafeNextPath } from "@/lib/safe-next";
import { Button, ErrorBanner, Input, Label, PageLoading } from "@/components/ui";

export default function LoginPage() {
  return (
    <Suspense fallback={<PageLoading />}>
      <LoginPageInner />
    </Suspense>
  );
}

function LoginPageInner() {
  const { login, verifyMfa } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const next = searchParams.get("next");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [code, setCode] = useState("");
  const [needsMfa, setNeedsMfa] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

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
      if (isSafeNextPath(next)) {
        // A real, full navigation -- `next` may point outside the
        // Next.js app entirely (e.g. back into /oauth/authorize on the
        // same origin, for an external application's sign-in flow),
        // which router.push() cannot reach.
        window.location.assign(next);
      } else {
        router.push("/dashboard");
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong.");
    } finally {
      setSubmitting(false);
    }
  }

  const registerHref = isSafeNextPath(next) ? `/register?next=${encodeURIComponent(next)}` : "/register";

  return (
    <div className="flex min-h-screen items-center justify-center bg-white px-4">
      <div className="w-full max-w-sm">
        <div className="mb-8 flex flex-col items-center">
          {/* eslint-disable-next-line @next/next/no-img-element -- fixed-size static brand asset */}
          <img src="/brand/icon-96.png" alt="IntraForge" width={44} height={44} className="mb-3 h-11 w-11" />
          <h1 className="text-lg font-semibold text-text-primary">IntraForge</h1>
          <p className="mt-1 text-sm text-slate-500">Sign in to your account</p>
        </div>

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
                inputMode="numeric"
                autoFocus
                maxLength={6}
                required
                value={code}
                onChange={(e) => setCode(e.target.value)}
                placeholder="123456"
              />
              <p className="mt-1.5 text-xs text-slate-500">
                This account has MFA enabled — enter the 6-digit code from your authenticator app.
              </p>
            </div>
          )}

          <Button type="submit" className="w-full" disabled={submitting}>
            {submitting ? "..." : needsMfa ? "Verify" : "Sign in"}
          </Button>
        </form>

        <p className="mt-5 text-center text-sm text-slate-500">
          Don&apos;t have an account?{" "}
          <Link href={registerHref} className="text-brand-600 hover:text-brand-500">
            Create one
          </Link>
        </p>
      </div>
    </div>
  );
}
