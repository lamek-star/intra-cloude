"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { PlugZap, Table as TableIcon } from "lucide-react";
import {
  api,
  ApiError,
  type ConnectedDatabase,
  type ConnectedTableSchema,
  type Organization,
  type Project,
  type RowsPage,
  type Workspace,
} from "@/lib/api";
import {
  Badge,
  Button,
  Card,
  ErrorBanner,
  PageHeader,
  PageLoading,
  Spinner,
  Table,
  Td,
  Th,
  THead,
  TRow,
} from "@/components/ui";
import { ShareSection } from "@/components/ShareSection";

const STATUS_TONE = { untested: "default", connected: "success", unreachable: "danger" } as const;
const ROWS_PER_PAGE = 25;

/** Column headers must come from the schema, not `Object.keys(rows[0])`
 * -- an empty table has zero rows to infer keys from, but still has
 * columns worth showing (Section 28 of the standing brief: does it work
 * when there is no data?). Falls back to inferring from the first row
 * only if the schema lookup somehow misses (defensive, not expected). */
function columnNamesFor(
  schema: ConnectedTableSchema[] | null,
  tableName: string,
  rows: RowsPage,
): string[] {
  const fromSchema = schema?.find((t) => t.name === tableName)?.columns.map((c) => c.name);
  if (fromSchema && fromSchema.length > 0) return fromSchema;
  return Object.keys(rows.results[0] ?? {});
}

