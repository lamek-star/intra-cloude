"use client";

import { useEffect, useState, type FormEvent } from "react";
import { api, ApiError, type DBColumn, type DBTable, type TableProfile, type TenantDatabase } from "@/lib/api";
import {
  Badge,
  Button,
  Card,
  ErrorBanner,
  Label,
  PageHeader,
  PageLoading,
  Select,
  Spinner,
} from "@/components/ui";

// Mirrors analytics/data.py's NUMERIC_TYPES/CATEGORICAL_TYPES/TEMPORAL_TYPES
// exactly — the backend rejects a column of the wrong kind for a given
// operation with a 400, but filtering the dropdowns to only offer
// eligible columns up front means an operator only ever discovers that
// by reading this list once, not by trial and error against the API.
const NUMERIC_TYPES = ["integer", "bigint", "decimal"];
const CATEGORICAL_TYPES = ["text", "varchar", "boolean"];
const TEMPORAL_TYPES = ["date", "datetime"];

type FieldSpec =
  | { kind: "column"; key: string; label: string; types: string[] }
  | { kind: "number"; key: string; label: string; default?: number };

type OperationSpec = {
  key: string;
  operation: string; // the actual OPERATIONS registry key -- may repeat across specs (t_test)
  label: string;
  category: "Descriptive" | "Statistical";
  fields: FieldSpec[];
};

const OPERATIONS: OperationSpec[] = [
  { key: "count", operation: "count", label: "Row count", category: "Descriptive", fields: [] },
  {
    key: "distinct_count",
    operation: "distinct_count",
    label: "Distinct value count",
    category: "Descriptive",
    fields: [{ kind: "column", key: "column", label: "Column", types: [...NUMERIC_TYPES, ...CATEGORICAL_TYPES] }],
  },
  {
    key: "missing",
    operation: "missing",
    label: "Missing values",
    category: "Descriptive",
    fields: [{ kind: "column", key: "column", label: "Column", types: [...NUMERIC_TYPES, ...CATEGORICAL_TYPES, ...TEMPORAL_TYPES] }],
  },
  {
    key: "frequency_distribution",
    operation: "frequency_distribution",
    label: "Frequency distribution",
    category: "Descriptive",
    fields: [
      { kind: "column", key: "column", label: "Column", types: [...NUMERIC_TYPES, ...CATEGORICAL_TYPES] },
      { kind: "number", key: "top_n", label: "Top N values", default: 10 },
    ],
  },
  {
    key: "sum",
    operation: "sum",
    label: "Sum",
    category: "Descriptive",
    fields: [{ kind: "column", key: "column", label: "Column", types: NUMERIC_TYPES }],
  },
  {
    key: "mean",
    operation: "mean",
    label: "Mean",
    category: "Descriptive",
    fields: [{ kind: "column", key: "column", label: "Column", types: NUMERIC_TYPES }],
  },
  {
    key: "median",
    operation: "median",
    label: "Median",
    category: "Descriptive",
    fields: [{ kind: "column", key: "column", label: "Column", types: NUMERIC_TYPES }],
  },
  {
    key: "min",
    operation: "min",
    label: "Minimum",
    category: "Descriptive",
    fields: [{ kind: "column", key: "column", label: "Column", types: NUMERIC_TYPES }],
  },
  {
    key: "max",
    operation: "max",
    label: "Maximum",
    category: "Descriptive",
    fields: [{ kind: "column", key: "column", label: "Column", types: NUMERIC_TYPES }],
  },
  {
    key: "stdev",
    operation: "stdev",
    label: "Standard deviation",
    category: "Descriptive",
    fields: [{ kind: "column", key: "column", label: "Column", types: NUMERIC_TYPES }],
  },
  {
    key: "variance",
    operation: "variance",
    label: "Variance",
    category: "Descriptive",
    fields: [{ kind: "column", key: "column", label: "Column", types: NUMERIC_TYPES }],
  },
  {
    key: "outlier_detection",
    operation: "outlier_detection",
    label: "Outlier detection (IQR)",
    category: "Descriptive",
    fields: [{ kind: "column", key: "column", label: "Column", types: NUMERIC_TYPES }],
  },
  {
    key: "pearson_correlation",
    operation: "pearson_correlation",
    label: "Pearson correlation",
    category: "Statistical",
    fields: [
      { kind: "column", key: "column_x", label: "Column X", types: NUMERIC_TYPES },
      { kind: "column", key: "column_y", label: "Column Y", types: NUMERIC_TYPES },
    ],
  },
  {
    key: "spearman_correlation",
    operation: "spearman_correlation",
    label: "Spearman correlation",
    category: "Statistical",
    fields: [
      { kind: "column", key: "column_x", label: "Column X", types: NUMERIC_TYPES },
      { kind: "column", key: "column_y", label: "Column Y", types: NUMERIC_TYPES },
    ],
  },
  {
    key: "linear_regression",
    operation: "linear_regression",
    label: "Linear regression",
    category: "Statistical",
    fields: [
      { kind: "column", key: "column_x", label: "Column X (predictor)", types: NUMERIC_TYPES },
      { kind: "column", key: "column_y", label: "Column Y (outcome)", types: NUMERIC_TYPES },
    ],
  },
  {
    key: "t_test_two_columns",
    operation: "t_test",
    label: "T-test (two columns)",
    category: "Statistical",
    fields: [
      { kind: "column", key: "column", label: "Column A", types: NUMERIC_TYPES },
      { kind: "column", key: "column_b", label: "Column B", types: NUMERIC_TYPES },
    ],
  },
  {
    key: "t_test_grouped",
    operation: "t_test",
    label: "T-test (one column, grouped)",
    category: "Statistical",
    fields: [
      { kind: "column", key: "column", label: "Value column", types: NUMERIC_TYPES },
      { kind: "column", key: "group_column", label: "Group column (exactly 2 groups)", types: CATEGORICAL_TYPES },
    ],
  },
  {
    key: "chi_square",
    operation: "chi_square",
    label: "Chi-square (independence)",
    category: "Statistical",
    fields: [
      { kind: "column", key: "column_a", label: "Column A", types: CATEGORICAL_TYPES },
      { kind: "column", key: "column_b", label: "Column B", types: CATEGORICAL_TYPES },
    ],
  },
  {
    key: "anova",
    operation: "anova",
    label: "One-way ANOVA",
    category: "Statistical",
    fields: [
      { kind: "column", key: "column", label: "Value column", types: NUMERIC_TYPES },
      { kind: "column", key: "group_column", label: "Group column", types: CATEGORICAL_TYPES },
    ],
  },
  {
    key: "time_series_summary",
    operation: "time_series_summary",
    label: "Time series summary",
    category: "Statistical",
    fields: [
      { kind: "column", key: "date_column", label: "Date column", types: TEMPORAL_TYPES },
      { kind: "column", key: "value_column", label: "Value column", types: NUMERIC_TYPES },
      { kind: "number", key: "window", label: "Moving average window", default: 7 },
    ],
  },
];

