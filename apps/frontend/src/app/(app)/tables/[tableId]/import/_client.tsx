"use client";

import { useEffect, useRef, useState } from "react";
import {
  api,
  ApiError,
  type Bucket,
  type ColumnMappingEntry,
  type DBTable,
  type FileObject,
  type ImportJob,
  type ImportJobError,
  type ImportPreview,
  type TenantDatabase,
} from "@/lib/api";
import {
  Badge,
  Button,
  ErrorBanner,
  Label,
  PageHeader,
  PageLoading,
  Select,
  Spinner,
  Table,
  Td,
  Th,
  THead,
  TRow,
} from "@/components/ui";

type Step = "loading" | "source" | "preview" | "running" | "done";

export default function ImportClient({ tableId }: { tableId: string }) {
  const [step, setStep] = useState<Step>("loading");
  const [table, setTable] = useState<DBTable | null>(null);
  const [database, setDatabase] = useState<TenantDatabase | null>(null);
  const [projectId, setProjectId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [errorDetail, setErrorDetail] = useState<unknown>(null);

  const [buckets, setBuckets] = useState<Bucket[] | null>(null);
  const [selectedBucketId, setSelectedBucketId] = useState<string>("");
  const [files, setFiles] = useState<FileObject[] | null>(null);
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [newBucketName, setNewBucketName] = useState("");
  const [creatingBucket, setCreatingBucket] = useState(false);

  const [selectedFile, setSelectedFile] = useState<FileObject | null>(null);
  const [preview, setPreview] = useState<ImportPreview | null>(null);
  const [mapping, setMapping] = useState<Record<string, string>>({}); // csv_column -> target_column ("" = skip)
  const [submitting, setSubmitting] = useState(false);

  const [job, setJob] = useState<ImportJob | null>(null);
  const [jobErrors, setJobErrors] = useState<ImportJobError[] | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const t = await api.get<DBTable>(`/tables/${tableId}/`);
        setTable(t);
        const db = await api.get<TenantDatabase>(`/tenant-databases/${t.tenant_database}/`);
        setDatabase(db);
        setProjectId(db.project);
        const b = await api.get<Bucket[]>(`/projects/${db.project}/buckets/`);
        setBuckets(b);
        if (b.length > 0) {
          setSelectedBucketId(b[0].id);
        }
        setStep("source");
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "Failed to load table.");
        setErrorDetail(err);
      }
    })();
  }, [tableId]);

  useEffect(() => {
    if (!selectedBucketId) return;
    api
      .get<FileObject[]>(`/buckets/${selectedBucketId}/files/`)
      .then((all) => setFiles(all.filter((f) => f.status === "active")))
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load files."));
  }, [selectedBucketId]);

  async function handleCreateBucket() {
    if (!projectId || !newBucketName.trim()) return;
    setCreatingBucket(true);
    setError(null);
    try {
      const bucket = await api.post<Bucket>(`/projects/${projectId}/buckets/`, {
        name: newBucketName.trim(),
      });
      setBuckets((prev) => [...(prev ?? []), bucket]);
      setSelectedBucketId(bucket.id);
      setNewBucketName("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to create bucket.");
      setErrorDetail(err);
    } finally {
      setCreatingBucket(false);
    }
  }

  async function handleUpload(fileList: FileList | null) {
    if (!fileList || fileList.length === 0 || !selectedBucketId) return;
    setUploading(true);
    setError(null);
    try {
      const form = new FormData();
      form.append("file", fileList[0]);
      const uploaded = await api.postForm<FileObject>(`/buckets/${selectedBucketId}/files/`, form);
      setFiles((prev) => [uploaded, ...(prev ?? [])]);
      await handleSelectFile(uploaded);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Upload failed.");
      setErrorDetail(err);
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  async function handleSelectFile(file: FileObject) {
    setError(null);
    try {
      const p = await api.get<ImportPreview>(`/files/${file.id}/import-preview/`);
      setSelectedFile(file);
      setPreview(p);
      const initialMapping: Record<string, string> = {};
      for (const col of p.columns) {
        // Best-effort default: if a CSV header exactly matches an
        // existing (non-primary-key) table column name, pre-select it
        // rather than making the operator map every single column by
        // hand — still fully overridable per row below.
        const match = table?.columns.find((c) => !c.is_primary_key && c.name === col.csv_column);
        initialMapping[col.csv_column] = match ? match.name : "";
      }
      setMapping(initialMapping);
      setStep("preview");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to preview file.");
      setErrorDetail(err);
    }
  }

  async function handleStartImport() {
    if (!table || !selectedFile || !preview) return;
    const columnsByName = new Map(table.columns.map((c) => [c.name, c]));
    const columnMapping: ColumnMappingEntry[] = [];
    for (const [csvColumn, targetColumn] of Object.entries(mapping)) {
      if (!targetColumn) continue;
      const column = columnsByName.get(targetColumn);
      if (!column) continue;
      columnMapping.push({ csv_column: csvColumn, target_column: targetColumn, target_type: column.data_type });
    }
    if (columnMapping.length === 0) {
      setError("Map at least one CSV column to a table column before importing.");
      return;
    }

    setSubmitting(true);
    setError(null);
    try {
      const created = await api.post<ImportJob>(`/tables/${tableId}/imports/`, {
        file_id: selectedFile.id,
        encoding: preview.encoding,
        delimiter: preview.delimiter,
        column_mapping: columnMapping,
      });
      setJob(created);
      setStep("running");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to start import.");
      setErrorDetail(err);
    } finally {
      setSubmitting(false);
    }
  }

  useEffect(() => {
    if (step !== "running" || !job) return;
    let cancelled = false;
    const poll = async () => {
      try {
        const updated = await api.get<ImportJob>(`/imports/${job.id}/`);
        if (cancelled) return;
        setJob(updated);
        if (updated.status === "completed" || updated.status === "failed") {
          if (updated.rejected_rows > 0) {
            api
              .get<ImportJobError[]>(`/imports/${updated.id}/errors/`)
              .then((errs) => !cancelled && setJobErrors(errs))
              .catch(() => {});
          }
          setStep("done");
          return;
        }
        setTimeout(poll, 1500);
      } catch (err) {
        if (!cancelled) setError(err instanceof ApiError ? err.message : "Failed to check import status.");
 setErrorDetail(err);
      }
    };
    poll();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [step, job?.id]);

  if (step === "loading") return <PageLoading />;
  if (error && !table) return <ErrorBanner message={error} error={errorDetail} />;
  if (!table) return null;

  const mappableColumns = table.columns.filter((c) => !c.is_primary_key);

  return (
    <div>
      <PageHeader
        title={`Import CSV into ${table.name}`}
        breadcrumbs={[
          { label: "Organizations", href: "/orgs" },
          ...(database ? [{ label: database.name, href: `/tenant-databases/${database.id}` }] : []),
          { label: table.name, href: `/tables/${tableId}` },
          { label: "Import" },
        ]}
      />

      {error && (
        <div className="mb-4">
          <ErrorBanner message={error} error={errorDetail} />
        </div>
      )}

      {step === "source" && (
        <div className="space-y-6">
          <div>
            <Label htmlFor="bucket-select">Storage bucket</Label>
            {buckets && buckets.length > 0 ? (
              <Select
                id="bucket-select"
                value={selectedBucketId}
                onChange={(e) => {
                  setSelectedBucketId(e.target.value);
                  setSelectedFile(null);
                  setFiles(null);
                }}
                className="max-w-sm"
              >
                {buckets.map((b) => (
                  <option key={b.id} value={b.id}>
                    {b.name}
                  </option>
                ))}
              </Select>
            ) : (
              <p className="text-sm text-slate-500">
                This project has no storage buckets yet — create one below to upload a CSV into.
              </p>
            )}
          </div>

          {(!buckets || buckets.length === 0) && (
            <div className="flex max-w-sm items-end gap-2">
              <div className="flex-1">
                <Label htmlFor="new-bucket-name">New bucket name</Label>
                <input
                  id="new-bucket-name"
                  value={newBucketName}
                  onChange={(e) => setNewBucketName(e.target.value)}
                  placeholder="imports"
                  className="w-full rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-800 outline-none focus:border-indigo-400 focus:ring-1 focus:ring-indigo-400"
                />
              </div>
              <Button onClick={handleCreateBucket} disabled={creatingBucket || !newBucketName.trim()}>
                {creatingBucket ? "..." : "Create bucket"}
              </Button>
            </div>
          )}

          {selectedBucketId && (
            <div>
              <Label htmlFor="csv-file-input">Upload a CSV, or pick one already in this bucket</Label>
              <div className="flex items-center gap-3">
                <input
                  ref={fileInputRef}
                  id="csv-file-input"
                  type="file"
                  accept=".csv,text/csv"
                  onChange={(e) => handleUpload(e.target.files)}
                  disabled={uploading}
                  className="text-sm text-slate-600 file:mr-3 file:rounded-md file:border-0 file:bg-indigo-500 file:px-3 file:py-2 file:text-sm file:font-medium file:text-slate-900 hover:file:bg-indigo-400"
                />
                {uploading && <Spinner className="h-4 w-4 text-slate-400" />}
              </div>

              {files && files.length > 0 && (
                <div className="mt-4">
                  <Table>
                    <THead>
                      <Th>File</Th>
                      <Th>Size</Th>
                      <Th>
                        <span className="sr-only">Action</span>
                      </Th>
                    </THead>
                    <tbody>
                      {files.map((f) => (
                        <TRow key={f.id}>
                          <Td>{f.display_filename}</Td>
                          <Td className="text-slate-400">{formatBytes(f.size)}</Td>
                          <Td>
                            <Button size="sm" variant="secondary" onClick={() => handleSelectFile(f)}>
                              Use this file
                            </Button>
                          </Td>
                        </TRow>
                      ))}
                    </tbody>
                  </Table>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {step === "preview" && preview && selectedFile && (
        <div className="space-y-6">
          <div className="flex flex-wrap items-center gap-2 text-sm text-slate-400">
            <span>
              {selectedFile.display_filename} · detected encoding <Badge>{preview.encoding}</Badge>
              delimiter <Badge>{preview.delimiter === "\t" ? "tab" : preview.delimiter}</Badge>
            </span>
          </div>

          <div>
            <h2 className="mb-2 text-sm font-semibold text-slate-900">Map columns</h2>
            <p className="mb-3 text-sm text-slate-500">
              Each CSV column below can be mapped to an existing column on <strong>{table.name}</strong>, or
              left set to Skip to ignore it. The target type shown is the destination column&apos;s real
              type — rows that fail to convert to it are rejected individually, not the whole import.
            </p>
            <Table>
              <THead>
                <Th>CSV column</Th>
                <Th>Inferred type</Th>
                <Th>Sample values</Th>
                <Th>Import into</Th>
              </THead>
              <tbody>
                {preview.columns.map((col) => {
                  const columnIndex = preview.headers.indexOf(col.csv_column);
                  const samples = preview.sample_rows
                    .slice(0, 3)
                    .map((row) => row[columnIndex])
                    .filter((v) => v !== undefined && v !== "");
                  return (
                    <TRow key={col.csv_column}>
                      <Td className="font-medium text-slate-800">{col.csv_column}</Td>
                      <Td className="text-slate-400">{col.inferred_type}</Td>
                      <Td className="max-w-xs truncate text-slate-500">{samples.join(", ") || "—"}</Td>
                      <Td>
                        <Select
                          value={mapping[col.csv_column] ?? ""}
                          onChange={(e) =>
                            setMapping((prev) => ({ ...prev, [col.csv_column]: e.target.value }))
                          }
                          className="min-w-[10rem]"
                        >
                          <option value="">Skip</option>
                          {mappableColumns.map((c) => (
                            <option key={c.id} value={c.name}>
                              {c.name} ({c.data_type})
                            </option>
                          ))}
                        </Select>
                      </Td>
                    </TRow>
                  );
                })}
              </tbody>
            </Table>
          </div>

          <div className="flex justify-end gap-2">
            <Button
              variant="ghost"
              onClick={() => {
                setStep("source");
                setPreview(null);
                setSelectedFile(null);
              }}
            >
              Back
            </Button>
            <Button onClick={handleStartImport} disabled={submitting}>
              {submitting ? "Starting…" : "Start import"}
            </Button>
          </div>
        </div>
      )}

      {step === "running" && job && (
        <div className="flex flex-col items-center justify-center gap-4 rounded-xl border border-slate-200 py-16">
          <Spinner className="h-6 w-6 text-indigo-600" />
          <p className="text-sm text-slate-600">
            Importing… {job.imported_rows} row{job.imported_rows === 1 ? "" : "s"} imported
            {job.total_rows ? ` of ${job.total_rows}` : ""}
            {job.rejected_rows > 0 ? `, ${job.rejected_rows} rejected so far` : ""}
          </p>
        </div>
      )}

      {step === "done" && job && (
        <div className="space-y-4">
          <div
            className={`rounded-xl border p-5 ${
              job.status === "completed" && job.rejected_rows === 0
                ? "border-emerald-500/30 bg-emerald-500/5"
                : "border-amber-500/30 bg-amber-500/5"
            }`}
          >
            <p className="text-sm font-medium text-slate-900">
              {job.status === "failed" ? "Import failed" : "Import finished"}
            </p>
            <p className="mt-1 text-sm text-slate-600">
              {job.imported_rows} row{job.imported_rows === 1 ? "" : "s"} imported
              {job.rejected_rows > 0 ? `, ${job.rejected_rows} rejected` : ""}
              {job.total_rows ? ` (${job.total_rows} total rows in the file)` : ""}.
            </p>
            {job.error_message && <p className="mt-2 text-sm text-red-600">{job.error_message}</p>}
          </div>

          {jobErrors && jobErrors.length > 0 && (
            <div>
              <h2 className="mb-2 text-sm font-semibold text-slate-900">
                Rejected rows{jobErrors.length >= 200 ? " (first 200)" : ""}
              </h2>
              <Table>
                <THead>
                  <Th>Row</Th>
                  <Th>Reason</Th>
                </THead>
                <tbody>
                  {jobErrors.map((e) => (
                    <TRow key={e.id}>
                      <Td className="font-mono text-xs">{e.row_number}</Td>
                      <Td className="text-red-600">{e.message}</Td>
                    </TRow>
                  ))}
                </tbody>
              </Table>
            </div>
          )}

          <div className="flex gap-2">
            <Button
              variant="secondary"
              onClick={() => {
                setStep("source");
                setJob(null);
                setJobErrors(null);
                setPreview(null);
                setSelectedFile(null);
              }}
            >
              Import another file
            </Button>
            <a
              href={`/tables/${tableId}`}
              className="inline-flex items-center justify-center rounded-md bg-indigo-500 px-3.5 py-2 text-sm font-medium text-slate-900 hover:bg-indigo-400"
            >
              View table
            </a>
          </div>
        </div>
      )}
    </div>
  );
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
