"use client";

import { useEffect, useRef, useState } from "react";
import { FileText } from "lucide-react";
import { api, ApiError, ensureCsrfCookie, type FileObject, type Project } from "@/lib/api";
import {
  Button,
  EmptyState,
  ErrorBanner,
  Input,
  PageHeader,
  PageLoading,
  Spinner,
  Table,
  Td,
  Th,
  THead,
  TRow,
} from "@/components/ui";

function formatBytes(bytes: number): string {
  if (bytes === 0) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  const i = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  return `${(bytes / Math.pow(1024, i)).toFixed(i === 0 ? 0 : 1)} ${units[i]}`;
}

// There's no standalone GET /buckets/{id}/ in this API — a Bucket is only
// ever returned nested inside a project's bucket list
// (storage/urls.py). The project page passes the bucket's name/project id
// through the link's query string so this page doesn't need to guess.
export default function BucketDetailClient({
  bucketId,
  initialName,
  projectId,
}: {
  bucketId: string;
  initialName: string | null;
  projectId: string | null;
}) {
  const [bucketName] = useState(initialName ?? "Bucket");
  const [project, setProject] = useState<Project | null>(null);
  const [files, setFiles] = useState<FileObject[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [search, setSearch] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);

  async function loadFiles(q?: string) {
    const qs = q ? `?search=${encodeURIComponent(q)}` : "";
    setFiles(await api.get<FileObject[]>(`/buckets/${bucketId}/files/${qs}`));
  }

  async function load() {
    try {
      if (projectId) {
        setProject(await api.get<Project>(`/projects/${projectId}/`));
      }
      await loadFiles();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load bucket.");
    }
  }

  useEffect(() => {
    // One-shot fetch-on-mount/param-change, not a state-sync loop — the
    // React Compiler rule can't see that `load` only runs once per
    // `bucketId` change, since it can't statically follow the call.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [bucketId]);

  async function handleUpload(fileList: FileList | null) {
    if (!fileList || fileList.length === 0) return;
    setUploading(true);
    setError(null);
    try {
      await ensureCsrfCookie();
      for (const file of Array.from(fileList)) {
        const form = new FormData();
        form.append("file", file);
        await api.postForm<FileObject>(`/buckets/${bucketId}/files/`, form);
      }
      await loadFiles(search || undefined);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Upload failed.");
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  async function handleDelete(file: FileObject) {
    if (!confirm(`Delete "${file.display_filename}"? This can be restored via the API afterward.`)) return;
    try {
      await api.del(`/files/${file.id}/`);
      setFiles((prev) => prev?.filter((f) => f.id !== file.id) ?? null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Delete failed.");
    }
  }

  if (files === null && !error) return <PageLoading />;

  return (
    <div>
      <PageHeader
        title={bucketName}
        breadcrumbs={[
          { label: "Organizations", href: "/orgs" },
          ...(project ? [{ label: project.name, href: `/projects/${project.id}` }] : []),
          { label: bucketName },
        ]}
        description="Files are streamed through the backend and checksummed/MIME-sniffed on upload."
        actions={
          <>
            <input
              ref={fileInputRef}
              type="file"
              multiple
              className="hidden"
              onChange={(e) => handleUpload(e.target.files)}
            />
            <Button onClick={() => fileInputRef.current?.click()} disabled={uploading}>
              {uploading ? (
                <>
                  <Spinner className="h-3.5 w-3.5" /> Uploading…
                </>
              ) : (
                "Upload files"
              )}
            </Button>
          </>
        }
      />

      {error && (
        <div className="mb-4">
          <ErrorBanner message={error} />
        </div>
      )}

      <div className="mb-3">
        <Input
          placeholder="Search files…"
          value={search}
          onChange={(e) => {
            setSearch(e.target.value);
            loadFiles(e.target.value || undefined);
          }}
          className="max-w-xs"
        />
      </div>

      {files && files.length === 0 ? (
        <EmptyState
          title="No files yet"
          description="Upload a file to get started."
          action={<Button onClick={() => fileInputRef.current?.click()}>Upload files</Button>}
        />
      ) : (
        <Table>
          <THead>
            <Th>Name</Th>
            <Th>Size</Th>
            <Th>Type</Th>
            <Th>Uploaded</Th>
            <Th>
              <span className="sr-only">Actions</span>
            </Th>
          </THead>
          <tbody>
            {files?.map((f) => (
              <TRow key={f.id}>
                <Td className="font-medium text-white">
                  <span className="flex items-center gap-2">
                    <FileText className="h-4 w-4 text-slate-400" />
                    {f.display_filename}
                  </span>
                </Td>
                <Td className="text-slate-400">{formatBytes(f.size)}</Td>
                <Td className="text-slate-500">{f.content_type}</Td>
                <Td className="text-slate-500">{new Date(f.created_at).toLocaleString()}</Td>
                <Td>
                  <div className="flex justify-end gap-3 text-xs">
                    <a
                      href={`/api/v1/files/${f.id}/download/`}
                      className="text-indigo-400 hover:text-indigo-300"
                    >
                      Download
                    </a>
                    <button
                      onClick={() => handleDelete(f)}
                      className="text-red-400 hover:text-red-300"
                    >
                      Delete
                    </button>
                  </div>
                </Td>
              </TRow>
            ))}
          </tbody>
        </Table>
      )}
    </div>
  );
}
