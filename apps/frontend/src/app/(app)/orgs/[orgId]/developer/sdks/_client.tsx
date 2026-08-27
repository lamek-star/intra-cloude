"use client";

import { useEffect, useState } from "react";
import { api, ApiError, type Organization } from "@/lib/api";
import { CopyButton, ErrorBanner, PageHeader, PageLoading } from "@/components/ui";
import { DeveloperNav } from "@/components/DeveloperNav";

const JS_EXAMPLE = `const res = await fetch(
  "https://<your-intracloud-host>/api/v1/buckets/<bucket-id>/files/",
  { headers: { Authorization: "Bearer " + process.env.INTRACLOUD_CREDENTIAL } }
);
const files = await res.json();`;

const PYTHON_EXAMPLE = `import os, requests

res = requests.get(
    "https://<your-intracloud-host>/api/v1/buckets/<bucket-id>/files/",
    headers={"Authorization": f"Bearer {os.environ['INTRACLOUD_CREDENTIAL']}"},
)
files = res.json()`;

const CURL_EXAMPLE = `curl https://<your-intracloud-host>/api/v1/buckets/<bucket-id>/files/ \\
  -H "Authorization: Bearer $INTRACLOUD_CREDENTIAL"`;

export default function SdksClient({ orgId }: { orgId: string }) {
  const [org, setOrg] = useState<Organization | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [errorDetail, setErrorDetail] = useState<unknown>(null);

  useEffect(() => {
    api
      .get<Organization>(`/organizations/${orgId}/`)
      .then(setOrg)
      .catch((err) => {
        setError(err instanceof ApiError ? err.message : "Failed to load organization.");
        setErrorDetail(err);
      });
  }, [orgId]);

  if (!org && !error) return <PageLoading />;
  if (error && !org) return <ErrorBanner message={error} error={errorDetail} />;
  if (!org) return null;

  return (
    <div>
      <PageHeader
        title="SDKs"
        breadcrumbs={[
          { label: "Organizations", href: "/orgs" },
          { label: org.name, href: `/orgs/${orgId}` },
          { label: "Developer", href: `/orgs/${orgId}/developer` },
          { label: "SDKs" },
        ]}
        description="There's no published client library yet — call the API directly with the credential secret from an application's page."
      />
      <DeveloperNav orgId={orgId} active="sdks" />

      <div className="space-y-6">
        <CodeBlock title="JavaScript / TypeScript" code={JS_EXAMPLE} />
        <CodeBlock title="Python" code={PYTHON_EXAMPLE} />
        <CodeBlock title="curl" code={CURL_EXAMPLE} />

        <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
          <p className="font-medium">Keep this credential server-side.</p>
          <p className="mt-1 text-amber-700">
            A credential secret (starts with <code className="rounded bg-white/70 px-1 py-0.5">pdc_sk_</code>)
            grants whatever access its resource grants allow. Never put it in browser JavaScript, a mobile app
            binary, or any other client an end user can inspect — call your own backend, and have your
            backend call Intra-Cloud with the secret.
          </p>
        </div>
      </div>
    </div>
  );
}

function CodeBlock({ title, code }: { title: string; code: string }) {
  return (
    <div>
      <div className="mb-2 flex items-center justify-between">
        <h2 className="text-sm font-semibold text-slate-700">{title}</h2>
        <CopyButton value={code} />
      </div>
      <pre className="overflow-x-auto rounded-2xl border border-slate-200 bg-slate-50 p-4 text-xs text-slate-700">
        {code}
      </pre>
    </div>
  );
}
