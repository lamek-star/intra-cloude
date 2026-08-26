"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { Plus, RefreshCw, Trash2, TriangleAlert, X } from "lucide-react";
import {
  api,
  ApiError,
  type Dashboard,
  type DashboardRenderResult,
  type DashboardWidget,
  type DashboardWidgetResult,
  type DBColumn,
  type DBTable,
  type TenantDatabase,
} from "@/lib/api";
import { OPERATIONS, type OperationSpec } from "@/lib/analytics-operations";
import { Badge, Button, Card, ErrorBanner, Label, Modal, PageHeader, PageLoading, Select, Input } from "@/components/ui";
import { useConfirm } from "@/components/ConfirmProvider";

export default function DashboardClient({ dashboardId }: { dashboardId: string }) {
  const router = useRouter();
  const confirm = useConfirm();
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [database, setDatabase] = useState<TenantDatabase | null>(null);
  const [tables, setTables] = useState<DBTable[]>([]);
  const [render, setRender] = useState<DashboardRenderResult | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [loadErrorDetail, setLoadErrorDetail] = useState<unknown>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [addOpen, setAddOpen] = useState(false);
  const [savingWidgets, setSavingWidgets] = useState(false);

  const loadRender = useCallback(async () => {
    setRefreshing(true);
    try {
      const r = await api.get<DashboardRenderResult>(`/dashboards/${dashboardId}/render/`);
      setRender(r);
    } catch (err) {
      setLoadError(err instanceof ApiError ? err.message : "Failed to render dashboard.");
      setLoadErrorDetail(err);
    } finally {
      setRefreshing(false);
    }
  }, [dashboardId]);

  const load = useCallback(async () => {
    try {
      const d = await api.get<Dashboard>(`/dashboards/${dashboardId}/`);
      setDashboard(d);
      api
        .get<TenantDatabase>(`/tenant-databases/${d.tenant_database}/`)
        .then(setDatabase)
        .catch(() => {});
      api
        .get<DBTable[]>(`/tenant-databases/${d.tenant_database}/tables/`)
        .then(setTables)
        .catch(() => {});
      await loadRender();
    } catch (err) {
      setLoadError(err instanceof ApiError ? err.message : "Failed to load dashboard.");
      setLoadErrorDetail(err);
    }
  }, [dashboardId, loadRender]);

  useEffect(() => {
    // One-shot fetch-on-mount/param-change, not a state-sync loop.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    load();
  }, [load]);

  async function saveWidgets(widgets: DashboardWidget[]) {
    if (!dashboard) return;
    setSavingWidgets(true);
    setLoadError(null);
    try {
      const updated = await api.patch<Dashboard>(`/dashboards/${dashboardId}/`, { widgets });
      setDashboard(updated);
      await loadRender();
    } catch (err) {
      setLoadError(err instanceof ApiError ? err.message : "Failed to update dashboard.");
      setLoadErrorDetail(err);
    } finally {
      setSavingWidgets(false);
    }
  }

  async function removeWidget(index: number) {
    if (!dashboard) return;
    if (!(await confirm({ title: "Remove this widget from the dashboard?", confirmLabel: "Remove", danger: true })))
      return;
    await saveWidgets(dashboard.widgets.filter((_, i) => i !== index));
  }

  async function handleDeleteDashboard() {
    if (!dashboard) return;
    if (
      !(await confirm({
        title: `Delete the dashboard "${dashboard.name}"?`,
        description: "This cannot be undone.",
        confirmLabel: "Delete",
        danger: true,
      }))
    )
      return;
    try {
      await api.del(`/dashboards/${dashboardId}/`);
      router.push(`/tenant-databases/${dashboard.tenant_database}`);
    } catch (err) {
      setLoadError(err instanceof ApiError ? err.message : "Failed to delete dashboard.");
      setLoadErrorDetail(err);
    }
  }

  if (!dashboard && !loadError) return <PageLoading />;
  if (loadError && !dashboard) return <ErrorBanner message={loadError} error={loadErrorDetail} />;
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
          <>
            <Button variant="danger" size="sm" onClick={handleDeleteDashboard}>
              <Trash2 className="h-3.5 w-3.5" />
              Delete
            </Button>
            <Button variant="secondary" size="sm" onClick={loadRender} disabled={refreshing}>
              <RefreshCw className={`h-3.5 w-3.5 ${refreshing ? "animate-spin" : ""}`} />
              Refresh
            </Button>
            <Button size="sm" onClick={() => setAddOpen(true)} disabled={tables.length === 0}>
              <Plus className="h-3.5 w-3.5" />
              Add widget
            </Button>
          </>
        }
      />

      {loadError && (
        <div className="mb-4">
          <ErrorBanner message={loadError} error={loadErrorDetail} />
        </div>
      )}

      {!render ? (
        <PageLoading />
      ) : render.widgets.length === 0 ? (
        <Card>
          <p className="text-sm text-slate-500">
            This dashboard has no widgets yet.{" "}
            {tables.length > 0 ? (
              <button className="text-indigo-600 hover:text-indigo-500" onClick={() => setAddOpen(true)}>
                Add one
              </button>
            ) : (
              "Create a table in this database first."
            )}
          </p>
        </Card>
      ) : (
        <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
          {render.widgets.map((w, i) => (
            <WidgetCard
              key={i}
              widget={w}
              onRemove={() => removeWidget(i)}
              disabled={savingWidgets}
            />
          ))}
        </div>
      )}

      <AddWidgetModal
        open={addOpen}
        tables={tables}
        onClose={() => setAddOpen(false)}
        onAdd={async (widget) => {
          setAddOpen(false);
          await saveWidgets([...dashboard.widgets, widget]);
        }}
      />
    </div>
  );
}

