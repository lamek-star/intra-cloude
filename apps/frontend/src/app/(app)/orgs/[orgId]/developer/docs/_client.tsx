"use client";

import { useEffect, useState } from "react";
import { ExternalLink } from "lucide-react";
import { api, ApiError, type Organization } from "@/lib/api";
import { Card, ErrorBanner, PageHeader, PageLoading } from "@/components/ui";
import { DeveloperNav } from "@/components/DeveloperNav";

export default function DocsClient({ orgId }: { orgId: string }) {
  const [org, setOrg] = useState<Organization | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .get<Organization>(`/organizations/${orgId}/`)
      .then(setOrg)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load organization."));
  }, [orgId]);

  if (!org && !error) return <PageLoading />;
  if (error && !org) return <ErrorBanner message={error} />;
  if (!org) return null;

  return (
    <div>
      <PageHeader
        title="Docs"
        breadcrumbs={[
          { label: "Organizations", href: "/orgs" },
          { label: org.name, href: `/orgs/${orgId}` },
          { label: "Developer", href: `/orgs/${orgId}/developer` },
          { label: "Docs" },
        ]}
        description="There's no consolidated in-app documentation site yet. Here's what's real and where to find it."
      />
      <DeveloperNav orgId={orgId} active="docs" />

      <div className="space-y-3">
        <a href="/api/v1/organizations/" target="_blank" rel="noreferrer" className="block">
          <Card className="transition-colors hover:border-indigo-400/40 hover:bg-slate-50">
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium text-slate-900">Browsable API</p>
                <p className="mt-1 text-xs text-slate-500">
                  Every endpoint is self-documenting through Django REST Framework&apos;s browsable API — the
                  same requests the frontend makes, inspectable in a browser. Opens{" "}
                  <code className="rounded bg-slate-100 px-1 py-0.5">/api/v1/organizations/</code> as a
                  starting point.
                </p>
              </div>
              <ExternalLink className="h-4 w-4 shrink-0 text-slate-300" />
            </div>
          </Card>
        </a>

        <Card>
          <p className="font-medium text-slate-900">Written guides</p>
          <p className="mt-1 text-xs text-slate-500">
            Architecture, security, deployment, backup/restore, and the end-user guide all live as Markdown
            in the project repository under <code className="rounded bg-slate-100 px-1 py-0.5">docs/</code>{" "}
            — not yet republished as a browsable site from this deployment.
          </p>
        </Card>

        <Card>
          <p className="font-medium text-slate-900">Authentication</p>
          <p className="mt-1 text-xs text-slate-500">
            Applications authenticate with a bearer-token credential — see the SDKs tab for working
            examples in JavaScript, Python, and curl.
          </p>
        </Card>
      </div>
    </div>
  );
}
