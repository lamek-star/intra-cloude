"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  Activity,
  Building2,
  ChevronRight,
  HeartPulse,
  History,
  Layers,
} from "lucide-react";
import { api, ApiError, type AuditEvent, type Organization, type Paginated, type Workspace } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { Badge, Card, EmptyState, ErrorBanner, PageHeader, PageLoading, Spinner, StatCard } from "@/components/ui";

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

  const totalWorkspaces = orgSummaries?.reduce((sum, s) => sum + (s.workspaceCount ?? 0), 0) ?? 0;
  const workspaceCountUnknown = orgSummaries?.some((s) => s.workspaceCount === null) ?? false;
  const healthyCount = health?.filter((h) => h.status === "healthy").length ?? 0;
  const healthTotal = health?.length ?? 0;
  const allHealthy = health !== null && healthyCount === healthTotal;

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

      <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          icon={Building2}
          label="Organizations"
          value={orgSummaries?.length ?? 0}
          accent="blue"
        />
        <StatCard
          icon={Layers}
          label="Workspaces"
          value={totalWorkspaces}
          accent="amber"
          detail={workspaceCountUnknown ? "Some counts unavailable" : undefined}
        />
        <StatCard
          icon={HeartPulse}
          label="System health"
          value={health === null ? "…" : `${healthyCount}/${healthTotal}`}
          accent={health === null ? "blue" : allHealthy ? "emerald" : "amber"}
          detail={health === null ? "Checking…" : allHealthy ? "All checks passing" : "Needs attention"}
        />
        <StatCard
          icon={History}
          label="Recent activity"
          value={recentActivity === null ? "…" : recentActivity.length}
          accent="violet"
          detail={
            orgSummaries && orgSummaries.length > 1 ? "Open an org for its log" : "Last 8 events"
          }
        />
      </div>

      <div className="mb-6 grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div>
          <SectionHeader title="Organizations" href={orgSummaries && orgSummaries.length > 0 ? "/orgs" : undefined} />
          {orgSummaries && orgSummaries.length === 0 ? (
            <EmptyState
              title="No organizations yet"
              description="Create your first organization to begin managing projects, storage, databases, and applications."
            />
          ) : (
            <Card className="!p-0">
              <ul className="divide-y divide-slate-100">
                {orgSummaries?.map(({ org, workspaceCount }) => (
                  <li key={org.id}>
                    <button
                      onClick={() => router.push(`/orgs/${org.id}`)}
                      className="flex w-full items-center gap-3 px-5 py-3.5 text-left hover:bg-slate-50"
                    >
                      <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-indigo-50 text-indigo-600">
                        <Building2 className="h-4 w-4" />
                      </span>
                      <span className="min-w-0 flex-1">
                        <span className="block truncate text-sm font-medium text-slate-800">{org.name}</span>
                        <span className="block text-xs text-slate-400">
                          {workspaceCount === null
                            ? "Workspace count unavailable"
                            : `${workspaceCount} workspace${workspaceCount === 1 ? "" : "s"}`}
                        </span>
                      </span>
                      <ChevronRight className="h-4 w-4 shrink-0 text-slate-300" />
                    </button>
                  </li>
                ))}
              </ul>
            </Card>
          )}
        </div>

        <div>
          <SectionHeader title="Recent activity" />
          {recentActivity === null ? (
            <Card>
              <div className="flex items-center gap-2 text-sm text-slate-400">
                <Spinner className="h-4 w-4" /> Loading…
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
            <Card className="!p-0">
              <ul className="divide-y divide-slate-100">
                {recentActivity.map((event) => (
                  <li key={event.id} className="flex items-center gap-3 px-5 py-3.5">
                    <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-violet-50 text-violet-600">
                      <Activity className="h-4 w-4" />
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-sm text-slate-800">
                        {event.action}{" "}
                        <span className="text-slate-400">on {event.resource_type}</span>
                      </span>
                      <span className="block text-xs text-slate-400">
                        {new Date(event.timestamp).toLocaleString()}
                      </span>
                    </span>
                    <Badge
                      tone={
                        event.result === "success"
                          ? "success"
                          : event.result === "denied"
                            ? "warning"
                            : "danger"
                      }
                    >
                      {event.result}
                    </Badge>
                  </li>
                ))}
              </ul>
            </Card>
          )}
        </div>
      </div>

      <div>
        <SectionHeader title="System health" />
        {health === null ? (
          <Card>
            <div className="flex items-center gap-2 text-sm text-slate-400">
              <Spinner className="h-4 w-4" /> Checking…
            </div>
          </Card>
        ) : (
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
            {health.map((check) => (
              <Card key={check.name} className="flex items-center justify-between">
                <span className="text-sm text-slate-600">{check.name}</span>
                <HealthBadge status={check.status} />
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function SectionHeader({ title, href }: { title: string; href?: string }) {
  return (
    <div className="mb-3 flex items-center justify-between">
      <h2 className="text-sm font-semibold text-slate-700">{title}</h2>
      {href && (
        <Link href={href} className="text-xs font-medium text-indigo-600 hover:text-indigo-500">
          View all
        </Link>
      )}
    </div>
  );
}

function HealthBadge({ status }: { status: HealthStatus }) {
  const tones = { healthy: "success", warning: "warning", unavailable: "danger", unknown: "default" } as const;
  const labels = { healthy: "Healthy", warning: "Warning", unavailable: "Unavailable", unknown: "Unknown" };
  return <Badge tone={tones[status]}>{labels[status]}</Badge>;
}