function WidgetCard({
  widget,
  onRemove,
  disabled,
}: {
  widget: DashboardWidgetResult;
  onRemove: () => void;
  disabled: boolean;
}) {
  const removeButton = (
    <button
      onClick={onRemove}
      disabled={disabled}
      aria-label="Remove widget"
      className="rounded p-1 text-slate-300 hover:bg-slate-100 hover:text-red-600 disabled:opacity-50"
    >
      <X className="h-3.5 w-3.5" />
    </button>
  );

  if (widget.error) {
    return (
      <Card>
        <div className="mb-2 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <TriangleAlert className="h-4 w-4 text-amber-600" />
            <span className="text-sm font-medium text-slate-900">{widget.title || "Untitled widget"}</span>
          </div>
          {removeButton}
        </div>
        <p className="text-xs text-amber-700">{widget.error}</p>
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
        <span className="text-sm font-medium text-slate-900">{widget.title || "Untitled widget"}</span>
        <div className="flex items-center gap-2">
          {typeof result.p_value === "number" && (
            <Badge tone={(result.p_value as number) < 0.05 ? "success" : "default"}>
              p = {(result.p_value as number).toFixed(4)}
            </Badge>
          )}
          {removeButton}
        </div>
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
        <p className="mb-2 text-xs text-amber-700">{result.interpretation_note}</p>
      )}
      <details className="text-xs text-slate-500">
        <summary className="cursor-pointer select-none hover:text-slate-600">Full result</summary>
        <pre className="mt-2 overflow-x-auto rounded-md border border-slate-200 bg-slate-50 p-3 text-[11px] text-slate-600">
          {JSON.stringify(result, null, 2)}
        </pre>
      </details>
    </Card>
  );
}

const CHART_TYPES = [
  { value: "stat", label: "Stat" },
  { value: "table", label: "Table" },
];

