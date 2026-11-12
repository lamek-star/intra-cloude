"use client";

import { useState, type FormEvent } from "react";
import { api, ApiError, ensureCsrfCookie } from "@/lib/api";
import { Button, ErrorBanner, Input, Label, Modal } from "@/components/ui";

/** The bucket's automatic cleanup (storage.manage): how long the Trash and earlier versions are kept. */
export function CleanupSettings({
  bucketId,
  trashDays,
  versionDays,
  onClose,
  onSaved,
}: {
  bucketId: string;
  trashDays: number;
  versionDays: number;
  onClose: () => void;
  onSaved: (b: { trash_days: number; version_days: number }) => void;
}) {
  const [trash, setTrash] = useState(String(trashDays));
  const [versions, setVersions] = useState(String(versionDays));
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function save(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await ensureCsrfCookie();
      onSaved(
        await api.patch<{ trash_days: number; version_days: number }>(`/buckets/${bucketId}/`, {
          trash_days: Number(trash),
          version_days: Number(versions),
        }),
      );
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "The settings were not saved.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal open onClose={onClose} title="Automatic cleanup">
      <form onSubmit={save} className="space-y-4">
        {error && <ErrorBanner message={error} />}
        <p className="text-sm text-slate-600">IntraForge tidies this bucket every night. 0 means never.</p>
        <div>
          <Label htmlFor="cleanup-trash">Delete files from the Trash after (days)</Label>
          <Input id="cleanup-trash" type="number" min={0} max={3650} required value={trash} onChange={(e) => setTrash(e.target.value)} />
        </div>
        <div>
          <Label htmlFor="cleanup-versions">Delete earlier versions older than (days)</Label>
          <Input id="cleanup-versions" type="number" min={0} max={3650} required value={versions} onChange={(e) => setVersions(e.target.value)} />
        </div>
        <div className="flex justify-end gap-2">
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" disabled={busy}>
            Save
          </Button>
        </div>
      </form>
    </Modal>
  );
}
