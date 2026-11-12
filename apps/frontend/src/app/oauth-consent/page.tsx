"use client";

import { Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { Check, ShieldCheck } from "lucide-react";
import { api, ApiError, ensureCsrfCookie } from "@/lib/api";
import { Button, Card, ErrorBanner, Spinner } from "@/components/ui";

type ConsentInfo = { application: string; account: string; scopes: { scope: string; words: string }[] };

/** The consent screen (OAuthClient.requires_consent): an application that is not IntraForge's own asks once
 * before it receives anything about the person. Allow goes back to /oauth/authorize; Deny goes back to the
 * application with access_denied. */
function Consent() {
  const params = useSearchParams();
  const ask = {
    client_id: params.get("client_id") ?? "",
    redirect_uri: params.get("redirect_uri") ?? "",
    scope: params.get("scope") ?? "",
    state: params.get("state") ?? "",
  };
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const info = useQuery({
    queryKey: ["oauth-consent", ask.client_id, ask.scope, ask.redirect_uri],
    queryFn: () =>
      api.get<ConsentInfo>(
        `/oauth/consent/?${new URLSearchParams({ client_id: ask.client_id, redirect_uri: ask.redirect_uri, scope: ask.scope })}`,
      ),
    retry: false,
  });

  async function answer(decision: "allow" | "deny") {
    setBusy(true);
    setError(null);
    try {
      await ensureCsrfCookie();
      const r = await api.post<{ decision: string; redirect?: string }>("/oauth/consent/", { ...ask, decision });
      // Allow: the same sign-in request again, which now goes through. Deny: the server-checked address.
      window.location.assign(decision === "allow" ? `/oauth/authorize?${params.toString()}` : (r.redirect ?? "/"));
    } catch (err) {
      setError(err);
      setBusy(false);
    }
  }

  if (info.isLoading) {
    return (
      <div className="flex justify-center py-10 text-text-muted">
        <Spinner className="h-5 w-5" />
      </div>
    );
  }
  if (info.isError || !info.data) {
    return <ErrorBanner message={info.error instanceof ApiError ? info.error.message : "This sign-in request is not valid."} />;
  }
  return (
    <Card className="space-y-5">
      <div className="flex items-center gap-3">
        <span className="grid h-10 w-10 place-items-center rounded-xl bg-brand-50 text-brand-600">
          <ShieldCheck className="h-5 w-5" aria-hidden="true" />
        </span>
        <div>
          <h1 className="text-lg font-semibold text-slate-900">{info.data.application} wants to sign you in</h1>
          <p className="text-sm text-slate-500">as {info.data.account}</p>
        </div>
      </div>
      <div>
        <p className="text-sm font-medium text-slate-700">It will be able to see:</p>
        <ul className="mt-2 space-y-1.5">
          {info.data.scopes.map((s) => (
            <li key={s.scope} className="flex items-center gap-2 text-sm text-slate-600">
              <Check className="h-4 w-4 text-green-600" aria-hidden="true" /> {s.words}
            </li>
          ))}
        </ul>
        <p className="mt-3 text-xs text-slate-500">Nothing else: not your files, databases or organizations.</p>
      </div>
      {error != null && <ErrorBanner message={error instanceof ApiError ? error.message : "That did not work."} error={error} />}
      <div className="flex justify-end gap-2">
        <Button variant="ghost" onClick={() => void answer("deny")} disabled={busy}>
          Deny
        </Button>
        <Button onClick={() => void answer("allow")} disabled={busy}>
          Allow
        </Button>
      </div>
    </Card>
  );
}

export default function OAuthConsentPage() {
  return (
    <main className="grid min-h-screen place-items-center bg-slate-50 p-6">
      <div className="w-full max-w-md">
        <Suspense fallback={null}>
          <Consent />
        </Suspense>
      </div>
    </main>
  );
}
