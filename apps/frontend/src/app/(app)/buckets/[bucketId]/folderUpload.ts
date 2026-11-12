// Uploading a whole folder from the computer: the browser gives each file its path inside the chosen folder
// ("Invoices/2026/march.pdf"); the same folders are made in the bucket (reusing ones that already exist) and each
// file goes into its own. A file that fails does not stop the others: the failures are reported at the end.

import { api, ApiError, type FileObject, type Folder } from "@/lib/api";

/** The folder path of a file, without its own name ([] for none), with empty or dot parts dropped. */
export function folderOf(relativePath: string): string[] {
  const parts = relativePath.split("/").filter((p) => p && p !== "." && p !== "..");
  return parts.slice(0, -1);
}

/** Every folder path needed, parents before children, each once. */
export function foldersToMake(paths: string[]): string[][] {
  const seen = new Set<string>();
  const out: string[][] = [];
  for (const p of paths) {
    const parts = folderOf(p);
    for (let i = 1; i <= parts.length; i++) {
      const key = parts.slice(0, i).join("/");
      if (!seen.has(key)) {
        seen.add(key);
        out.push(parts.slice(0, i));
      }
    }
  }
  return out.sort((a, b) => a.length - b.length);
}

export type FolderUploadResult = { uploaded: number; failed: { path: string; reason: string }[] };

/** Uploads `files` (from an <input webkitdirectory>) under `parent` (null = the top of the bucket). */
export async function uploadFolder(
  bucketId: string,
  parent: Folder | null,
  files: File[],
  onProgress: (done: number, total: number) => void,
): Promise<FolderUploadResult> {
  const pathOf = (f: File) => (f as File & { webkitRelativePath?: string }).webkitRelativePath || f.name;
  const ids = new Map<string, string | null>([["", parent?.id ?? null]]);
  const failed: FolderUploadResult["failed"] = [];
  let filesFailed = 0;

  async function childFolder(parentId: string | null, name: string): Promise<string> {
    const query = parentId ? `?parent=${parentId}` : "";
    const find = async () => (await api.get<Folder[]>(`/buckets/${bucketId}/folders/${query}`)).find((f) => f.name === name);
    const existing = await find();
    if (existing) return existing.id;
    try {
      return (await api.post<Folder>(`/buckets/${bucketId}/folders/`, { name, parent_id: parentId })).id;
    } catch (err) {
      // Made meanwhile (another upload, another person): use that one.
      if (err instanceof ApiError && err.status === 409) {
        const again = await find();
        if (again) return again.id;
      }
      throw err;
    }
  }

  for (const parts of foldersToMake(files.map(pathOf))) {
    const parentId = ids.get(parts.slice(0, -1).join("/"));
    if (parentId === undefined) continue; // its parent could not be made
    try {
      ids.set(parts.join("/"), await childFolder(parentId, parts[parts.length - 1]));
    } catch (err) {
      failed.push({ path: `${parts.join("/")}/`, reason: err instanceof ApiError ? err.message : "The folder could not be made." });
    }
  }

  let done = 0;
  onProgress(0, files.length);
  for (const file of files) {
    const path = pathOf(file);
    const folderId = ids.get(folderOf(path).join("/"));
    try {
      if (folderId === undefined) throw new Error("Its folder could not be made.");
      const form = new FormData();
      form.append("file", file);
      if (folderId) form.append("folder", folderId);
      await api.postForm<FileObject>(`/buckets/${bucketId}/files/`, form);
    } catch (err) {
      filesFailed += 1;
      failed.push({ path, reason: err instanceof Error ? err.message : "Upload failed." });
    }
    done += 1;
    onProgress(done, files.length);
  }
  return { uploaded: files.length - filesFailed, failed };
}
