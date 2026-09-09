"use client";

import { useEffect, useState, type FormEvent } from "react";
import Link from "next/link";
import {
  api,
  ApiError,
  type AppFieldDataType,
  type AppFieldDefinition,
  type AppInstance,
  type AppModelDefinition,
  type AppRecordsPage,
  type AppRelationshipDefinition,
  type Paginated,
} from "@/lib/api";
import {
  Badge,
  Button,
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

const PAGE_SIZE = 25;

export default function AppModelClient({ modelId }: { modelId: string }) {
  const [model, setModel] = useState<AppModelDefinition | null>(null);
  const [instance, setInstance] = useState<AppInstance | null>(null);
  const [fields, setFields] = useState<AppFieldDefinition[] | null>(null);
  const [outgoing, setOutgoing] = useState<AppRelationshipDefinition[]>([]);
  const [page, setPage] = useState<AppRecordsPage | null>(null);
  const [offset, setOffset] = useState(0);
  const [search, setSearch] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [errorDetail, setErrorDetail] = useState<unknown>(null);
  const [recordsError, setRecordsError] = useState<string | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [editingRecord, setEditingRecord] = useState<Record<string, unknown> | null>(null);
  const confirm = useConfirm();

  async function loadMeta() {
    const m = await api.get<AppModelDefinition>(`/app-models/${modelId}/`);
    setModel(m);
    const [f, r, inst] = await Promise.all([
      api.get<Paginated<AppFieldDefinition>>(`/app-models/${modelId}/fields/?limit=100`),
      api.get<Paginated<AppRelationshipDefinition>>(
        `/app-instances/${m.instance}/relationships/?limit=500`,
      ),
      api.get<AppInstance>(`/app-instances/${m.instance}/`),
    ]);
    setFields(f.results);
    setOutgoing(r.results.filter((rel) => rel.source_model === m.id));
    setInstance(inst);
  }

  async function loadRecords(newOffset = offset, q = search) {
    setRecordsError(null);
    const params = new URLSearchParams({ limit: String(PAGE_SIZE), offset: String(newOffset) });
    if (q) params.set("search", q);
    try {
      setPage(await api.get<AppRecordsPage>(`/app-models/${modelId}/records/?${params.toString()}`));
    } catch (err) {
      setRecordsError(err instanceof ApiError ? err.message : "Failed to load records.");
      setPage(null);
    }
  }

  async function loadAll() {
    try {
      await loadMeta();
      await loadRecords(0, "");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load this model.");
      setErrorDetail(err);
    }
  }

  useEffect(() => {
    // One-shot fetch-on-mount/param-change, not a state-sync loop.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    loadAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [modelId]);

  async function handleDeleteRecord(record: Record<string, unknown>) {
    if (!(await confirm({ title: "Delete this record?", confirmLabel: "Delete", danger: true }))) return;
    try {
      await api.del(`/app-models/${modelId}/records/${record.id}/`);
      await loadRecords();
    } catch (err) {
      setRecordsError(err instanceof ApiError ? err.message : "Failed to delete record.");
    }
  }

  if (!model && !error) return <PageLoading />;
  if (error && !model) return <ErrorBanner message={error} error={errorDetail} />;
  if (!model || !fields) return null;

  const totalPages = page ? Math.max(1, Math.ceil(page.count / PAGE_SIZE)) : 1;
  const currentPage = Math.floor(offset / PAGE_SIZE) + 1;

  return (
    <div>
      <PageHeader
        title={model.label}
        breadcrumbs={[
          { label: "Organizations", href: "/orgs" },
          ...(instance ? [{ label: instance.label, href: `/app-instances/${instance.id}` }] : []),
          { label: model.label },
        ]}
        actions={
          <Button
            onClick={() => {
              setEditingRecord(null);
              setModalOpen(true);
            }}
          >
            Add record
          </Button>
        }
      />

      {error && (
        <div className="mb-4">
          <ErrorBanner message={error} error={errorDetail} />
        </div>
      )}

      <div className="mb-3 flex flex-wrap items-center gap-1.5">
        {fields.map((f) => (
          <Badge key={f.id}>
            {f.label}: {f.data_type}
            {f.required ? " · required" : ""}
          </Badge>
        ))}
        {outgoing.map((r) => (
          <Badge key={r.id} tone="info">
            {r.label}: reference
          </Badge>
        ))}
      </div>

      <div className="mb-3">
        <Input
          placeholder="Search text fields…"
          value={search}
          onChange={(e) => {
            setSearch(e.target.value);
            setOffset(0);
            loadRecords(0, e.target.value);
          }}
          className="max-w-xs"
        />
      </div>

      {recordsError ? (
        <ErrorBanner message={recordsError} />
      ) : page && page.results.length === 0 ? (
        <EmptyState
          title={search ? "No matching records" : "No records yet"}
          description={search ? undefined : "Add a record to start populating this model."}
          action={
            !search && (
              <Button
                onClick={() => {
                  setEditingRecord(null);
                  setModalOpen(true);
                }}
              >
                Add record
              </Button>
            )
          }
        />
      ) : page ? (
        <>
          <Table>
            <THead>
              {fields.map((f) => (
                <Th key={f.id}>{f.label}</Th>
              ))}
              {outgoing.map((r) => (
                <Th key={r.id}>{r.label}</Th>
              ))}
              <Th>
                <span className="sr-only">Actions</span>
              </Th>
            </THead>
            <tbody>
              {page.results.map((record) => (
                <TRow key={String(record.id)}>
                  {fields.map((f) => (
                    <Td key={f.id}>{formatValue(record[f.id], f.data_type)}</Td>
                  ))}
                  {outgoing.map((r) => (
                    <Td key={r.id} className="font-mono text-xs text-slate-500">
                      {record[r.id] ? String(record[r.id]).slice(0, 8) : "—"}
                    </Td>
                  ))}
                  <Td>
                    <div className="flex justify-end gap-3 text-xs">
                      <Link
                        href={`/app-models/${modelId}/records/${record.id}`}
                        className="text-brand-600 hover:text-brand-500"
                      >
                        View
                      </Link>
                      <button
                        onClick={() => {
                          setEditingRecord(record);
                          setModalOpen(true);
                        }}
                        className="text-brand-600 hover:text-brand-500"
                      >
                        Edit
                      </button>
                      <button
                        onClick={() => handleDeleteRecord(record)}
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

          {page.count > PAGE_SIZE && (
            <div className="mt-3 flex items-center justify-between text-sm text-slate-500">
              <span>
                {page.count} record{page.count === 1 ? "" : "s"} · page {currentPage} of {totalPages}
              </span>
              <div className="flex gap-2">
                <Button
                  size="sm"
                  variant="secondary"
                  disabled={offset === 0}
                  onClick={() => {
                    const next = Math.max(0, offset - PAGE_SIZE);
                    setOffset(next);
                    loadRecords(next);
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
                    loadRecords(next);
                  }}
                >
                  Next
                </Button>
              </div>
            </div>
          )}
        </>
      ) : null}

      <RecordFormModal
        open={modalOpen}
        modelId={modelId}
        fields={fields}
        relationships={outgoing}
        initialRecord={editingRecord}
        onClose={() => setModalOpen(false)}
        onSaved={() => {
          setModalOpen(false);
          loadRecords();
        }}
      />
    </div>
  );
}

export function formatValue(value: unknown, dataType: AppFieldDataType): string {
  if (value === null || value === undefined) return "—";
  if (dataType === "boolean") return value ? "true" : "false";
  return String(value);
}

function RecordFormModal({
  open,
  modelId,
  fields,
  relationships,
  initialRecord,
  onClose,
  onSaved,
}: {
  open: boolean;
  modelId: string;
  fields: AppFieldDefinition[];
  relationships: AppRelationshipDefinition[];
  initialRecord: Record<string, unknown> | null;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [values, setValues] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [errorDetail, setErrorDetail] = useState<unknown>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!open) return;
    const initial: Record<string, string> = {};
    for (const f of fields) {
      const raw = initialRecord?.[f.id];
      initial[f.id] =
        raw === null || raw === undefined
          ? ""
          : f.data_type === "datetime" && typeof raw === "string"
            ? raw.replace(" ", "T").slice(0, 16)
            : String(raw);
    }
    for (const r of relationships) {
      const raw = initialRecord?.[r.id];
      initial[r.id] = raw === null || raw === undefined ? "" : String(raw);
    }
    // Resets the form's fields when the modal opens or switches which
    // record it's editing — a prop-change-driven reset, not a render loop.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setValues(initial);
    setError(null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, initialRecord]);

  function buildPayload(): Record<string, unknown> {
    const payload: Record<string, unknown> = {};
    for (const f of fields) {
      const raw = values[f.id] ?? "";
      if (raw === "") {
        if (initialRecord) payload[f.id] = null;
        continue;
      }
      switch (f.data_type) {
        case "integer":
          payload[f.id] = parseInt(raw, 10);
          break;
        case "boolean":
          payload[f.id] = raw === "true";
          break;
        case "datetime":
          payload[f.id] = raw.length === 16 ? `${raw}:00` : raw;
          break;
        default:
          payload[f.id] = raw;
      }
    }
    for (const r of relationships) {
      const raw = values[r.id] ?? "";
      if (raw === "") {
        if (initialRecord) payload[r.id] = null;
        continue;
      }
      payload[r.id] = raw;
    }
    return payload;
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const payload = buildPayload();
      if (initialRecord) {
        await api.patch(`/app-models/${modelId}/records/${initialRecord.id}/`, payload);
      } else {
        await api.post(`/app-models/${modelId}/records/`, payload);
      }
      onSaved();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to save record.");
      setErrorDetail(err);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Modal open={open} onClose={onClose} title={initialRecord ? "Edit record" : "Add record"}>
      <form onSubmit={handleSubmit} className="max-h-[70vh] space-y-3 overflow-y-auto">
        {error && <ErrorBanner message={error} error={errorDetail} />}
        {fields.map((f) => (
          <div key={f.id}>
            <Label htmlFor={`field-${f.id}`}>
              {f.label}
              {f.required && <span className="text-red-600"> *</span>}
            </Label>
            <FieldValueInput
              field={f}
              id={`field-${f.id}`}
              value={values[f.id] ?? ""}
              onChange={(v) => setValues((prev) => ({ ...prev, [f.id]: v }))}
            />
          </div>
        ))}
        {relationships.map((r) => (
          <div key={r.id}>
            <Label htmlFor={`rel-${r.id}`}>{r.label}</Label>
            <ReferenceSelect
              relationship={r}
              id={`rel-${r.id}`}
              value={values[r.id] ?? ""}
              onChange={(v) => setValues((prev) => ({ ...prev, [r.id]: v }))}
              open={open}
            />
          </div>
        ))}
        <div className="flex justify-end gap-2 pt-1">
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" disabled={submitting}>
            {submitting ? "..." : initialRecord ? "Save" : "Add record"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

export function FieldValueInput({
  field,
  id,
  value,
  onChange,
}: {
  field: AppFieldDefinition;
  id: string;
  value: string;
  onChange: (v: string) => void;
}) {
  const required = field.required;
  if (field.data_type === "boolean") {
    return (
      <Select id={id} value={value || "false"} onChange={(e) => onChange(e.target.value)}>
        <option value="true">true</option>
        <option value="false">false</option>
      </Select>
    );
  }
  if (field.data_type === "date") {
    return (
      <Input
        id={id}
        type="date"
        required={required}
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
    );
  }
  if (field.data_type === "datetime") {
    return (
      <Input
        id={id}
        type="datetime-local"
        required={required}
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
    );
  }
  if (field.data_type === "integer") {
    return (
      <Input
        id={id}
        type="number"
        step={1}
        required={required}
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
    );
  }
  if (field.data_type === "decimal") {
    return (
      <Input
        id={id}
        type="number"
        step="any"
        required={required}
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
    );
  }
  return <Input id={id} required={required} value={value} onChange={(e) => onChange(e.target.value)} />;
}

// A reference field's value is another record's id — this picker fetches a
// bounded page of the target model's records and labels each option with
// the first scalar field value found on it (fields are returned in
// creation order, so this is usually the record's "name"-ish field), since
// records have no single designated display field of their own.
export function ReferenceSelect({
  relationship,
  id,
  value,
  onChange,
  open,
}: {
  relationship: AppRelationshipDefinition;
  id: string;
  value: string;
  onChange: (v: string) => void;
  open: boolean;
}) {
  const [options, setOptions] = useState<{ id: string; label: string }[] | null>(null);

  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    api
      .get<AppRecordsPage>(`/app-models/${relationship.target_model}/records/?limit=100`)
      .then((page) => {
        if (cancelled) return;
        setOptions(
          page.results.map((record) => ({
            id: String(record.id),
            label: labelFor(record),
          })),
        );
      })
      .catch(() => {
        if (!cancelled) setOptions([]);
      });
    return () => {
      cancelled = true;
    };
  }, [open, relationship.target_model]);

  if (!options) {
    return (
      <Select id={id} disabled value="">
        <option>Loading…</option>
      </Select>
    );
  }

  return (
    <Select id={id} value={value} onChange={(e) => onChange(e.target.value)}>
      <option value="">—</option>
      {options.map((o) => (
        <option key={o.id} value={o.id}>
          {o.label}
        </option>
      ))}
    </Select>
  );
}

function labelFor(record: Record<string, unknown>): string {
  for (const [key, val] of Object.entries(record)) {
    if (key === "id") continue;
    if (typeof val === "string" && val.trim()) return val;
    if (typeof val === "number" || typeof val === "boolean") return String(val);
  }
  return String(record.id).slice(0, 8);
}
