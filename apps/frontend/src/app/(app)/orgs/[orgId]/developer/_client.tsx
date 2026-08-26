"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { AppWindow, ChevronRight, KeyRound } from "lucide-react";
import { api, ApiError, type Application, type ApplicationCredential, type Organization } from "@/lib/api";
import { Card, EmptyState, ErrorBanner, LinkButton, PageHeader, PageLoading, StatCard } from "@/components/ui";
import { DeveloperNav } from "@/components/DeveloperNav";

function isActiveCredential(c: ApplicationCredential): boolean {
  if (c.revoked_at) return false;
  if (c.expires_at && new Date(c.expires_at) <= new Date()) return false;
  return true;
}

export default function DeveloperOverviewClient({ orgId }: { orgId: string }) {
  const router = useRouter();
  const [org, setOrg] = useState<Organization | null>(null);
  const [applications, setApplications] = useState<Application[] | null>(null);
  const [activeCredentials, setActiveCredentials] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [errorDetail, setErrorDetail] = useState<unknown>(null);

  useEffect(() => {
    (async () => {
      try {
        const [o, apps] = await Promise.all([
          api.get<Organization>(`/organizations/${orgId}/`),
          api.get<Application[]>(`/organizations/${orgId}/applications/`),
        ]);
        setOrg(o);
        setApplications(apps);

        // Bounded by however many applications this org has -- same
        // accepted N+1-but-small pattern as /dashboard's per-org
        // workspace-count fan-out. There's no org-wide credential list
        // endpoint (applications/urls.py only exposes credentials
        // per-application), so this is the honest way to get a real count.
        const perApp = await Promise.all(
          apps.map((app) =>
            api
              .get<ApplicationCredential[]>(`/applications/${app.id}/credentials/`)
              .catch(() => [] as ApplicationCredential[]),
          ),
        );
        setActiveCredentials(perApp.flat().filter(isActiveCredential).length);
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "Failed to load developer overview.");
        setErrorDetail(err);
      }
    })();
  }, [orgId]);

  if (!org && !error) return <PageLoading />;
  if (error && !org) return <ErrorBanner message={error} error={errorDetail} />;
  if (!org) return null;

  return (
    <div>
      <PageHeader
        title="Developer"
        breadcrumbs={[
          { label: "Organizations", href: "/orgs" },
          { label: org.name, href: `/orgs/${orgId}` },
          { label: "Developer" },
        ]}
        description="Register applications, issue scoped credentials, and connect external software to this organization."
      />

      <DeveloperNav orgId={orgId} active="" />

      <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-2">
        <StatCard icon={AppWindow} label="Applications" value={applications?.length ?? 0} accent="blue" />
        <StatCard
          icon={KeyRound}
          label="Active credentials"
          value={activeCredentials === null ? "…" : activeCredentials}
          accent="violet"
          detail="Across all applications"
        />
      </div>

      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-sm font-semibold text-slate-600">Applications</h2>
        <LinkButton href={`/orgs/${orgId}/developer/applications`} size="sm">
          Manage applications
        </LinkButton>
      </div>
      {applications && applications.length === 0 ? (
        <EmptyState
          title="No applications yet"
          description="Register a website, backend service, or AI application to issue it a scoped API credential."
          action={
            <LinkButton href={`/orgs/${orgId}/developer/applications`} size="sm">
              New application
            </LinkButton>
          }
        />
      ) : (
        <Card className="!p-0">
          <ul className="divide-y divide-slate-100">
            {applications?.slice(0, 6).map((app) => (
              <li key={app.id}>
                <button
                  onClick={() => router.push(`/applications/${app.id}`)}
                  className="flex w-full items-center gap-3 px-5 py-3.5 text-left hover:bg-slate-50"
                >
                  <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-blue-50 text-blue-600">
                    <AppWindow className="h-4 w-4" />
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-sm font-medium text-slate-800">{app.name}</span>
                    {app.description && (
                      <span className="block truncate text-xs text-slate-400">{app.description}</span>
                    )}
                  </span>
                  <ChevronRight className="h-4 w-4 shrink-0 text-slate-300" />
                </button>
              </li>
            ))}
          </ul>
        </Card>
      )}
    </div>
  );
}
