"use client";

import Link from "next/link";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Activity, AlertTriangle, AppWindow } from "lucide-react";
import { api, ApiError, type Organization } from "@/lib/api";
import { Badge, EmptyState, ErrorBanner, PageHeader, PageLoading, StatCard, Table, Td, Th, THead, TRow } from "@/components/ui";
import { DeveloperNav } from "@/components/DeveloperNav";
import { limitPercent, limitText } from "@/app/(app)/applications/[applicationId]/DailyLimit";

type AppUsage = {
  id: string;
  name: string;
  requests: number;
  errors: number;
  avg_ms: number | null;
  max_ms: number | null;
  last_at: string | null;
  daily_request_limit?: number | null;
  requests_today?: number;
};
type Day = { date: string; requests: number; errors: number };
export type Usage = {
  days: number;
  since: string;
  retention_days: number;
  totals: { requests: number; errors: number };
  applications: AppUsage[];
  daily: Day[];
};

const RANGES = [1, 7, 30];

/** Percentage of failed requests, one decimal; "—" with no requests (not a misleading 0%). */
export function errorRate(requests: number, errors: number): string {
  return requests ? `${((errors / requests) * 100).toFixed(1)}%` : "—";
}

/** Every day of the window, including days with no requests, so a quiet day shows as a gap, not as missing. */
export function fillDays(daily: Day[], days: number, since: string): Day[] {
  const byDate = new Map(daily.map((d) => [d.date, d]));
  const start = new Date(since);
  const out: Day[] = [];
  for (let i = 1; i <= days; i++) {
    const day = new Date(Date.UTC(start.getUTCFullYear(), start.getUTCMonth(), start.getUTCDate() + i));
    const key = day.toISOString().slice(0, 10);
    out.push(byDate.get(key) ?? { date: key, requests: 0, errors: 0 });
  }
  return out;
}

export default function UsageClient({ orgId }: { orgId: string }) {
  const [days, setDays] = useState(7);
  const org = useQuery({ queryKey: ["org", orgId], queryFn: () => api.get<Organization>(`/organizations/${orgId}/`) });
  const usage = useQuery({
    queryKey: ["org", orgId, "api-usage", days],
    queryFn: () => api.get<Usage>(`/organizations/${orgId}/api-usage/?days=${days}`),
    placeholderData: keepPreviousData,
  });

  if (usage.isLoading) return <PageLoading />;
  const data = usage.data;
  const orgName = org.data?.name ?? "Organization";
  const forbidden = usage.error instanceof ApiError && usage.error.status === 403;
  const series = data ? fillDays(data.daily, data.days, data.since) : [];
  const peak = Math.max(1, ...series.map((d) => d.requests));
  const activeApps = data ? data.applications.filter((a) => a.requests > 0).length : 0;

  return (
    <div>
      <PageHeader
        title="Usage"
        description="How much each application uses IntraForge, from its request log."
        breadcrumbs={[
          { label: "Organizations", href: "/orgs" },
          { label: orgName, href: `/orgs/${orgId}` },
          { label: "Developer", href: `/orgs/${orgId}/developer` },
          { label: "Usage" },
        ]}
      />
      <DeveloperNav orgId={orgId} active="usage" />
      {usage.isError && (
        <div className="mb-4">
          <ErrorBanner
            message={forbidden ? "You don't have permission to see applications' usage." : "Usage could not be loaded."}
            error={usage.error}
          />
        </div>
      )}
      <div className="mb-4 flex gap-2" role="group" aria-label="Period">
        {RANGES.filter((d) => !data || d <= data.retention_days).map((d) => (
          <button
            key={d}
            onClick={() => setDays(d)}
            aria-pressed={days === d}
            className={`rounded-lg px-3 py-1.5 text-sm ${days === d ? "bg-brand-600 text-white" : "bg-slate-100 text-slate-700 hover:bg-slate-200"}`}
          >
            {d === 1 ? "24 hours" : `${d} days`}
          </button>
        ))}
      </div>
      {data && (
        <>
          <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-3">
            <StatCard icon={Activity} label="Requests" value={data.totals.requests} accent="blue" />
            <StatCard
              icon={AlertTriangle}
              label="Failed"
              value={data.totals.errors}
              accent="amber"
              detail={errorRate(data.totals.requests, data.totals.errors)}
            />
            <StatCard icon={AppWindow} label="Applications in use" value={`${activeApps} of ${data.applications.length}`} accent="green" />
          </div>
          {days > 1 && (
            <div className="mb-6 rounded-xl border border-slate-200 p-4">
              <p className="mb-3 text-sm font-medium text-slate-600">Requests per day</p>
              <div className="flex h-28 items-end gap-1" aria-label="Requests per day">
                {series.map((d) => (
                  <div
                    key={d.date}
                    className="flex h-full flex-1 flex-col justify-end"
                    title={`${d.date}: ${d.requests} requests, ${d.errors} failed`}
                  >
                    <div className="w-full rounded-t bg-blue-400" style={{ height: `${(d.requests / peak) * 100}%` }}>
                      <div
                        className="w-full rounded-t bg-amber-500"
                        style={{ height: d.requests ? `${(d.errors / d.requests) * 100}%` : 0 }}
                      />
                    </div>
                  </div>
                ))}
              </div>
              <p className="mt-2 text-xs text-text-muted">Blue: requests; amber: failed. Hover a day for numbers.</p>
            </div>
          )}
          {data.applications.length === 0 ? (
            <EmptyState title="No applications yet" description="Register one under Applications; its usage appears here." />
          ) : (
            <Table>
              <THead>
                <Th>Application</Th>
                <Th>Requests</Th>
                <Th>Failed</Th>
                <Th>Average</Th>
                <Th>Slowest</Th>
                <Th>Last request</Th>
                <Th>Today / daily limit</Th>
              </THead>
              <tbody>
                {data.applications.map((a) => (
                  <TRow key={a.id}>
                    <Td>
                      <Link href={`/applications/${a.id}`} className="font-medium text-brand-600 hover:underline">
                        {a.name}
                      </Link>
                    </Td>
                    <Td className="tabular-nums">{a.requests}</Td>
                    <Td className="tabular-nums">
                      {a.errors} <span className="text-xs text-text-muted">({errorRate(a.requests, a.errors)})</span>
                    </Td>
                    <Td className="tabular-nums text-text-muted">{a.avg_ms === null ? "—" : `${a.avg_ms} ms`}</Td>
                    <Td className="tabular-nums text-text-muted">{a.max_ms === null ? "—" : `${a.max_ms} ms`}</Td>
                    <Td className="text-text-muted">{a.last_at ? new Date(a.last_at).toLocaleString() : "None in this period"}</Td>
                    <Td className="tabular-nums">
                      {limitText(a.daily_request_limit, a.requests_today)}
                      {(limitPercent(a.daily_request_limit, a.requests_today) ?? 0) >= 100 && (
                        <span className="ml-2"><Badge tone="danger">Limit reached</Badge></span>
                      )}
                    </Td>
                  </TRow>
                ))}
              </tbody>
            </Table>
          )}
          <p className="mt-3 text-xs text-text-muted">
            Counted from the request log, which keeps {data.retention_days} days. Storage use is on the Storage tab.
          </p>
        </>
      )}
    </div>
  );
}
