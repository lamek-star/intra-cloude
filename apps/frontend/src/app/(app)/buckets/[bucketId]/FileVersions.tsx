"use client";

import { useEffect, useRef, useState } from "react";
import { api, ApiError, ensureCsrfCookie, type FileObject, type FileVersion } from "@/lib/api";
import { Button, ErrorBanner, Modal, Spinner, Table, Td, Th, THead, TRow } from "@/components/ui";
import { formatBytes } from "./format";

/** A file's kept earlier contents (buckets with versioning on), and uploading a new version. */
export function FileVersions({
  file,
  onClose,
  onNewVersion,
}: {
  file: FileObject;
  onClose: () => void;
  onNewVersion: (updated: FileObject) => void;
}) {
  const [versions, setVersions] = useState<FileVersion[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    let live = true;
    api
      .get<FileVersion[]>(`/files/${file.id}/versions/`)
      .then((v) => live && setVersions(v))
      .catch((err) => live && setError(err instanceof ApiError ? err.message : "Could not load the versions."));
    return () => {
      live = false;
    };
  }, [file.id]);

  async function upload(chosen: FileList | null) {
    const picked = chosen?.[0];
    if (!picked) return;
    setUploading(true);
    setError(null);
    try {
      await ensureCsrfCookie();
      const form = new FormData();
      form.append("file", picked);
      const updated = await api.postForm<FileObject>(`/files/${file.id}/versions/`, form);
      onNewVersion(updated);
      setVersions(await api.get<FileVersion[]>(`/files/${file.id}/versions/`));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Upload failed. The current version is unchanged.");
    } finally {
      setUploading(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  return (
    <Modal open onClose={onClose} title={`Versions of ${file.display_filename}`}>
      <div className="space-y-4">
        {error && <ErrorBanner message={error} />}
        <p className="text-sm text-slate-600">
          Current: {formatBytes(file.size)}, changed {new Date(file.updated_at).toLocaleString()}.
        </p>
        {versions === null && !error && (
          <div className="flex justify-center py-4 text-text-muted">
            <Spinner className="h-5 w-5" />
          </div>
        )}
        {versions?.length === 0 && (
          <p className="text-sm text-text-muted">
            No earlier versions are kept for this file. A bucket keeps them only when versioning is on.
          </p>
        )}
        {versions && versions.length > 0 && (
          <Table>
            <THead>
              <Th>Replaced</Th>
              <Th>Size</Th>
              <Th>By</Th>
            </THead>
            <tbody>
              {versions.map((v) => (
                <TRow key={v.id}>
                  <Td className="whitespace-nowrap">
                    <span title={`SHA-256 ${v.checksum_sha256}`}>{new Date(v.created_at).toLocaleString()}</span>
                  </Td>
                  <Td className="font-mono tabular-nums">{formatBytes(v.size)}</Td>
                  <Td className="text-text-muted">{v.created_by_email}</Td>
                </TRow>
              ))}
            </tbody>
          </Table>
        )}
        <div className="flex justify-end gap-2">
          <input ref={inputRef} type="file" className="hidden" onChange={(e) => void upload(e.target.files)} />
          <Button variant="secondary" onClick={() => inputRef.current?.click()} disabled={uploading}>
            {uploading ? <Spinner className="h-3.5 w-3.5" /> : null}
            Upload new version
          </Button>
          <Button variant="ghost" onClick={onClose}>
            Close
          </Button>
        </div>
      </div>
    </Modal>
  );
}
