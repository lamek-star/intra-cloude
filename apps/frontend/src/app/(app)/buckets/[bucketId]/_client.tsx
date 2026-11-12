"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import { FileText, Folder as FolderIcon, FolderPlus, FolderUp } from "lucide-react";
import { uploadFolder } from "./folderUpload";
import { useProjectTrail } from "@/lib/project-trail";
import {
  api,
  ApiError,
  ensureCsrfCookie,
  type FileObject,
  type Folder,
  type Project,
  type Workspace,
} from "@/lib/api";
import {
  Button,
  EmptyState,
  ErrorBanner,
  Input,
  Label,
  Modal,
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
import { useConfirm } from "@/components/ConfirmProvider";
import { FileVersions } from "./FileVersions";
import { ShareLinks } from "./ShareLinks";
import { CleanupSettings } from "./CleanupSettings";
import { formatBytes } from "./format";

type View = "files" | "trash";

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
  const [bucketName, setBucketName] = useState(initialName ?? "Bucket");
  const [project, setProject] = useState<Project | null>(null);
  const trail = useProjectTrail(project?.id);
  const [organizationId, setOrganizationId] = useState<string | null>(null);
  const [files, setFiles] = useState<FileObject[] | null>(null);
  const [folders, setFolders] = useState<Folder[]>([]);
  // The folders from the top of the bucket down to the one being shown; empty = the top.
  const [path, setPath] = useState<Folder[]>([]);
  const [view, setView] = useState<View>("files");
  const [trashRefused, setTrashRefused] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [errorDetail, setErrorDetail] = useState<unknown>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [search, setSearch] = useState("");
  const [folderModalOpen, setFolderModalOpen] = useState(false);
  const [versionsOf, setVersionsOf] = useState<FileObject | null>(null);
  const [sharing, setSharing] = useState<FileObject | null>(null);
  const [cleanup, setCleanup] = useState<{ trash_days: number; version_days: number } | null>(null);
  const [cleanupOpen, setCleanupOpen] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const folderInputRef = useRef<HTMLInputElement>(null);
  const [folderProgress, setFolderProgress] = useState<string | null>(null);
  const confirm = useConfirm();

  const current = path.length ? path[path.length - 1] : null;

  async function loadContents(at: Folder | null, shown: View, q?: string) {
    const params = new URLSearchParams();
    if (at) params.set("folder", at.id);
    if (q) params.set("search", q);
    if (shown === "trash") params.set("status", "deleted");
    setTrashRefused(false);
    const folderParams = at ? `?parent=${at.id}` : "";
    try {
      // Both at once, shown together: folders arriving after the files made the rows jump.
      const [nextFiles, nextFolders] = await Promise.all([
        api.get<FileObject[]>(`/buckets/${bucketId}/files/?${params.toString()}`),
        shown === "files" && !q ? api.get<Folder[]>(`/buckets/${bucketId}/folders/${folderParams}`) : Promise.resolve([]),
      ]);
      setFolders(nextFolders);
      setFiles(nextFiles);
    } catch (err) {
      if (shown === "trash" && err instanceof ApiError && err.status === 403) {
        setTrashRefused(true);
        setFolders([]);
        setFiles([]);
        return;
      }
      throw err;
    }
  }

  async function load() {
    try {
      // Opened straight from its address (a bookmark, a refresh): the link's name and project are not in the URL,
      // so the bucket itself says them.
      let project = projectId;
      const bucket = await api.get<{ name?: string; project?: string; trash_days?: number; version_days?: number }>(
        `/buckets/${bucketId}/`,
      );
      if (!initialName && bucket.name) setBucketName(bucket.name);
      project = project ?? bucket.project ?? null;
      if (bucket.trash_days !== undefined) setCleanup({ trash_days: bucket.trash_days, version_days: bucket.version_days ?? 0 });
      if (project) {
        const p = await api.get<Project>(`/projects/${project}/`);
        setProject(p);
        // Best-effort, for the Sharing section's organization scope --
        // the file list above doesn't depend on this resolving.
        api
          .get<Workspace>(`/workspaces/${p.workspace}/`)
          .then((ws) => setOrganizationId(ws.organization))
          .catch(() => {});
      }
      await loadContents(null, "files");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load bucket.");
      setErrorDetail(err);
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

  async function show(nextPath: Folder[], nextView: View) {
    setPath(nextPath);
    setView(nextView);
    setSearch("");
    setError(null);
    setNotice(null);
    try {
      await loadContents(nextPath.length ? nextPath[nextPath.length - 1] : null, nextView);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load this folder.");
      setErrorDetail(err);
    }
  }

  async function handleUpload(fileList: FileList | null) {
    if (!fileList || fileList.length === 0) return;
    setUploading(true);
    setError(null);
    setNotice(null);
    try {
      await ensureCsrfCookie();
      for (const file of Array.from(fileList)) {
        const form = new FormData();
        form.append("file", file);
        if (current) form.append("folder", current.id);
        await api.postForm<FileObject>(`/buckets/${bucketId}/files/`, form);
      }
      await loadContents(current, "files", search || undefined);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Upload failed.");
      setErrorDetail(err);
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  async function handleFolderUpload(fileList: FileList | null) {
    if (!fileList || fileList.length === 0) return;
    setUploading(true);
    setError(null);
    setNotice(null);
    try {
      await ensureCsrfCookie();
      const result = await uploadFolder(bucketId, current, Array.from(fileList), (done, total) =>
        setFolderProgress(`${done} of ${total}`),
      );
      await loadContents(current, "files", search || undefined);
      if (result.failed.length === 0) {
        setNotice(`${result.uploaded} ${result.uploaded === 1 ? "file" : "files"} uploaded with their folders.`);
      } else {
        const shown = result.failed.slice(0, 5).map((f) => `${f.path}: ${f.reason}`);
        const more = result.failed.length > 5 ? ` and ${result.failed.length - 5} more` : "";
        setError(`${result.uploaded} uploaded; ${result.failed.length} could not be: ${shown.join("; ")}${more}.`);
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Upload failed.");
      setErrorDetail(err);
    } finally {
      setUploading(false);
      setFolderProgress(null);
      if (folderInputRef.current) folderInputRef.current.value = "";
    }
  }

  async function handleDelete(file: FileObject) {
    if (
      !(await confirm({
        title: `Delete "${file.display_filename}"?`,
        description: "It moves to the Trash, where it can be restored.",
        confirmLabel: "Delete",
        danger: true,
      }))
    )
      return;
    try {
      await api.del(`/files/${file.id}/`);
      setFiles((prev) => prev?.filter((f) => f.id !== file.id) ?? null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Delete failed.");
      setErrorDetail(err);
    }
  }

  async function handleRestore(file: FileObject) {
    setError(null);
    setNotice(null);
    try {
      await ensureCsrfCookie();
      await api.post(`/files/${file.id}/restore/`);
      setFiles((prev) => prev?.filter((f) => f.id !== file.id) ?? null);
      setNotice(`“${file.display_filename}” is back in ${current ? `“${current.name}”` : "the bucket"}.`);
    } catch (err) {
      // 409: quarantined, or the name is in use again -- the server's message says which.
      setError(err instanceof ApiError ? err.message : "Restore failed.");
      setErrorDetail(err);
    }
  }

  if (files === null && !error) return <PageLoading />;

  const inTrash = view === "trash";
  const empty = (files?.length ?? 0) === 0 && folders.length === 0;

  return (
    <div>
      <PageHeader
        title={bucketName}
        breadcrumbs={[{ label: "Organizations", href: "/orgs" }, ...trail, { label: bucketName }]}
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
            <input
              ref={(el) => {
                folderInputRef.current = el;
                // Not in React's types: lets the person choose a folder; its files keep their paths.
                el?.setAttribute("webkitdirectory", "");
              }}
              type="file"
              multiple
              className="hidden"
              data-testid="folder-input"
              onChange={(e) => void handleFolderUpload(e.target.files)}
            />
            {cleanup && (
              <Button variant="ghost" onClick={() => setCleanupOpen(true)}>
                Cleanup
              </Button>
            )}
            {!inTrash && (
              <Button variant="secondary" onClick={() => setFolderModalOpen(true)}>
                <FolderPlus aria-hidden="true" className="h-4 w-4" />
                New folder
              </Button>
            )}
            {!inTrash && (
              <Button variant="secondary" onClick={() => folderInputRef.current?.click()} disabled={uploading}>
                <FolderUp aria-hidden="true" className="h-4 w-4" />
                {folderProgress ? `Uploading ${folderProgress}` : "Upload folder"}
              </Button>
            )}
            <Button onClick={() => fileInputRef.current?.click()} disabled={uploading || inTrash}>
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
          <ErrorBanner message={error} error={errorDetail} />
        </div>
      )}
      <div aria-live="polite" className="mb-2 text-sm text-green-700">
        {notice}
      </div>

      <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
        <nav aria-label="Folder path" className="flex min-w-0 flex-wrap items-center gap-1.5 text-sm">
          {path.length === 0 ? (
            <span aria-current="page" className="font-medium text-text-primary">
              {bucketName}
            </span>
          ) : (
            <button type="button" className="text-brand-600 hover:underline" onClick={() => void show([], view)}>
              {bucketName}
            </button>
          )}
          {path.map((f, i) => (
            <span key={f.id} className="flex items-center gap-1.5">
              <span aria-hidden="true" className="text-slate-300">
                /
              </span>
              {i === path.length - 1 ? (
                <span aria-current="page" className="font-medium text-text-primary">
                  {f.name}
                </span>
              ) : (
                <button
                  type="button"
                  className="text-brand-600 hover:underline"
                  onClick={() => void show(path.slice(0, i + 1), view)}
                >
                  {f.name}
                </button>
              )}
            </span>
          ))}
        </nav>
        <div role="group" aria-label="Show" className="inline-flex rounded-lg border border-border-subtle bg-white p-0.5">
          {(["files", "trash"] as const).map((v) => (
            <button
              key={v}
              type="button"
              aria-pressed={view === v}
              onClick={() => void show(path, v)}
              className={`rounded-md px-3 py-1 text-xs font-medium ${
                view === v ? "bg-surface-sunken text-text-primary" : "text-slate-600 hover:text-text-primary"
              }`}
            >
              {v === "files" ? "Files" : "Trash"}
            </button>
          ))}
        </div>
      </div>

      {!inTrash && (
        <div className="mb-3">
          <Input
            aria-label="Search files in this folder"
            placeholder="Search files…"
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              loadContents(current, "files", e.target.value || undefined).catch(() => {});
            }}
            className="max-w-xs"
          />
        </div>
      )}

      {inTrash && trashRefused ? (
        <EmptyState
          title="You can't see the Trash here"
          description="Seeing and restoring deleted files needs permission to delete files in this bucket."
        />
      ) : empty ? (
        inTrash ? (
          <EmptyState title="Trash is empty" description="Deleted files from this folder appear here." />
        ) : search ? (
          <EmptyState
            title="No matching files"
            description={`Nothing in this folder matches “${search}”.`}
            action={
              <Button variant="secondary" onClick={() => void show(path, "files")}>
                Clear search
              </Button>
            }
          />
        ) : (
          <EmptyState
            title={current ? "This folder is empty" : "No files yet"}
            description="Upload a file to get started."
            action={<Button onClick={() => fileInputRef.current?.click()}>Upload files</Button>}
          />
        )
      ) : (
        <Table>
          <THead>
            <Th>Name</Th>
            <Th>Size</Th>
            <Th>Type</Th>
            <Th>{inTrash ? "Deleted" : "Uploaded"}</Th>
            <Th>
              <span className="sr-only">Actions</span>
            </Th>
          </THead>
          <tbody>
            {folders.map((folder) => (
              <TRow key={folder.id} onClick={() => void show([...path, folder], "files")}>
                <Td className="font-medium text-slate-900">
                  <span className="flex items-center gap-2">
                    <FolderIcon aria-hidden="true" className="h-4 w-4 text-brand-600" />
                    {folder.name}
                  </span>
                </Td>
                <Td className="text-text-muted">—</Td>
                <Td className="text-slate-500">Folder</Td>
                <Td className="text-slate-500">{new Date(folder.created_at).toLocaleString()}</Td>
                <Td>
                  <span className="sr-only">Open folder</span>
                </Td>
              </TRow>
            ))}
            {files?.map((f) => (
              <TRow key={f.id}>
                <Td className="font-medium text-slate-900">
                  <span className="flex items-center gap-2">
                    <FileText aria-hidden="true" className="h-4 w-4 text-slate-400" />
                    {f.display_filename}
                  </span>
                </Td>
                <Td className="font-mono tabular-nums text-text-muted">{formatBytes(f.size)}</Td>
                <Td className="text-slate-500">{f.mime_type}</Td>
                <Td className="text-slate-500">
                  {new Date(inTrash ? f.updated_at : f.created_at).toLocaleString()}
                </Td>
                <Td>
                  <div className="flex justify-end gap-3 text-xs">
                    {inTrash ? (
                      <Button size="sm" variant="secondary" onClick={() => void handleRestore(f)}>
                        Restore
                      </Button>
                    ) : (
                      <>
                        <a href={`/api/v1/files/${f.id}/download/`} className="text-brand-600 hover:text-brand-700">
                          Download
                        </a>
                        <button onClick={() => setVersionsOf(f)} className="text-brand-600 hover:text-brand-700">
                          Versions
                        </button>
                        <button onClick={() => setSharing(f)} className="text-brand-600 hover:text-brand-700">
                          Share link
                        </button>
                        <button onClick={() => handleDelete(f)} className="text-red-600 hover:text-red-700">
                          Delete
                        </button>
                      </>
                    )}
                  </div>
                </Td>
              </TRow>
            ))}
          </tbody>
        </Table>
      )}

      {organizationId && (
        <div className="mt-8">
          <ShareSection organizationId={organizationId} resourceType="storage.bucket" resourceId={bucketId} />
        </div>
      )}

      <NewFolderModal
        open={folderModalOpen}
        bucketId={bucketId}
        parent={current}
        onClose={() => setFolderModalOpen(false)}
        onCreated={(folder) => {
          setFolderModalOpen(false);
          setFolders((prev) => [...prev, folder].sort((a, b) => a.name.localeCompare(b.name)));
        }}
      />

      {sharing && <ShareLinks file={sharing} onClose={() => setSharing(null)} />}

      {cleanupOpen && cleanup && (
        <CleanupSettings
          bucketId={bucketId}
          trashDays={cleanup.trash_days}
          versionDays={cleanup.version_days}
          onClose={() => setCleanupOpen(false)}
          onSaved={(b) => {
            setCleanup({ trash_days: b.trash_days, version_days: b.version_days });
            setCleanupOpen(false);
            setNotice("Cleanup settings saved.");
          }}
        />
      )}

      {versionsOf && (
        <FileVersions
          file={versionsOf}
          onClose={() => setVersionsOf(null)}
          onNewVersion={(updated) => {
            setVersionsOf(updated);
            setFiles((prev) => prev?.map((f) => (f.id === updated.id ? updated : f)) ?? null);
          }}
        />
      )}
    </div>
  );
}

function NewFolderModal({
  open,
  bucketId,
  parent,
  onClose,
  onCreated,
}: {
  open: boolean;
  bucketId: string;
  parent: Folder | null;
  onClose: () => void;
  onCreated: (folder: Folder) => void;
}) {
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await ensureCsrfCookie();
      const folder = await api.post<Folder>(`/buckets/${bucketId}/folders/`, {
        name: name.trim(),
        parent_id: parent?.id ?? null,
      });
      setName("");
      onCreated(folder);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "The folder could not be created.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal open={open} onClose={onClose} title={parent ? `New folder in ${parent.name}` : "New folder"}>
      <form onSubmit={submit} className="space-y-4">
        {error && <ErrorBanner message={error} />}
        <div>
          <Label htmlFor="new-folder-name">Name</Label>
          <Input id="new-folder-name" required maxLength={255} value={name} onChange={(e) => setName(e.target.value)} />
        </div>
        <div className="flex justify-end gap-2">
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" disabled={busy || !name.trim()}>
            Create
          </Button>
        </div>
      </form>
    </Modal>
  );
}
