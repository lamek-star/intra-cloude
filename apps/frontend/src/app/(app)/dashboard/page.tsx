"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, ApiError, type AuditEvent, type Organization, type Paginated, type Workspace } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { Badge, Card, EmptyState, ErrorBanner, PageHeader, PageLoading, Spinner } from "@/components/ui";

type OrgSummary = { org: Organization; workspaceCount: number | null };

type HealthStatus = "healthy" | "warning" | "unavailable" | "unknown";

type HealthCheck = { name: string; status: HealthStatus; detail?: string };

// Plain same-origin fetch, not the `api` helper: /healthz and /readyz are
// deliberately unauthenticated and unversioned (config/urls.py's own
// comment — "infrastructure endpoints, not part of the public API
// surface"), mounted at the root, not under /api/v1.
async function fetchHealth(path: string): Promise<{ ok: boolean; body: unknown }> {
  try {
    const res = await fetch(path, { credentials: "include" });
    const body = await res.json().catch(() => null);
    return { ok: res.ok, body };
  } catch {
    return { ok: false, body: null };
  }
}

export default function DashboardPage() {
  const { user } = useAuth();
  const router = useRouter();
  const [orgSummaries, setOrgSummaries] = useState<OrgSummary[] | null>(null);
  const [health, setHealth] = useState<HealthCheck[] | null>(null);
  const [recentActivity, setRecentActivity] = useState<AuditEvent[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const orgs = await api.get<Organization[]>("/organizations/");
        // One workspace-count fetch per org, in parallel -- bounded by
        // however many organizations this user actually belongs to
        // (typically a handful), not a deep per-org aggregate over
        // every project/bucket/database, which would be a real N+1
        // problem for a landing page (Section 34: avoid excessive
        // client requests, don't preload thousands of records).
        const summaries = await Promise.all(
          orgs.map(async (org) => {
            try {
              const workspaces = await api.get<Workspace[]>(`/organizations/${org.id}/workspaces/`);
              return { org, workspaceCount: workspaces.length };
            } catch {
              return { org, workspaceCount: null };
            }
          }),
        );
        setOrgSummaries(summaries);

        // Recent activity is genuinely available only when there's
        // exactly one organization to unambiguously show it for, and
        // only if this user holds audit.read there -- fail soft
        // (an empty section, not an error) exactly like the org detail
        // page already does for its members list.
        if (orgs.length === 1) {
          try {
            const events = await api.get<Paginated<AuditEvent>>(
              `/organizations/${orgs[0].id}/audit/?limit=8`,
            );
            setRecentActivity(events.results);
          } catch {
            setRecentActivity([]);
          }
        } else {
          setRecentActivity([]);
        }
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "Failed to load your organizations.");
      }

      const [healthz, readyz] = await Promise.all([fetchHealth("/healthz"), fetchHealth("/readyz")]);
      const checks: HealthCheck[] = [
        { name: "API", status: healthz.ok ? "healthy" : "unavailable" },
      ];
      const readyBody = readyz.body as { checks?: Record<string, string> } | null;
      if (readyBody?.checks) {
        for (const [name, value] of Object.entries(readyBody.checks)) {
          checks.push({ name, status: value === "ok" ? "healthy" : "warning", detail: value });
        }
      } else {
        checks.push({ name: "Readiness", status: readyz.ok ? "healthy" : "unavailable" });
      }
      setHealth(checks);
    })();
  }, []);

  if (orgSummaries === null && !error) return <PageLoading />;

  return (
    <div>
      <PageHeader
        title={`Welcome${user ? `, ${user.first_name || user.email}` : ""}`}
        description="An overview of your organizations and this deployment's health."
      />

      {error && (
        <div className="mb-4">
          <ErrorBanner message={error} />
        </div>
      )}

      <div className="mb-8">
        <h2 className="mb-3 text-sm font-semibold text-slate-300">System health</h2>
        {health === null ? (
          <Card>
            <div className="flex items-center gap-2 text-sm text-slate-500">
              <Spinner className="h-4 w-4" /> Checking...
            </div>
          </Card>
        ) : (
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
            {health.map((check) => (
              <Card key={check.name} className="flex items-center justify-between">
                <span className="text-sm text-slate-300">{check.name}</span>
                <HealthBadge status={check.status} />
              </Card>
            ))}
          </div>
        )}
      </div>

      <div className="mb-8">
        <h2 className="mb-3 text-sm font-semibold text-slate-300">Organizations</h2>
        {orgSummaries && orgSummaries.length === 0 ? (
          <EmptyState
            title="No organizations yet"
            description="Create your first organization to begin managing projects, storage, databases, and applications."
          />
        ) : (
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {orgSummaries?.map(({ org, workspaceCount }) => (
              <button key={org.id} onClick={() => router.push(`/orgs/${org.id}`)} className="text-left">
                <Card className="h-full transition-colors hover:border-indigo-400/40 hover:bg-white/[0.05]">
                  <p className="font-medium text-white">{org.name}</p>
                  <p className="mt-1 text-xs text-slate-500">
                    {workspaceCount === null
                      ? "Workspace count unavailable"
                      : `${workspaceCount} workspace${workspaceCount === 1 ? "" : "s"}`}
                  </p>
                </Card>
              </button>
            ))}
          </div>
        )}
      </div>

      <div>
        <h2 className="mb-3 text-sm font-semibold text-slate-300">Recent activity</h2>
        {recentActivity === null ? (
          <Card>
            <div className="flex items-center gap-2 text-sm text-slate-500">
              <Spinner className="h-4 w-4" /> Loading...
            </div>
          </Card>
        ) : recentActivity.length === 0 ? (
          <EmptyState
            title="No recent activity to show"
            description={
              orgSummaries && orgSummaries.length > 1
                ? "Open an organization to see its own audit log."
                : "Actions across your organization will show up here."
            }
          />
        ) : (
          <Card>
            <ul className="divide-y divide-white/5">
              {recentActivity.map((event) => (
                <li key={event.id} className="flex items-center justify-between gap-4 py-2.5 text-sm">
                  <span className="text-slate-300">
                    {event.action} <span className="text-slate-500">on {event.resource_type}</span>
                  </span>
                  <div className="flex items-center gap-2">
                    <Badge tone={event.result === "success" ? "success" : event.result === "denied" ? "warning" : "danger"}>
                      {event.result}
                    </Badge>
                    <span className="whitespace-nowrap text-xs text-slate-500">
                      {new Date(event.timestamp).toLocaleString()}
                    </span>
                  </div>
                </li>
              ))}
            </ul>
          </Card>
        )}
      </div>
    </div>
  );
}

function HealthBadge({ status }: { status: HealthStatus }) {
  const tones = { healthy: "success", warning: "warning", unavailable: "danger", unknown: "default" } as const;
  const labels = { healthy: "Healthy", warning: "Warning", unavailable: "Unavailable", unknown: "Unknown" };
  return <Badge tone={tones[status]}>{labels[status]}</Badge>;
}
