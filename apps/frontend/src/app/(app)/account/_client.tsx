"use client";

import { useState, type FormEvent } from "react";
import { ShieldCheck, ShieldOff } from "lucide-react";
import { api, ApiError, ensureCsrfCookie, type User } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { Badge, Button, Card, CopyButton, ErrorBanner, Input, Label, PageHeader, PageLoading } from "@/components/ui";

type Enrollment = { secret: string; provisioning_uri: string };

/** The setup key in groups of four, as authenticator apps show it, so it can be typed by hand. */
export function groupKey(secret: string): string {
  return secret.replace(/(.{4})(?=.)/g, "$1 ");
}

export default function AccountClient() {
  const { user, refresh } = useAuth();
  if (!user) return <PageLoading />;

  return (
    <div className="max-w-2xl space-y-6">
      <PageHeader title="Your account" description="Your sign-in details and two-step sign-in." />

      <Card>
        <dl className="grid gap-4 sm:grid-cols-2">
          <div>
            <dt className="text-xs font-medium text-text-muted">Email</dt>
            <dd className="mt-0.5 text-sm text-text-primary">{user.email}</dd>
          </div>
          <div>
            <dt className="text-xs font-medium text-text-muted">Name</dt>
            <dd className="mt-0.5 text-sm text-text-primary">
              {[user.first_name, user.last_name].filter(Boolean).join(" ") || "—"}
            </dd>
          </div>
        </dl>
      </Card>

      <TwoStepSignIn user={user} onChanged={refresh} />
    </div>
  );
}

function TwoStepSignIn({ user, onChanged }: { user: User; onChanged: () => Promise<void> }) {
  const [enrollment, setEnrollment] = useState<Enrollment | null>(null);
  const [turningOff, setTurningOff] = useState(false);
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState<string | null>(null);

  function reset() {
    setEnrollment(null);
    setTurningOff(false);
    setCode("");
    setError(null);
  }

  async function run(action: () => Promise<void>) {
    setBusy(true);
    setError(null);
    setDone(null);
    try {
      await ensureCsrfCookie();
      await action();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong. Nothing was changed.");
    } finally {
      setBusy(false);
    }
  }

  const start = () =>
    run(async () => {
      setEnrollment(await api.post<Enrollment>("/auth/mfa/enroll/"));
    });

  const confirm = (e: FormEvent) => {
    e.preventDefault();
    return run(async () => {
      await api.post("/auth/mfa/confirm/", { code: code.trim() });
      reset();
      setDone("Two-step sign-in is on. You'll be asked for a code each time you sign in.");
      await onChanged();
    });
  };

  const turnOff = (e: FormEvent) => {
    e.preventDefault();
    return run(async () => {
      await api.post("/auth/mfa/disable/", { code: code.trim() });
      reset();
      setDone("Two-step sign-in is off.");
      await onChanged();
    });
  };

  return (
    <Card className="space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex items-start gap-3">
          {user.mfa_enabled ? (
            <ShieldCheck aria-hidden="true" className="mt-0.5 h-5 w-5 text-green-600" />
          ) : (
            <ShieldOff aria-hidden="true" className="mt-0.5 h-5 w-5 text-text-muted" />
          )}
          <div>
            <h2 className="text-sm font-semibold text-text-primary">Two-step sign-in</h2>
            <p className="mt-0.5 max-w-md text-sm text-slate-500">
              After your password, enter a six-digit code from an authenticator app on your phone. Someone who
              learns your password still can&apos;t sign in.
            </p>
          </div>
        </div>
        <Badge tone={user.mfa_enabled ? "success" : "default"}>{user.mfa_enabled ? "On" : "Off"}</Badge>
      </div>

      <div aria-live="polite">{done && <p className="text-sm text-green-700">{done}</p>}</div>
      {error && <ErrorBanner message={error} />}

      {!user.mfa_enabled && !enrollment && (
        <Button onClick={() => void start()} disabled={busy}>
          Turn on two-step sign-in
        </Button>
      )}

      {!user.mfa_enabled && enrollment && (
        <form onSubmit={confirm} className="space-y-4 rounded-lg border border-border-subtle bg-surface-sunken p-4">
          <ol className="list-decimal space-y-2 pl-5 text-sm text-slate-600">
            <li>Open an authenticator app on your phone and choose to add an account with a setup key.</li>
            <li>
              Enter this key (account: <span className="font-medium">{user.email}</span>, time-based):
              <div className="mt-2 flex flex-wrap items-center gap-2">
                <code className="rounded bg-slate-900 px-2 py-1.5 font-mono text-sm tracking-wide text-slate-100">
                  {groupKey(enrollment.secret)}
                </code>
                <CopyButton value={enrollment.secret} label="Copy key" />
              </div>
              <p className="mt-1.5 text-xs text-text-muted">
                On this phone? <a href={enrollment.provisioning_uri} className="text-brand-600 underline">Open in your authenticator app</a>.
              </p>
            </li>
            <li>Type the six-digit code the app now shows.</li>
          </ol>
          <div className="max-w-48">
            <Label htmlFor="mfa-confirm-code">Code from the app</Label>
            <Input
              id="mfa-confirm-code"
              inputMode="numeric"
              autoComplete="one-time-code"
              pattern="[0-9]{6}"
              maxLength={6}
              required
              value={code}
              onChange={(e) => setCode(e.target.value)}
            />
          </div>
          <div className="flex gap-2">
            <Button type="submit" disabled={busy || code.trim().length !== 6}>
              Turn on
            </Button>
            <Button type="button" variant="ghost" onClick={reset} disabled={busy}>
              Cancel
            </Button>
          </div>
        </form>
      )}

      {user.mfa_enabled && !turningOff && (
        <Button variant="secondary" onClick={() => setTurningOff(true)}>
          Turn off two-step sign-in
        </Button>
      )}

      {user.mfa_enabled && turningOff && (
        <form onSubmit={turnOff} className="space-y-4 rounded-lg border border-border-subtle bg-surface-sunken p-4">
          <p className="text-sm text-slate-600">
            To turn it off, enter a current code from your authenticator app.
          </p>
          <div className="max-w-48">
            <Label htmlFor="mfa-disable-code">Current code</Label>
            <Input
              id="mfa-disable-code"
              inputMode="numeric"
              autoComplete="one-time-code"
              pattern="[0-9]{6}"
              maxLength={6}
              required
              value={code}
              onChange={(e) => setCode(e.target.value)}
            />
          </div>
          <div className="flex gap-2">
            <Button type="submit" variant="danger" disabled={busy || code.trim().length !== 6}>
              Turn off
            </Button>
            <Button type="button" variant="ghost" onClick={reset} disabled={busy}>
              Cancel
            </Button>
          </div>
        </form>
      )}
    </Card>
  );
}