export default function ConnectedDatabaseDetailClient({
  connectedDatabaseId,
}: {
  connectedDatabaseId: string;
}) {
  const router = useRouter();
  const [cdb, setCdb] = useState<ConnectedDatabase | null>(null);
  const [project, setProject] = useState<Project | null>(null);
  const [organizationId, setOrganizationId] = useState<string | null>(null);
  const [schema, setSchema] = useState<ConnectedTableSchema[] | null>(null);
  const [schemaError, setSchemaError] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [testing, setTesting] = useState(false);
  const [selectedTable, setSelectedTable] = useState<string | null>(null);
  const [rows, setRows] = useState<RowsPage | null>(null);
  const [rowsError, setRowsError] = useState<string | null>(null);
  const [rowsLoading, setRowsLoading] = useState(false);
  const [offset, setOffset] = useState(0);

  async function load() {
    try {
      const c = await api.get<ConnectedDatabase>(`/connected-databases/${connectedDatabaseId}/`);
      setCdb(c);
      const p = await api.get<Project>(`/projects/${c.project}/`);
      setProject(p);
      api
        .get<Workspace>(`/workspaces/${p.workspace}/`)
        .then((ws) => setOrganizationId(ws.organization))
        .catch(() => {});
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load connected database.");
      return;
    }
    try {
      setSchema(
        await api.get<ConnectedTableSchema[]>(`/connected-databases/${connectedDatabaseId}/schema/`),
      );
    } catch (err) {
      setSchema([]);
      setSchemaError(err instanceof ApiError ? err.message : "Failed to load schema.");
    }
  }

  useEffect(() => {
    // One-shot fetch-on-mount/param-change, not a state-sync loop.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [connectedDatabaseId]);

  async function loadRows(table: string, newOffset: number) {
    setRowsLoading(true);
    setRowsError(null);
    try {
      const page = await api.get<RowsPage>(
        `/connected-databases/${connectedDatabaseId}/tables/${encodeURIComponent(table)}/rows/?limit=${ROWS_PER_PAGE}&offset=${newOffset}`,
      );
      setRows(page);
      setOffset(newOffset);
    } catch (err) {
      setRowsError(err instanceof ApiError ? err.message : "Failed to load rows.");
    } finally {
      setRowsLoading(false);
    }
  }

  async function testConnection() {
    setTesting(true);
    setError(null);
    try {
      const updated = await api.post<ConnectedDatabase>(
        `/connected-databases/${connectedDatabaseId}/test/`,
      );
      setCdb(updated);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to test connection.");
    } finally {
      setTesting(false);
    }
  }

  async function handleDelete() {
    if (!cdb) return;
    if (!confirm(`Remove the connection "${cdb.name}"? This only removes the connection record -- the external database itself is untouched.`)) {
      return;
    }
    try {
      await api.del(`/connected-databases/${connectedDatabaseId}/`);
      router.push(`/projects/${cdb.project}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to remove connection.");
    }
  }

  if (!cdb && !error) return <PageLoading />;
  if (error && !cdb) return <ErrorBanner message={error} />;
  if (!cdb) return null;

  return (
    <div className="space-y-8">
      <PageHeader
        title={cdb.name}
        breadcrumbs={[
          { label: "Organizations", href: "/orgs" },
          ...(project ? [{ label: project.name, href: `/projects/${project.id}` }] : []),
          { label: cdb.name },
        ]}
        description={`${cdb.host}:${cdb.port}/${cdb.database_name} — connected mode, read-only, nothing copied in.`}
        actions={
          <>
            <Button size="sm" variant="secondary" onClick={testConnection} disabled={testing}>
              {testing ? (
                <>
                  <Spinner className="h-3.5 w-3.5" /> Testing…
                </>
              ) : (
                <>
                  <PlugZap className="h-3.5 w-3.5" />
                  Test connection
                </>
              )}
            </Button>
            <Button size="sm" variant="danger" onClick={handleDelete}>
              Remove
            </Button>
          </>
        }
      />

      {error && <ErrorBanner message={error} />}

      <Card>
        <div className="flex flex-wrap items-center gap-6 text-sm">
          <div>
            <p className="text-xs text-slate-500">Status</p>
            <Badge tone={STATUS_TONE[cdb.status]}>{cdb.status}</Badge>
          </div>
          <div>
            <p className="text-xs text-slate-500">Username</p>
            <p className="text-slate-200">{cdb.username}</p>
          </div>
          <div>
            <p className="text-xs text-slate-500">SSL mode</p>
            <p className="text-slate-200">{cdb.sslmode}</p>
          </div>
          <div>
            <p className="text-xs text-slate-500">Last tested</p>
            <p className="text-slate-200">
              {cdb.last_tested_at ? new Date(cdb.last_tested_at).toLocaleString() : "Never"}
            </p>
          </div>
        </div>
        {cdb.status === "unreachable" && cdb.last_test_error && (
          <div className="mt-3">
            <ErrorBanner message={cdb.last_test_error} />
          </div>
        )}
      </Card>

      <section>
        <h2 className="mb-3 text-sm font-semibold text-slate-300">Tables</h2>
        {schemaError && <ErrorBanner message={schemaError} />}
        {schema && schema.length === 0 && !schemaError && (
          <p className="text-sm text-slate-500">
            No tables found, or the connection hasn't been tested yet -- try "Test connection" above.
          </p>
        )}
        {schema && schema.length > 0 && (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-[220px_1fr]">
            <div className="space-y-1">
              {schema.map((t) => (
                <button
                  key={t.name}
                  onClick={() => {
                    setSelectedTable(t.name);
                    loadRows(t.name, 0);
                  }}
                  className={`flex w-full items-center gap-2 rounded-md px-2.5 py-2 text-left text-sm ${
                    selectedTable === t.name
                      ? "bg-indigo-500/15 text-indigo-300"
                      : "text-slate-300 hover:bg-white/5 hover:text-white"
                  }`}
                >
                  <TableIcon className="h-3.5 w-3.5 shrink-0" />
                  <span className="truncate">{t.name}</span>
                </button>
              ))}
            </div>
            <div>
              {!selectedTable && (
                <p className="text-sm text-slate-500">Select a table to browse its rows.</p>
              )}
              {selectedTable && rowsError && <ErrorBanner message={rowsError} />}
              {selectedTable && rowsLoading && <PageLoading />}
              {selectedTable && rows && !rowsLoading && (
                <>
                  <div className="overflow-x-auto">
                    <Table>
                      <THead>
                        {columnNamesFor(schema, selectedTable, rows).map((col) => (
                          <Th key={col}>{col}</Th>
                        ))}
                      </THead>
                      <tbody>
                        {rows.results.map((row, i) => (
                          <TRow key={i}>
                            {columnNamesFor(schema, selectedTable, rows).map((col) => (
                              <Td key={col} className="text-slate-300">
                                {row[col] === null || row[col] === undefined ? (
                                  <span className="text-slate-600">null</span>
                                ) : (
                                  String(row[col])
                                )}
                              </Td>
                            ))}
                          </TRow>
                        ))}
                      </tbody>
                    </Table>
                  </div>
                  {rows.results.length === 0 && (
                    <p className="mt-3 text-sm text-slate-500">This table has no rows.</p>
                  )}
                  <div className="mt-3 flex items-center justify-between text-xs text-slate-500">
                    <span>
                      {rows.count === 0
                        ? "No rows"
                        : `${offset + 1}–${Math.min(offset + ROWS_PER_PAGE, rows.count)} of ${rows.count}`}
                    </span>
                    <div className="flex gap-2">
                      <Button
                        size="sm"
                        variant="secondary"
                        disabled={offset === 0}
                        onClick={() => loadRows(selectedTable, Math.max(0, offset - ROWS_PER_PAGE))}
                      >
                        Previous
                      </Button>
                      <Button
                        size="sm"
                        variant="secondary"
                        disabled={offset + ROWS_PER_PAGE >= rows.count}
                        onClick={() => loadRows(selectedTable, offset + ROWS_PER_PAGE)}
                      >
                        Next
                      </Button>
                    </div>
                  </div>
                </>
              )}
            </div>
          </div>
        )}
      </section>

      {organizationId && (
        <ShareSection
          organizationId={organizationId}
          resourceType="databases.connected_database"
          resourceId={connectedDatabaseId}
        />
      )}
    </div>
  );
}
