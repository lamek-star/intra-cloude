import { Badge, Table, THead, Th, Td, TRow } from "@/components/ui";

type Result = Record<string, unknown>;

// Scalar fields worth surfacing as a badge, in the order they should appear.
const HIGHLIGHT_KEYS = [
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
] as const;

// Keys that carry the tabular payload of an operation, most specific first.
// `analytics.OPERATIONS` returns these as either an array of uniform objects
// (frequency_distribution, time_series_summary) or an array of numbers
// (outlier_sample, moving_average).
const SERIES_KEYS = ["distribution", "points", "outlier_sample", "moving_average"] as const;

function formatValue(v: unknown): string {
  if (v === null || v === undefined) return "—";
  if (typeof v === "number") return Number.isInteger(v) ? String(v) : v.toFixed(4).replace(/\.?0+$/, "");
  if (typeof v === "boolean") return v ? "true" : "false";
  if (typeof v === "object") return JSON.stringify(v);
  return String(v);
}

function findSeries(result: Result): { key: string; rows: unknown[] } | null {
  for (const key of SERIES_KEYS) {
    const v = result[key];
    if (Array.isArray(v) && v.length > 0) return { key, rows: v };
  }
  return null;
}

function isRecord(v: unknown): v is Record<string, unknown> {
  return typeof v === "object" && v !== null && !Array.isArray(v);
}

function SeriesTable({ seriesKey, rows }: { seriesKey: string; rows: unknown[] }) {
  const columns = isRecord(rows[0]) ? Object.keys(rows[0]) : null;

  return (
    <Table>
      <THead>
        {columns ? columns.map((c) => <Th key={c}>{c}</Th>) : <Th>{seriesKey}</Th>}
      </THead>
      <tbody>
        {rows.map((row, i) => (
          <TRow key={i}>
            {columns ? (
              columns.map((c) => <Td key={c}>{formatValue(isRecord(row) ? row[c] : undefined)}</Td>)
            ) : (
              <Td>{formatValue(row)}</Td>
            )}
          </TRow>
        ))}
      </tbody>
    </Table>
  );
}

// Falls back to a key/value table when an operation returns only scalars, so a
// widget asking for a table display still renders something meaningful.
function ScalarTable({ result }: { result: Result }) {
  const entries = Object.entries(result).filter(
    ([k, v]) => k !== "operation" && v !== null && v !== undefined && !Array.isArray(v) && !isRecord(v),
  );
  if (entries.length === 0) return null;

  return (
    <Table>
      <THead>
        <Th>Field</Th>
        <Th>Value</Th>
      </THead>
      <tbody>
        {entries.map(([k, v]) => (
          <TRow key={k}>
            <Td className="whitespace-nowrap text-slate-500">{k}</Td>
            <Td>{formatValue(v)}</Td>
          </TRow>
        ))}
      </tbody>
    </Table>
  );
}

/**
 * Renders one analytics operation result. `display` mirrors a dashboard
 * widget's stored `chart_type`; the tabular view is also used as the fallback
 * for a "stat" widget whose result has no scalar worth badging, so an
 * array-only operation never renders as an empty card.
 */
export function AnalyticsResult({ result, display = "stat" }: { result: Result; display?: string }) {
  const highlights = HIGHLIGHT_KEYS.filter((k) => result[k] !== undefined).map((k) => ({ k, v: result[k] }));
  const series = findSeries(result);
  const showTable = display === "table" || highlights.length === 0;

  return (
    <>
      {highlights.length > 0 && (
        <div className="mb-2 flex flex-wrap gap-2">
          {highlights.map(({ k, v }) => (
            <Badge key={k} tone="info">
              {k}: {formatValue(v)}
            </Badge>
          ))}
        </div>
      )}
      {typeof result.interpretation_note === "string" && (
        <p className="mb-2 text-xs text-amber-700">{result.interpretation_note}</p>
      )}
      {Array.isArray(result.assumptions) && result.assumptions.length > 0 && (
        <p className="mb-2 text-xs text-slate-500">Assumptions: {(result.assumptions as string[]).join("; ")}</p>
      )}
      {showTable && (
        <div className="mb-2">
          {series ? <SeriesTable seriesKey={series.key} rows={series.rows} /> : <ScalarTable result={result} />}
        </div>
      )}
      <details className="text-xs text-slate-500">
        <summary className="cursor-pointer select-none hover:text-slate-600">Full result</summary>
        <pre className="mt-2 overflow-x-auto rounded-md border border-slate-200 bg-slate-50 p-3 text-[11px] text-slate-600">
          {JSON.stringify(result, null, 2)}
        </pre>
      </details>
    </>
  );
}
