"use client";

import { useCallback, useEffect, useState } from "react";
import { RefreshCw, TriangleAlert } from "lucide-react";
import {
  api,
  ApiError,
  type Dashboard,
  type DashboardRenderResult,
  type DashboardWidgetResult,
  type TenantDatabase,
} from "@/lib/api";
import { Badge, Card, ErrorBanner, PageHeader, PageLoading } from "@/components/ui";

export default function DashboardClient({ dashboardId }: { dashboardId: string }) {
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [database, setDatabase] = useState<TenantDatabase | null>(null);
  const [render, setRender] = useState<DashboardRenderResult | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  const loadRender = useCallback(async () => {
    setRefreshing(true);
    try {
      const r = await api.get<DashboardRenderResult>(`/dashboards/${dashboardId}/render/`);
      setRender(r);
    } catch (err) {
      setLoadError(err instanceof ApiError ? err.message : "Failed to render dashboard.");
    } finally {
      setRefreshing(false);
    }
  }, [dashboardId]);

  useEffect(() => {
    (async () => {
      try {
        const d = await api.get<Dashboard>(`/dashboards/${dashboardId}/`);
        setDashboard(d);
        api
          .get<TenantDatabase>(`/tenant-databases/${d.tenant_database}/`)
          .then(setDatabase)
          .catch(() => {});
        await loadRender();
      } catch (err) {
        setLoadError(err instanceof ApiError ? err.message : "Failed to load dashboard.");
      }
    })();
  }, [dashboardId, loadRender]);

  if (!dashboard && !loadError) return <PageLoading />;
  if (loadError && !dashboard) return <ErrorBanner message={loadError} />;
  if (!dashboard) return null;

  return (
    <div>
      <PageHeader
        title={dashboard.name}
        breadcrumbs={[
          { label: "Organizations", href: "/orgs" },
          ...(database
            ? [{ label: database.name, href: `/tenant-databases/${database.id}` }]
            : []),
          { label: dashboard.name },
        ]}
        description="Every widget re-runs against live data and re-checks your permissions each time this page loads."
        actions={
          <button
            onClick={loadRender}
            disabled={refreshing}
            className="flex items-center gap-1.5 rounded-md border border-white/10 px-3 py-1.5 text-sm text-slate-300 hover:bg-white/5 disabled:opacity-50"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${refreshing ? "animate-spin" : ""}`} />
            Refresh
          </button>
        }
      />

      {loadError && (
        <div className="mb-4">
          <ErrorBanner message={loadError} />
        </div>
      )}

      {!render ? (
        <PageLoading />
      ) : render.widgets.length === 0 ? (
        <Card>
          <p className="text-sm text-slate-400">This dashboard has no widgets yet.</p>
        </Card>
      ) : (
        <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
          {render.widgets.map((w, i) => (
            <WidgetCard key={i} widget={w} />
          ))}
        </div>
      )}
    </div>
  );
}

function WidgetCard({ widget }: { widget: DashboardWidgetResult }) {
  if (widget.error) {
    return (
      <Card>
        <div className="mb-2 flex items-center gap-2">
          <TriangleAlert className="h-4 w-4 text-amber-400" />
          <span className="text-sm font-medium text-white">{widget.title || "Untitled widget"}</span>
        </div>
        <p className="text-xs text-amber-300">{widget.error}</p>
      </Card>
    );
  }

  const result = widget.data ?? {};
  const highlightKeys = [
    "r",
    "rho",
    "p_value",
    "statistic",
    "slope",
    "r_squared",
    "value",
    "count",
    "distinct_count",
    "missing_count",
    "duplicate_rows",
    "outlier_count",
  ];
  const highlights = highlightKeys.filter((k) => result[k] !== undefined).map((k) => ({ k, v: result[k] }));

  return (
    <Card>
      <div className="mb-2 flex items-center justify-between">
        <span className="text-sm font-medium text-white">{widget.title || "Untitled widget"}</span>
        {typeof result.p_value === "number" && (
          <Badge tone={(result.p_value as number) < 0.05 ? "success" : "default"}>
            p = {(result.p_value as number).toFixed(4)}
          </Badge>
        )}
      </div>
      {highlights.length > 0 && (
        <div className="mb-2 flex flex-wrap gap-2">
          {highlights.map(({ k, v }) => (
            <Badge key={k} tone="info">
              {k}: {typeof v === "number" ? v.toFixed(4).replace(/\.?0+$/, "") : String(v)}
            </Badge>
          ))}
        </div>
      )}
      {typeof result.interpretation_note === "string" && (
        <p className="mb-2 text-xs text-amber-300">{result.interpretation_note}</p>
      )}
      <details className="text-xs text-slate-500">
        <summary className="cursor-pointer select-none hover:text-slate-300">Full result</summary>
        <pre className="mt-2 overflow-x-auto rounded-md bg-black/30 p-3 text-[11px] text-slate-300">
          {JSON.stringify(result, null, 2)}
        </pre>
      </details>
    </Card>
  );
}
