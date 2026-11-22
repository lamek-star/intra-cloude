"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState, type FormEvent, type ReactNode } from "react";
import { CheckCircle2, Package } from "lucide-react";
import { ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { getAppAccess, requestAccess, type AppAccess, type NewPerson } from "@/lib/access";
import { isSafeNextPath } from "@/lib/safe-next";
import { Button, ErrorBanner, Input, Label, PageLoading, Select, Textarea } from "@/components/ui";

const EMPTY: NewPerson = {
  email: "",
  password: "",
  first_name: "",
  last_name: "",
  phone: "",
  requested_role: "",
  message: "",
};

export default function RequestAccessPage() {
  return (
    <Suspense fallback={<PageLoading />}>
      <RequestAccessInner />
    </Suspense>
  );
}

/** An application's own "Request access" (ADR-0026): a new person asks to work in it; an administrator approves and
 * chooses the role; a single-use link then activates the account. Signed in, it asks for the current account. */
function RequestAccessInner() {
  const params = useSearchParams();
  const appId = params.get("app") ?? "";
  const next = params.get("next");
  const { user } = useAuth();
  const [app, setApp] = useState<AppAccess | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [form, setForm] = useState<NewPerson>(EMPTY);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const validId = /^[0-9a-f-]{36}$/i.test(appId);

  useEffect(() => {
    if (!validId) return;
    getAppAccess(appId)
      .then(setApp)
      .catch(() => setLoadError("This app is not available here."));
  }, [appId, validId]);

  const set = (key: keyof NewPerson) => (value: string) => setForm((f) => ({ ...f, [key]: value }));

  async function submit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const body = user ? { requested_role: form.requested_role, message: form.message } : form;
      setDone((await requestAccess(appId, body)).detail);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong.");
    } finally {
      setSubmitting(false);
    }
  }

  const loginHref = isSafeNextPath(next) ? `/login?next=${encodeURIComponent(next)}` : "/login";

  if (!validId || loadError) {
    return (
      <Shell>
        <ErrorBanner message={loadError ?? "Open this page from an app's sign-in page."} />
      </Shell>
    );
  }
  if (!app) return <PageLoading />;

  return (
    <Shell>
      <div className="mb-6 flex flex-col items-center text-center">
        <span className="mb-3 flex h-11 w-11 items-center justify-center rounded-xl bg-brand-50 text-brand-600">
          <Package size={24} aria-hidden="true" />
        </span>
        <h1 className="text-lg font-semibold text-text-primary">Request access to {app.product_name}</h1>
        <p className="mt-0.5 text-sm font-medium text-text-primary">{app.display_name}</p>
        <p className="mt-1 text-sm text-slate-500">
          The shop&apos;s administrator approves each person and chooses their job.
        </p>
      </div>

      {done ? (
        <div className="space-y-4 rounded-xl border border-slate-200 bg-white p-6 text-center">
          <CheckCircle2 className="mx-auto h-8 w-8 text-green-600" aria-hidden="true" />
          <p className="text-sm text-text-primary">{done}</p>
          <Link href={loginHref} className="text-sm text-brand-600 underline underline-offset-4">
            Back to sign in
          </Link>
        </div>
      ) : !app.accepts_requests ? (
        <ErrorBanner message="This shop does not take requests here. Ask the shop's administrator to add you." />
      ) : (
        <form onSubmit={submit} className="space-y-4 rounded-xl border border-slate-200 bg-white p-6">
          {error && <ErrorBanner message={error} />}
          {user ? (
            <p className="text-sm text-text-muted">
              Asking as <strong className="text-text-primary">{user.email}</strong>.
            </p>
          ) : (
            <>
              <div className="grid grid-cols-2 gap-3">
                <Field id="first_name" label="First name" value={form.first_name} onChange={set("first_name")} required />
                <Field id="last_name" label="Last name" value={form.last_name} onChange={set("last_name")} />
              </div>
              <Field id="email" label="Email" type="email" value={form.email} onChange={set("email")} required />
              <Field id="phone" label="Phone" value={form.phone} onChange={set("phone")} />
              <div>
                <Label htmlFor="password">Choose a password</Label>
                <Input
                  id="password"
                  type="password"
                  autoComplete="new-password"
                  required
                  value={form.password}
                  onChange={(e) => set("password")(e.target.value)}
                  placeholder="At least 12 characters"
                />
                <p className="mt-1 text-xs text-text-muted">You sign in with it once your account is activated.</p>
              </div>
            </>
          )}
          <div>
            <Label htmlFor="job">The job you will do</Label>
            <Select id="job" value={form.requested_role} onChange={(e) => set("requested_role")(e.target.value)}>
              <option value="">Let the administrator choose</option>
              {app.roles.map((r) => (
                <option key={r.slug} value={r.slug}>
                  {r.name} — {r.summary}
                </option>
              ))}
            </Select>
          </div>
          <div>
            <Label htmlFor="message">Message to the administrator (optional)</Label>
            <Textarea
              id="message"
              maxLength={500}
              value={form.message}
              onChange={(e) => set("message")(e.target.value)}
            />
          </div>
          <Button type="submit" className="w-full" disabled={submitting}>
            {submitting ? "..." : "Send request"}
          </Button>
        </form>
      )}

      {!done && (
        <p className="mt-5 text-center text-sm text-slate-500">
          Already have access?{" "}
          <Link href={loginHref} className="text-brand-600 underline underline-offset-4 hover:text-brand-500">
            Sign in
          </Link>
        </p>
      )}
    </Shell>
  );
}

function Shell({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-white px-4 py-10">
      <div className="w-full max-w-md">{children}</div>
    </div>
  );
}

function Field({
  id,
  label,
  value,
  onChange,
  type = "text",
  required = false,
}: {
  id: string;
  label: string;
  value: string;
  onChange: (v: string) => void;
  type?: string;
  required?: boolean;
}) {
  return (
    <div>
      <Label htmlFor={id}>{label}</Label>
      <Input id={id} type={type} required={required} value={value} onChange={(e) => onChange(e.target.value)} />
    </div>
  );
}