type AnalysisResult = { spec: OperationSpec; params: Record<string, unknown>; result: Record<string, unknown> };

export default function AnalyticsClient({ tableId }: { tableId: string }) {
  const [table, setTable] = useState<DBTable | null>(null);
  const [database, setDatabase] = useState<TenantDatabase | null>(null);
  const [profile, setProfile] = useState<TableProfile | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [selectedSpecKey, setSelectedSpecKey] = useState<string>(OPERATIONS[0].key);
  const [fieldValues, setFieldValues] = useState<Record<string, string>>({});
  const [running, setRunning] = useState(false);
  const [runError, setRunError] = useState<string | null>(null);
  const [history, setHistory] = useState<AnalysisResult[]>([]);

  useEffect(() => {
    (async () => {
      try {
        const t = await api.get<DBTable>(`/tables/${tableId}/`);
        setTable(t);
        api
          .get<TenantDatabase>(`/tenant-databases/${t.tenant_database}/`)
          .then(setDatabase)
          .catch(() => {});
        const p = await api.get<TableProfile>(`/tables/${tableId}/profile/`);
        setProfile(p);
      } catch (err) {
        setLoadError(err instanceof ApiError ? err.message : "Failed to load table.");
      }
    })();
  }, [tableId]);

  if (!table && !loadError) return <PageLoading />;
  if (loadError && !table) return <ErrorBanner message={loadError} />;
  if (!table) return null;

  const spec = OPERATIONS.find((o) => o.key === selectedSpecKey)!;
  const columnsByType = (types: string[]) => table.columns.filter((c) => types.includes(c.data_type));

  async function handleRun(e: FormEvent) {
    e.preventDefault();
    setRunError(null);
    const params: Record<string, unknown> = {};
    for (const field of spec.fields) {
      const raw = fieldValues[field.key];
      if (field.kind === "column") {
        if (!raw) {
          setRunError(`${field.label} is required.`);
          return;
        }
        params[field.key] = raw;
      } else if (field.kind === "number") {
        params[field.key] = raw ? Number(raw) : field.default;
      }
    }

    setRunning(true);
    try {
      const result = await api.post<Record<string, unknown>>(`/tables/${tableId}/analyze/`, {
        operation: spec.operation,
        params,
      });
      setHistory((prev) => [{ spec, params, result }, ...prev]);
    } catch (err) {
      setRunError(err instanceof ApiError ? err.message : "Analysis failed.");
    } finally {
      setRunning(false);
    }
  }

  return (
    <div>
      <PageHeader
        title={`Analytics — ${table.name}`}
        breadcrumbs={[
          { label: "Organizations", href: "/orgs" },
          ...(database ? [{ label: database.name, href: `/tenant-databases/${database.id}` }] : []),
          { label: table.name, href: `/tables/${tableId}` },
          { label: "Analytics" },
        ]}
      />

      {loadError && (
        <div className="mb-4">
          <ErrorBanner message={loadError} />
        </div>
      )}

      {profile && (
        <div className="mb-8">
          <h2 className="mb-3 text-sm font-semibold text-white">
            Data quality report
            <span className="ml-2 font-normal text-slate-500">
              {profile.row_count} row{profile.row_count === 1 ? "" : "s"} · {profile.column_count} column
              {profile.column_count === 1 ? "" : "s"}
              {profile.truncated ? ` · profiled from a ${profile.sampled_rows}-row sample` : ""}
            </span>
          </h2>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {profile.columns.map((c) => (
              <Card key={c.name}>
                <div className="mb-2 flex items-center justify-between">
                  <span className="text-sm font-medium text-white">{c.name}</span>
                  <Badge>{c.data_type}</Badge>
                </div>
                <dl className="space-y-1 text-xs text-slate-400">
                  <Row label="Missing" value={`${c.missing_count} (${c.null_percentage}%)`} />
                  <Row label="Unique" value={String(c.unique_count)} />
                  {c.mean !== undefined && <Row label="Mean" value={c.mean.toFixed(2)} />}
                  {c.median !== undefined && <Row label="Median" value={c.median.toFixed(2)} />}
                  {c.min !== undefined && c.max !== undefined && (
                    <Row label="Range" value={`${c.min} – ${c.max}`} />
                  )}
                  {c.stdev !== undefined && <Row label="Std dev" value={c.stdev.toFixed(2)} />}
                  {c.potential_outlier_count !== undefined && c.potential_outlier_count > 0 && (
                    <Row label="Potential outliers" value={String(c.potential_outlier_count)} />
                  )}
                  {c.top_values && c.top_values.length > 0 && (
                    <div className="pt-1">
                      <span className="text-slate-500">Top values: </span>
                      {c.top_values
                        .slice(0, 3)
                        .map((tv) => `${String(tv.value)} (${tv.count})`)
                        .join(", ")}
                    </div>
                  )}
                </dl>
              </Card>
            ))}
          </div>
        </div>
      )}

      <div className="mb-8">
        <h2 className="mb-3 text-sm font-semibold text-white">Run an analysis</h2>
        <Card>
          <form onSubmit={handleRun} className="space-y-4">
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div>
                <Label htmlFor="operation-select">Operation</Label>
                <Select
                  id="operation-select"
                  value={selectedSpecKey}
                  onChange={(e) => {
                    setSelectedSpecKey(e.target.value);
                    setFieldValues({});
                    setRunError(null);
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
                  <Label htmlFor={`field-${field.key}`}>{field.label}</Label>
                  {field.kind === "column" ? (
                    <Select
                      id={`field-${field.key}`}
                      value={fieldValues[field.key] ?? ""}
                      onChange={(e) => setFieldValues((prev) => ({ ...prev, [field.key]: e.target.value }))}
                    >
                      <option value="">Select a column…</option>
                      {columnsByType(field.types).map((c: DBColumn) => (
                        <option key={c.id} value={c.name}>
                          {c.name} ({c.data_type})
                        </option>
                      ))}
                    </Select>
                  ) : (
                    <input
                      id={`field-${field.key}`}
                      type="number"
                      value={fieldValues[field.key] ?? String(field.default ?? "")}
                      onChange={(e) => setFieldValues((prev) => ({ ...prev, [field.key]: e.target.value }))}
                      className="w-full rounded-md border border-white/10 bg-white/5 px-3 py-2 text-sm text-slate-100 outline-none focus:border-indigo-400 focus:ring-1 focus:ring-indigo-400"
                    />
                  )}
                </div>
              ))}
            </div>
            {runError && <ErrorBanner message={runError} />}
            <div className="flex justify-end">
              <Button type="submit" disabled={running}>
                {running ? (
                  <>
                    <Spinner className="h-4 w-4" /> Running…
                  </>
                ) : (
                  "Run"
                )}
              </Button>
            </div>
          </form>
        </Card>
      </div>

      {history.length > 0 && (
        <div>
          <h2 className="mb-3 text-sm font-semibold text-white">Results (this session)</h2>
          <div className="space-y-3">
            {history.map((entry, i) => (
              <ResultCard key={i} entry={entry} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-2">
      <span className="text-slate-500">{label}</span>
      <span className="text-slate-300">{value}</span>
    </div>
  );
}

function ResultCard({ entry }: { entry: AnalysisResult }) {
  const { spec, result } = entry;
  const highlightKeys = ["r", "rho", "p_value", "statistic", "slope", "r_squared", "value", "count", "distinct_count", "missing_count", "duplicate_rows", "outlier_count"];
  const highlights = highlightKeys
    .filter((k) => result[k] !== undefined)
    .map((k) => ({ k, v: result[k] }));

  return (
    <Card>
      <div className="mb-2 flex items-center justify-between">
        <span className="text-sm font-medium text-white">{spec.label}</span>
        {typeof result.p_value === "number" && (
          <Badge tone={result.p_value < 0.05 ? "success" : "default"}>
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
      {Array.isArray(result.assumptions) && result.assumptions.length > 0 && (
        <p className="mb-2 text-xs text-slate-500">
          Assumptions: {(result.assumptions as string[]).join("; ")}
        </p>
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