function AddWidgetModal({
  open,
  tables,
  onClose,
  onAdd,
}: {
  open: boolean;
  tables: DBTable[];
  onClose: () => void;
  onAdd: (widget: DashboardWidget) => Promise<void> | void;
}) {
  const [tableId, setTableId] = useState(tables[0]?.id ?? "");
  const [specKey, setSpecKey] = useState<string>(OPERATIONS[0].key);
  const [fieldValues, setFieldValues] = useState<Record<string, string>>({});
  const [title, setTitle] = useState("");
  const [chartType, setChartType] = useState("stat");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    // Reset the form each time the modal opens, not a state-sync loop.
    if (open) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setTableId(tables[0]?.id ?? "");
      setSpecKey(OPERATIONS[0].key);
      setFieldValues({});
      setTitle("");
      setChartType("stat");
      setError(null);
    }
  }, [open, tables]);

  if (!open) return null;

  const table = tables.find((t) => t.id === tableId) ?? tables[0];
  const spec: OperationSpec = OPERATIONS.find((o) => o.key === specKey)!;
  const columnsByType = (types: string[]) => table?.columns.filter((c: DBColumn) => types.includes(c.data_type)) ?? [];

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    if (!table) {
      setError("Select a table.");
      return;
    }
    const params: Record<string, unknown> = {};
    for (const field of spec.fields) {
      const raw = fieldValues[field.key];
      if (field.kind === "column") {
        if (!raw) {
          setError(`${field.label} is required.`);
          return;
        }
        params[field.key] = raw;
      } else if (field.kind === "number") {
        params[field.key] = raw ? Number(raw) : field.default;
      }
    }

    setSubmitting(true);
    try {
      await onAdd({
        table_id: table.id,
        operation: spec.operation,
        params,
        chart_type: chartType,
        title: title || spec.label,
      });
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Modal open={open} onClose={onClose} title="Add widget">
      <form onSubmit={handleSubmit} className="space-y-4">
        {error && <ErrorBanner message={error} />}
        <div>
          <Label htmlFor="widget-table">Table</Label>
          <Select id="widget-table" value={tableId} onChange={(e) => setTableId(e.target.value)}>
            {tables.map((t) => (
              <option key={t.id} value={t.id}>
                {t.name}
              </option>
            ))}
          </Select>
        </div>
        <div>
          <Label htmlFor="widget-operation">Operation</Label>
          <Select
            id="widget-operation"
            value={specKey}
            onChange={(e) => {
              setSpecKey(e.target.value);
              setFieldValues({});
            }}
          >
            <optgroup label="Descriptive">
              {OPERATIONS.filter((o) => o.category === "Descriptive").map((o) => (
                <option key={o.key} value={o.key}>
                  {o.label}
                </option>
              ))}
            </optgroup>
            <optgroup label="Statistical">
              {OPERATIONS.filter((o) => o.category === "Statistical").map((o) => (
                <option key={o.key} value={o.key}>
                  {o.label}
                </option>
              ))}
            </optgroup>
          </Select>
        </div>
        {spec.fields.map((field) => (
          <div key={field.key}>
            <Label htmlFor={`widget-field-${field.key}`}>{field.label}</Label>
            {field.kind === "column" ? (
              <Select
                id={`widget-field-${field.key}`}
                value={fieldValues[field.key] ?? ""}
                onChange={(e) => setFieldValues((prev) => ({ ...prev, [field.key]: e.target.value }))}
              >
                <option value="">Select a column…</option>
                {columnsByType(field.types).map((c) => (
                  <option key={c.id} value={c.name}>
                    {c.name} ({c.data_type})
                  </option>
                ))}
              </Select>
            ) : (
              <Input
                id={`widget-field-${field.key}`}
                type="number"
                value={fieldValues[field.key] ?? String(field.default ?? "")}
                onChange={(e) => setFieldValues((prev) => ({ ...prev, [field.key]: e.target.value }))}
              />
            )}
          </div>
        ))}
        <div>
          <Label htmlFor="widget-title">Title (optional)</Label>
          <Input
            id="widget-title"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder={spec.label}
          />
        </div>
        <div>
          <Label htmlFor="widget-chart-type">Display as</Label>
          <Select id="widget-chart-type" value={chartType} onChange={(e) => setChartType(e.target.value)}>
            {CHART_TYPES.map((c) => (
              <option key={c.value} value={c.value}>
                {c.label}
              </option>
            ))}
          </Select>
        </div>
        <div className="flex justify-end gap-2">
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" disabled={submitting || tables.length === 0}>
            {submitting ? "..." : "Add widget"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
