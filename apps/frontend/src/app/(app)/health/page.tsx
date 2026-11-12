"use client";

import { useQuery } from "@tanstack/react-query";
import { CheckCircle2, ShieldAlert, XCircle } from "lucide-react";
import { ApiError } from "@/lib/api";
import { healthSummary } from "@/lib/health";
import { Badge, Card, ErrorBanner, PageHeader, PageLoading } from "@/components/ui";

/** Health history and alerts (Super Administrator): each check every 5 minutes, the last 24 hours hour by hour,
 * and the alerts (a check that failed twice in a row; it closes by itself when the check passes again). */
export default function HealthPage() {
  const data = useQuery({ queryKey: ["system", "health"], queryFn: healthSummary, retry: false, refetchInterval: 60000 });
  if (data.isLoading) return <PageLoading />;
  const forbidden = data.error instanceof ApiError && data.error.status === 403;
  const d = data.data;

  return (
    <div className="max-w-5xl space-y-6">
      <PageHeader title="Health" description="IntraForge checks itself every 5 minutes and keeps two weeks of history." />
      {forbidden ? (
        <Card className="flex items-start gap-3">
          <ShieldAlert aria-hidden="true" className="mt-0.5 h-5 w-5 text-text-muted" />
          <p className="text-sm text-slate-600">Only the Super Administrator can see this installation&apos;s health history.</p>
        </Card>
      ) : data.isError || !d ? (
        <ErrorBanner message="The health history could not be loaded." error={data.error} />
      ) : (
        <>
          <section>
            <h2 className="mb-3 text-sm font-semibold text-slate-600">Alerts</h2>
            {d.alerts.length === 0 ? (
              <Card>
                <p className="text-sm text-green-700">No alerts in the last two weeks.</p>
              </Card>
            ) : (
              <ul className="space-y-2">
                {d.alerts.map((a) => (
                  <li key={`${a.check}-${a.opened_at}`}>
                    <Card className="flex items-start gap-3">
                      {a.closed_at ? (
                        <CheckCircle2 aria-hidden="true" className="mt-0.5 h-5 w-5 text-green-600" />
                      ) : (
                        <XCircle aria-hidden="true" className="mt-0.5 h-5 w-5 text-red-600" />
                      )}
                      <div className="min-w-0 flex-1">
                        <p className="text-sm font-semibold text-slate-900">
                          {a.label} <Badge tone={a.closed_at ? "default" : "danger"}>{a.closed_at ? "Solved" : "Open"}</Badge>
                        </p>
                        {a.detail && <p className="mt-0.5 text-sm text-slate-600">{a.detail}</p>}
                        <p className="mt-0.5 text-xs text-text-muted">
                          Since {new Date(a.opened_at).toLocaleString()}
                          {a.closed_at && ` until ${new Date(a.closed_at).toLocaleString()}`}
                        </p>
                      </div>
                    </Card>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section>
            <h2 className="mb-3 text-sm font-semibold text-slate-600">
              Now {d.latest.at && <span className="font-normal text-text-muted">(checked {new Date(d.latest.at).toLocaleTimeString()})</span>}
            </h2>
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
              {d.latest.checks.map((c) => (
                <Card key={c.check} className="flex items-center justify-between gap-2">
                  <span className="text-sm text-slate-600">{c.label}</span>
                  <Badge tone={c.ok ? "success" : "danger"}>{c.ok ? "OK" : "Failing"}</Badge>
                </Card>
              ))}
            </div>
          </section>

          <section>
            <h2 className="mb-3 text-sm font-semibold text-slate-600">The last 24 hours</h2>
            <Card className="space-y-2 overflow-x-auto">
              {d.hours.map((row) => (
                <div key={row.check} className="flex items-center gap-3">
                  <span className="w-48 shrink-0 truncate text-xs text-slate-600">{row.label}</span>
                  <div className="flex gap-0.5" role="img" aria-label={`${row.label}: ${row.hours.filter((h) => h.failed).length} of ${row.hours.length} hours with a failure`}>
                    {row.hours.map((h) => (
                      <span
                        key={h.hour}
                        title={`${new Date(h.hour).toLocaleString()}: ${h.ok} passed, ${h.failed} failed`}
                        className={`h-5 w-2.5 rounded-sm ${h.failed === 0 ? "bg-green-500" : h.ok === 0 ? "bg-red-500" : "bg-amber-500"}`}
                      />
                    ))}
                  </div>
                </div>
              ))}
              <p className="pt-1 text-xs text-text-muted">Each bar is one hour: green all passed, amber some failed, red all failed.</p>
            </Card>
          </section>
        </>
      )}
    </div>
  );
}
