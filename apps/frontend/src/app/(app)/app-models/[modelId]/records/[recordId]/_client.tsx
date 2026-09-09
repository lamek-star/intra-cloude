"use client";

import { useEffect, useState, type FormEvent } from "react";
import {
  api,
  ApiError,
  type AppFieldDefinition,
  type AppInstance,
  type AppModelDefinition,
  type AppRecordAttachment,
  type AppRelationshipDefinition,
  type AuditEvent,
  type Bucket,
  type FileObject,
  type Paginated,
} from "@/lib/api";
import {
  Badge,
  Button,
  Card,
  EmptyState,
  ErrorBanner,
  Label,
  Modal,
  PageHeader,
  PageLoading,
  Select,
  Spinner,
} from "@/components/ui";
import { useConfirm } from "@/components/ConfirmProvider";
import { FieldValueInput, ReferenceSelect } from "../../_client";

const HISTORY_PAGE_SIZE = 100;

export default function AppRecordClient({ modelId, recordId }: { modelId: string; recordId: string }) {
  const [model, setModel] = useState<AppModelDefinition | null>(null);
  const [instance, setInstance] = useState<AppInstance | null>(null);
  const [fields, setFields] = useState<AppFieldDefinition[] | null>(null);
  const [outgoing, setOutgoing] = useState<AppRelationshipDefinition[]>([]);
  const [record, setRecord] = useState<Record<string, unknown> | null>(null);
  const [values, setValues] = useState<Record<string, string>>({});
  const [attachments, setAttachments] = useState<AppRecordAttachment[] | null>(null);
  const [history, setHistory] = useState<AuditEvent[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [errorDetail, setErrorDetail] = useState<unknown>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [attachModalOpen, setAttachModalOpen] = useState(false);
  const confirm = useConfirm();

  function fieldValuesFrom(row: Record<string, unknown>) {
    const initial: Record<string, string> = {};
    for (const f of fields ?? []) {
      const raw = row[f.id];
      initial[f.id] =
        raw === null || raw === undefined
          ? ""
          : f.data_type === "datetime" && typeof raw === "string"
            ? raw.replace(" ", "T").slice(0, 16)
            : String(raw);
    }
    for (const r of outgoing) {
      const raw = row[r.id];
      initial[r.id] = raw === null || raw === undefined ? "" : String(raw);
    }
    return initial;
  }

  async function load() {
    try {
      const m = await api.get<AppModelDefinition>(`/app-models/${modelId}/`);
      setModel(m);
      const [f, r, inst, rec] = await Promise.all([
        api.get<Paginated<AppFieldDefinition>>(`/app-models/${modelId}/fields/?limit=100`),
        api.get<Paginated<AppRelationshipDefinition>>(
          `/app-instances/${m.instance}/relationships/?limit=500`,
        ),
        api.get<AppInstance>(`/app-instances/${m.instance}/`),
        api.get<Record<string, unknown>>(`/app-models/${modelId}/records/${recordId}/`),
      ]);
      const rels = r.results.filter((rel) => rel.source_model === m.id);
      setFields(f.results);
      setOutgoing(rels);
      setInstance(inst);
      setRecord(rec);
      const initial: Record<string, string> = {};
      for (const field of f.results) {
        const raw = rec[field.id];
        initial[field.id] =
          raw === null || raw === undefined
            ? ""
            : field.data_type === "datetime" && typeof raw === "string"
              ? raw.replace(" ", "T").slice(0, 16)
              : String(raw);
      }
      for (const rel of rels) {
        const raw = rec[rel.id];
        initial[rel.id] = raw === null || raw === undefined ? "" : String(raw);
      }
      setValues(initial);

      api
        .get<AppRecordAttachment[]>(`/app-models/${modelId}/records/${recordId}/attachments/`)
        .then(setAttachments)
        .catch(() => setAttachments([]));

      api
        .get<Paginated<AuditEvent>>(
          `/organizations/${inst.organization}/audit/?resource_type=app_model&resource_id=${modelId}&limit=${HISTORY_PAGE_SIZE}`,
        )
        .then((page) =>
          setHistory(page.results.filter((event) => event.context?.record_id === recordId)),
        )
        .catch(() => setHistory([]));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load this record.");
      setErrorDetail(err);
    }
  }

  useEffect(() => {
    // One-shot fetch-on-mount/param-change, not a state-sync loop.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [modelId, recordId]);

  async function handleSave(e: FormEvent) {
    e.preventDefault();
    if (!fields || !record) return;
    setSaveError(null);
    setSaving(true);
    try {
      const payload: Record<string, unknown> = {};
      for (const f of fields) {
        const raw = values[f.id] ?? "";
        if (raw === "") {
          payload[f.id] = null;
          continue;
        }
        if (f.data_type === "integer") payload[f.id] = parseInt(raw, 10);
        else if (f.data_type === "boolean") payload[f.id] = raw === "true";
        else if (f.data_type === "datetime") payload[f.id] = raw.length === 16 ? `${raw}:00` : raw;
        else payload[f.id] = raw;
      }
      for (const r of outgoing) {
        const raw = values[r.id] ?? "";
        payload[r.id] = raw === "" ? null : raw;
      }
      const updated = await api.patch<Record<string, unknown>>(
        `/app-models/${modelId}/records/${recordId}/`,
        payload,
      );
      setRecord(updated);
      setValues(fieldValuesFrom(updated));
    } catch (err) {
      setSaveError(err instanceof ApiError ? err.message : "Failed to save record.");
    } finally {
      setSaving(false);
    }
  }

  async function handleDetach(attachment: AppRecordAttachment) {
    if (!(await confirm({ title: `Detach "${attachment.filename}"?`, confirmLabel: "Detach" }))) return;
    try {
      await api.del(`/app-models/${modelId}/records/${recordId}/attachments/${attachment.id}/`);
      setAttachments((prev) => prev?.filter((a) => a.id !== attachment.id) ?? null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to detach the file.");
    }
  }

  if (!model && !error) return <PageLoading />;
  if (error && !model) return <ErrorBanner message={error} error={errorDetail} />;
  if (!model || !fields || !record) return null;

  return (
    <div>
      <PageHeader
        title={`${model.label} record`}
        breadcrumbs={[
          { label: "Organizations", href: "/orgs" },
          ...(instance ? [{ label: instance.label, href: `/app-instances/${instance.id}` }] : []),
          { label: model.label, href: `/app-models/${modelId}` },
          { label: String(record.id).slice(0, 8) },
        ]}
      />

      {error && (
        <div className="mb-4">
          <ErrorBanner message={error} error={errorDetail} />
        </div>
      )}

      <Card className="mb-6">
        <form onSubmit={handleSave} className="space-y-3">
          {saveError && <ErrorBanner message={saveError} />}
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
          {outgoing.map((r) => (
            <div key={r.id}>
              <Label htmlFor={`rel-${r.id}`}>{r.label}</Label>
              <ReferenceSelect
                relationship={r}
                id={`rel-${r.id}`}
                value={values[r.id] ?? ""}
                onChange={(v) => setValues((prev) => ({ ...prev, [r.id]: v }))}
                open
              />
            </div>
          ))}
          <div className="flex justify-end pt-1">
            <Button type="submit" disabled={saving}>
              {saving ? "..." : "Save"}
            </Button>
          </div>
        </form>
      </Card>

      <div className="mb-8">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-slate-600">Attachments</h2>
          <Button size="sm" variant="secondary" onClick={() => setAttachModalOpen(true)}>
            Attach file
          </Button>
        </div>
        {attachments === null ? (
          <div className="flex items-center gap-2 text-sm text-slate-500">
            <Spinner className="h-4 w-4" /> Loading...
          </div>
        ) : attachments.length === 0 ? (
          <EmptyState
            title="No attachments"
            description="Attach a file that's already been uploaded to a bucket in this project."
          />
        ) : (
          <div className="space-y-2">
            {attachments.map((a) => (
              <Card key={a.id} className="flex items-center justify-between py-2.5">
                <div>
                  <p className="text-sm font-medium text-slate-900">{a.filename}</p>
                  <p className="text-xs text-slate-500">
                    {a.mime_type} · {a.size} bytes
                    {a.status !== "active" && (
                      <>
                        {" · "}
                        <Badge tone="warning">{a.status}</Badge>
                      </>
                    )}
                  </p>
                </div>
                <div className="flex items-center gap-3 text-xs">
                  <a
                    href={`/api/v1/app-models/${modelId}/records/${recordId}/attachments/${a.id}/download/`}
                    className="text-brand-600 hover:text-brand-500"
                  >
                    Download
                  </a>
                  <button onClick={() => handleDetach(a)} className="text-red-600 hover:text-red-500">
                    Detach
                  </button>
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>

      <div>
        <h2 className="mb-3 text-sm font-semibold text-slate-600">History</h2>
        {history === null ? (
          <div className="flex items-center gap-2 text-sm text-slate-500">
            <Spinner className="h-4 w-4" /> Loading...
          </div>
        ) : history.length === 0 ? (
          <EmptyState
            title="No recorded activity"
            description="Create/update/delete and attachment actions on this record appear here."
          />
        ) : (
          <div className="space-y-1.5">
            {history.map((event) => (
              <div key={event.id} className="flex items-center gap-3 text-xs text-slate-500">
                <span className="whitespace-nowrap text-slate-400">
                  {new Date(event.timestamp).toLocaleString()}
                </span>
                <span className="font-medium text-slate-700">{event.action}</span>
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
              </div>
            ))}
          </div>
        )}
      </div>

      <AttachFileModal
        open={attachModalOpen}
        modelId={modelId}
        recordId={recordId}
        projectId={instance?.project ?? null}
        onClose={() => setAttachModalOpen(false)}
        onAttached={(a) => {
          setAttachments((prev) => [...(prev ?? []), a]);
          setAttachModalOpen(false);
        }}
      />
    </div>
  );
}

function AttachFileModal({
  open,
  modelId,
  recordId,
  projectId,
  onClose,
  onAttached,
}: {
  open: boolean;
  modelId: string;
  recordId: string;
  projectId: string | null;
  onClose: () => void;
  onAttached: (a: AppRecordAttachment) => void;
}) {
  const [buckets, setBuckets] = useState<Bucket[] | null>(null);
  const [bucketId, setBucketId] = useState("");
  const [files, setFiles] = useState<FileObject[] | null>(null);
  const [fileId, setFileId] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!open || !projectId) return;
    // Resets the picker's state whenever the modal reopens.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setBuckets(null);
    setBucketId("");
    setFiles(null);
    setFileId("");
    setError(null);
    api
      .get<Bucket[]>(`/projects/${projectId}/buckets/`)
      .then(setBuckets)
      .catch(() => setBuckets([]));
  }, [open, projectId]);

  useEffect(() => {
    if (!bucketId) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setFiles(null);
      return;
    }
    api
      .get<FileObject[]>(`/buckets/${bucketId}/files/`)
      .then((all) => setFiles(all.filter((f) => f.status === "active")))
      .catch(() => setFiles([]));
  }, [bucketId]);

  async function handleAttach(e: FormEvent) {
    e.preventDefault();
    if (!fileId) return;
    setError(null);
    setSubmitting(true);
    try {
      const attachment = await api.post<AppRecordAttachment>(
        `/app-models/${modelId}/records/${recordId}/attachments/`,
        { file_id: fileId },
      );
      onAttached(attachment);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to attach the file.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Modal open={open} onClose={onClose} title="Attach a file">
      <form onSubmit={handleAttach} className="space-y-4">
        {error && <ErrorBanner message={error} />}
        <div>
          <Label htmlFor="attach-bucket">Bucket</Label>
          <Select
            id="attach-bucket"
            value={bucketId}
            onChange={(e) => {
              setBucketId(e.target.value);
              setFileId("");
            }}
          >
            <option value="">Select a bucket…</option>
            {buckets?.map((b) => (
              <option key={b.id} value={b.id}>
                {b.name}
              </option>
            ))}
          </Select>
        </div>
        {bucketId && (
          <div>
            <Label htmlFor="attach-file">File</Label>
            {files === null ? (
              <p className="text-xs text-slate-500">Loading files…</p>
            ) : files.length === 0 ? (
              <p className="text-xs text-slate-500">This bucket has no active files.</p>
            ) : (
              <Select id="attach-file" value={fileId} onChange={(e) => setFileId(e.target.value)}>
                <option value="">Select a file…</option>
                {files.map((f) => (
                  <option key={f.id} value={f.id}>
                    {f.display_filename}
                  </option>
                ))}
              </Select>
            )}
          </div>
        )}
        <div className="flex justify-end gap-2">
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" disabled={!fileId || submitting}>
            {submitting ? "..." : "Attach"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
