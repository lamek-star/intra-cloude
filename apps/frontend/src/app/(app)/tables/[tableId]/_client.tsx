"use client";

import { useEffect, useState, type FormEvent } from "react";
import {
  api,
  ApiError,
  type DBColumn,
  type DBTable,
  type RowsPage,
  type TenantDatabase,
} from "@/lib/api";
import {
  Badge,
  Button,
  Checkbox,
  EmptyState,
  ErrorBanner,
  Input,
  Label,
  Modal,
  PageHeader,
  PageLoading,
  Select,
  Table,
  Td,
  Th,
  THead,
  TRow,
} from "@/components/ui";
import { useConfirm } from "@/components/ConfirmProvider";

const DATA_TYPES = [
  "text",
  "varchar",
  "integer",
  "bigint",
  "decimal",
  "boolean",
  "date",
  "datetime",
  "uuid",
  "json",
] as const;

const PAGE_SIZE = 25;

export default function TableDetailClient({ tableId }: { tableId: string }) {
  const [table, setTable] = useState<DBTable | null>(null);
  const [database, setDatabase] = useState<TenantDatabase | null>(null);
  const [page, setPage] = useState<RowsPage | null>(null);
  const [offset, setOffset] = useState(0);
  const [search, setSearch] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [errorDetail, setErrorDetail] = useState<unknown>(null);
  const [columnModalOpen, setColumnModalOpen] = useState(false);
  const [rowModalOpen, setRowModalOpen] = useState(false);
  const [editingRow, setEditingRow] = useState<Record<string, unknown> | null>(null);
  const confirm = useConfirm();

  async function loadTable() {
    const t = await api.get<DBTable>(`/tables/${tableId}/`);
    setTable(t);
    api.get<TenantDatabase>(`/tenant-databases/${t.tenant_database}/`).then(setDatabase).catch(() => {});
  }

  async function loadRows(newOffset = offset, q = search) {
    const params = new URLSearchParams({ limit: String(PAGE_SIZE), offset: String(newOffset) });
    if (q) params.set("search", q);
    setPage(await api.get<RowsPage>(`/tables/${tableId}/rows/?${params.toString()}`));
  }

  async function loadAll() {
    try {
      await loadTable();
      await loadRows(0, "");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load table.");
      setErrorDetail(err);
    }
  }

  useEffect(() => {
    // One-shot fetch-on-mount/param-change, not a state-sync loop.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    loadAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tableId]);

  async function handleDeleteRow(row: Record<string, unknown>) {
    if (!(await confirm({ title: "Delete this row?", confirmLabel: "Delete", danger: true }))) return;
    try {
      await api.del(`/tables/${tableId}/rows/${row.id}/`);
      await loadRows();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to delete row.");
      setErrorDetail(err);
    }
  }

  if (!table && !error) return <PageLoading />;
  if (error && !table) return <ErrorBanner message={error} error={errorDetail} />;
  if (!table) return null;

  const totalPages = page ? Math.max(1, Math.ceil(page.count / PAGE_SIZE)) : 1;
  const currentPage = Math.floor(offset / PAGE_SIZE) + 1;

  return (
    <div>
      <PageHeader
        title={table.name}
        breadcrumbs={[
          { label: "Organizations", href: "/orgs" },
          ...(database
            ? [{ label: database.name, href: `/tenant-databases/${database.id}` }]
            : []),
          { label: table.name },
        ]}
        actions={
          <>
            <a
              href={`/tables/${tableId}/analytics`}
              className="inline-flex items-center rounded-md border border-slate-200 bg-slate-50 px-3.5 py-2 text-sm font-medium text-slate-800 hover:bg-slate-100"
            >
              Analytics
            </a>
            <a
              href={`/tables/${tableId}/import`}
              className="inline-flex items-center rounded-md border border-slate-200 bg-slate-50 px-3.5 py-2 text-sm font-medium text-slate-800 hover:bg-slate-100"
            >
              Import CSV
            </a>
            <a
              href={`/api/v1/tables/${tableId}/rows/export/`}
              className="inline-flex items-center rounded-md border border-slate-200 bg-slate-50 px-3.5 py-2 text-sm font-medium text-slate-800 hover:bg-slate-100"
            >
              Export CSV
            </a>
            <Button variant="secondary" onClick={() => setColumnModalOpen(true)}>
              Add column
            </Button>
            <Button
              onClick={() => {
                setEditingRow(null);
                setRowModalOpen(true);
              }}
            >
              Add row
            </Button>
          </>
        }
      />

      {error && (
        <div className="mb-4">
          <ErrorBanner message={error} error={errorDetail} />
        </div>
      )}

      <div className="mb-3 flex flex-wrap items-center gap-1.5">
        {table.columns.map((c) => (
          <Badge key={c.id} tone={c.is_primary_key ? "info" : "default"}>
            {c.name}: {c.data_type}
            {!c.is_nullable && !c.is_primary_key ? " · required" : ""}
            {c.is_unique && !c.is_primary_key ? " · unique" : ""}
          </Badge>
        ))}
      </div>

      <div className="mb-3">
        <Input
          placeholder="Search text columns…"
          value={search}
          onChange={(e) => {
            setSearch(e.target.value);
            setOffset(0);
            loadRows(0, e.target.value);
          }}
          className="max-w-xs"
        />
      </div>

      {page && page.results.length === 0 ? (
        <EmptyState
          title={search ? "No matching rows" : "No rows yet"}
          description={search ? undefined : "Add a row to start populating this table."}
          action={
            !search && (
              <Button
                onClick={() => {
                  setEditingRow(null);
                  setRowModalOpen(true);
                }}
              >
                Add row
              </Button>
            )
          }
        />
      ) : (
        <>
          <Table>
            <THead>
              {table.columns.map((c) => (
                <Th key={c.id}>{c.name}</Th>
              ))}
              <Th>
                <span className="sr-only">Actions</span>
              </Th>
            </THead>
            <tbody>
              {page?.results.map((row) => (
                <TRow key={String(row.id)}>
                  {table.columns.map((c) => (
                    <Td key={c.id} className={c.is_primary_key ? "font-mono text-xs text-slate-500" : ""}>
                      {formatCell(row[c.name], c.data_type)}
                    </Td>
                  ))}
                  <Td>
                    <div className="flex justify-end gap-3 text-xs">
                      <button
                        onClick={() => {
                          setEditingRow(row);
                          setRowModalOpen(true);
                        }}
                        className="text-indigo-600 hover:text-indigo-500"
                      >
                        Edit
                      </button>
                      <button
                        onClick={() => handleDeleteRow(row)}
                        className="text-red-600 hover:text-red-500"
                      >
                        Delete
                      </button>
                    </div>
                  </Td>
                </TRow>
              ))}
            </tbody>
          </Table>

          {page && page.count > PAGE_SIZE && (
            <div className="mt-3 flex items-center justify-between text-sm text-slate-500">
              <span>
                {page.count} row{page.count === 1 ? "" : "s"} · page {currentPage} of {totalPages}
              </span>
              <div className="flex gap-2">
                <Button
                  size="sm"
                  variant="secondary"
                  disabled={offset === 0}
                  onClick={() => {
                    const next = Math.max(0, offset - PAGE_SIZE);
                    setOffset(next);
                    loadRows(next);
                  }}
                >
                  Previous
                </Button>
                <Button
                  size="sm"
                  variant="secondary"
                  disabled={offset + PAGE_SIZE >= page.count}
                  onClick={() => {
                    const next = offset + PAGE_SIZE;
                    setOffset(next);
                    loadRows(next);
                  }}
                >
                  Next
                </Button>
              </div>
            </div>
          )}
        </>
      )}

      <AddColumnModal
        open={columnModalOpen}
        tableId={tableId}
        onClose={() => setColumnModalOpen(false)}
        onCreated={(col) => {
          setTable((prev) => (prev ? { ...prev, columns: [...prev.columns, col] } : prev));
          setColumnModalOpen(false);
        }}
      />
      <RowFormModal
        open={rowModalOpen}
        tableId={tableId}
        columns={table.columns}
        initialRow={editingRow}
        onClose={() => setRowModalOpen(false)}
        onSaved={() => {
          setRowModalOpen(false);
          loadRows();
        }}
      />
    </div>
  );
}

function formatCell(value: unknown, dataType: string): string {
  if (value === null || value === undefined) return "—";
  if (dataType === "boolean") return value ? "true" : "false";
  if (dataType === "json") return JSON.stringify(value);
  return String(value);
}

function AddColumnModal({
  open,
  tableId,
  onClose,
  onCreated,
}: {
  open: boolean;
  tableId: string;
  onClose: () => void;
  onCreated: (col: DBColumn) => void;
}) {
  const [name, setName] = useState("");
  const [dataType, setDataType] = useState<(typeof DATA_TYPES)[number]>("text");
  const [maxLength, setMaxLength] = useState("255");
  const [precision, setPrecision] = useState("10");
  const [scale, setScale] = useState("2");
  const [isNullable, setIsNullable] = useState(true);
  const [isUnique, setIsUnique] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [errorDetail, setErrorDetail] = useState<unknown>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const col = await api.post<DBColumn>(`/tables/${tableId}/columns/`, {
        name,
        data_type: dataType,
        max_length: dataType === "varchar" ? Number(maxLength) : null,
        precision: dataType === "decimal" ? Number(precision) : null,
        scale: dataType === "decimal" ? Number(scale) : null,
        is_nullable: isNullable,
        is_unique: isUnique,
        default_value: null,
      });
      setName("");
      onCreated(col);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to create column.");
      setErrorDetail(err);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Modal open={open} onClose={onClose} title="Add column">
      <form onSubmit={handleSubmit} className="space-y-4">
        {error && <ErrorBanner message={error} error={errorDetail} />}
        <div>
          <Label htmlFor="col-name">Name</Label>
          <Input
            id="col-name"
            autoFocus
            required
            pattern="[a-z][a-z0-9_]*"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="email"
          />
        </div>
        <div>
          <Label htmlFor="col-type">Type</Label>
          <Select
            id="col-type"
            value={dataType}
            onChange={(e) => setDataType(e.target.value as (typeof DATA_TYPES)[number])}
          >
            {DATA_TYPES.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </Select>
        </div>
        {dataType === "varchar" && (
          <div>
            <Label htmlFor="col-maxlen">Max length</Label>
            <Input
              id="col-maxlen"
              type="number"
              min={1}
              value={maxLength}
              onChange={(e) => setMaxLength(e.target.value)}
            />
          </div>
        )}
        {dataType === "decimal" && (
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label htmlFor="col-precision">Precision</Label>
              <Input
                id="col-precision"
                type="number"
                min={1}
                value={precision}
                onChange={(e) => setPrecision(e.target.value)}
              />
            </div>
            <div>
              <Label htmlFor="col-scale">Scale</Label>
              <Input
                id="col-scale"
                type="number"
                min={0}
                value={scale}
                onChange={(e) => setScale(e.target.value)}
              />
            </div>
          </div>
        )}
        <div className="flex gap-4">
          <label className="flex items-center gap-2 text-sm text-slate-600">
            <Checkbox checked={isNullable} onChange={(e) => setIsNullable(e.target.checked)} />
            Nullable
          </label>
          <label className="flex items-center gap-2 text-sm text-slate-600">
            <Checkbox checked={isUnique} onChange={(e) => setIsUnique(e.target.checked)} />
            Unique
          </label>
        </div>
        <div className="flex justify-end gap-2">
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" disabled={submitting}>
            {submitting ? "..." : "Add column"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

function RowFormModal({
  open,
  tableId,
  columns,
  initialRow,
  onClose,
  onSaved,
}: {
  open: boolean;
  tableId: string;
  columns: DBColumn[];
  initialRow: Record<string, unknown> | null;
  onClose: () => void;
  onSaved: () => void;
}) {
  const editable = columns.filter((c) => !c.is_primary_key);
  const [values, setValues] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [errorDetail, setErrorDetail] = useState<unknown>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!open) return;
    const initial: Record<string, string> = {};
    for (const c of editable) {
      const raw = initialRow?.[c.name];
      initial[c.name] =
        raw === null || raw === undefined
          ? ""
          : c.data_type === "json"
            ? JSON.stringify(raw)
            : c.data_type === "datetime" && typeof raw === "string"
              ? raw.replace(" ", "T").slice(0, 16)
              : String(raw);
    }
    // Resets the form's fields when the modal opens or switches which
    // row it's editing — a prop-change-driven reset, not a render loop.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setValues(initial);
    setError(null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, initialRow]);

  function buildPayload(): Record<string, unknown> {
    const payload: Record<string, unknown> = {};
    for (const c of editable) {
      const raw = values[c.name] ?? "";
      if (raw === "") {
        if (initialRow) payload[c.name] = null;
        continue;
      }
      switch (c.data_type) {
        case "integer":
        case "bigint":
          payload[c.name] = parseInt(raw, 10);
          break;
        case "boolean":
          payload[c.name] = raw === "true";
          break;
        case "datetime":
          payload[c.name] = raw.length === 16 ? `${raw}:00` : raw;
          break;
        case "json":
          try {
            payload[c.name] = JSON.parse(raw);
          } catch {
            payload[c.name] = raw;
          }
          break;
        default:
          payload[c.name] = raw;
      }
    }
    return payload;
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const payload = buildPayload();
      if (initialRow) {
        await api.patch(`/tables/${tableId}/rows/${initialRow.id}/`, payload);
      } else {
        await api.post(`/tables/${tableId}/rows/`, payload);
      }
      onSaved();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to save row.");
      setErrorDetail(err);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Modal open={open} onClose={onClose} title={initialRow ? "Edit row" : "Add row"}>
      <form onSubmit={handleSubmit} className="max-h-[70vh] space-y-3 overflow-y-auto">
        {error && <ErrorBanner message={error} error={errorDetail} />}
        {editable.map((c) => (
          <div key={c.id}>
            <Label htmlFor={`field-${c.name}`}>
              {c.name}
              {!c.is_nullable && <span className="text-red-600"> *</span>}
            </Label>
            <FieldInput
              column={c}
              id={`field-${c.name}`}
              value={values[c.name] ?? ""}
              onChange={(v) => setValues((prev) => ({ ...prev, [c.name]: v }))}
            />
          </div>
        ))}
        <div className="flex justify-end gap-2 pt-1">
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" disabled={submitting}>
            {submitting ? "..." : initialRow ? "Save" : "Add row"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

function FieldInput({
  column,
  id,
  value,
  onChange,
}: {
  column: DBColumn;
  id: string;
  value: string;
  onChange: (v: string) => void;
}) {
  if (column.data_type === "boolean") {
    return (
      <Select id={id} value={value || "false"} onChange={(e) => onChange(e.target.value)}>
        <option value="true">true</option>
        <option value="false">false</option>
      </Select>
    );
  }
  if (column.data_type === "date") {
    return <Input id={id} type="date" value={value} onChange={(e) => onChange(e.target.value)} />;
  }
  if (column.data_type === "datetime") {
    return (
      <Input id={id} type="datetime-local" value={value} onChange={(e) => onChange(e.target.value)} />
    );
  }
  if (column.data_type === "integer" || column.data_type === "bigint") {
    return <Input id={id} type="number" step={1} value={value} onChange={(e) => onChange(e.target.value)} />;
  }
  if (column.data_type === "decimal") {
    return <Input id={id} type="number" step="any" value={value} onChange={(e) => onChange(e.target.value)} />;
  }
  if (column.data_type === "json") {
    return (
      <textarea
        id={id}
        rows={3}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="{}"
        className="w-full rounded-md border border-slate-200 bg-slate-50 px-3 py-2 font-mono text-xs text-slate-800 outline-none focus:border-indigo-400 focus:ring-1 focus:ring-indigo-400"
      />
    );
  }
  return (
    <Input
      id={id}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      maxLength={column.max_length ?? undefined}
    />
  );
}
