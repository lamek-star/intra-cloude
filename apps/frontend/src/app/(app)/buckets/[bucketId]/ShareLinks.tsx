"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";
import { api, ApiError, ensureCsrfCookie, type FileObject } from "@/lib/api";
import { Badge, Button, CopyButton, ErrorBanner, Input, Label, Modal } from "@/components/ui";

type ShareLink = {
  id: string;
  expires_at: string;
  max_downloads: number | null;
  downloads: number;
  created_at: string;
  created_by_email: string | null;
  revoked_at: string | null;
};

function state(l: ShareLink): { label: string; tone: "success" | "default" | "danger" } {
  if (l.revoked_at) return { label: "Stopped", tone: "default" };
  if (new Date(l.expires_at) <= new Date()) return { label: "Expired", tone: "default" };
  if (l.max_downloads !== null && l.downloads >= l.max_downloads) return { label: "Used up", tone: "default" };
  return { label: "Works", tone: "success" };
}

/** Links that let anyone who has them download this one file, for 1 to 30 days (storage.share). */
export function ShareLinks({ file, onClose }: { file: FileObject; onClose: () => void }) {
  const [links, setLinks] = useState<ShareLink[] | null>(null);
  const [days, setDays] = useState("7");
  const [limit, setLimit] = useState("");
  const [made, setMade] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      setLinks(await api.get<ShareLink[]>(`/files/${file.id}/share-links/`));
    } catch (err) {
      setLinks([]);
      setError(err instanceof ApiError ? err.message : "The links could not be loaded.");
    }
  }, [file.id]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- one fetch when the dialog opens
    void load();
  }, [load]);

  async function make(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await ensureCsrfCookie();
      const r = await api.post<ShareLink & { path: string }>(`/files/${file.id}/share-links/`, {
        days: Number(days),
        max_downloads: limit ? Number(limit) : null,
      });
      setMade(`${window.location.origin}${r.path}`);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "The link was not made.");
    } finally {
      setBusy(false);
    }
  }

  async function stop(link: ShareLink) {
    setError(null);
    try {
      await ensureCsrfCookie();
      await api.post(`/share-links/${link.id}/revoke/`);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "The link was not stopped.");
    }
  }

  return (
    <Modal open onClose={onClose} title={`Share ${file.display_filename}`}>
      <div className="space-y-4">
        {error && <ErrorBanner message={error} />}
        <p className="text-sm text-slate-600">
          Anyone who has the link can download this file (only this file) until it expires. Links work on the shop network.
        </p>
        <form onSubmit={make} className="flex flex-wrap items-end gap-3">
          <div className="w-28">
            <Label htmlFor="share-days">Days (1-30)</Label>
            <Input id="share-days" type="number" min={1} max={30} required value={days} onChange={(e) => setDays(e.target.value)} />
          </div>
          <div className="w-40">
            <Label htmlFor="share-limit">Downloads (optional)</Label>
            <Input id="share-limit" type="number" min={1} placeholder="No limit" value={limit} onChange={(e) => setLimit(e.target.value)} />
          </div>
          <Button type="submit" disabled={busy}>
            Make a link
          </Button>
        </form>
        {made && (
          <div className="space-y-2 rounded-lg border border-green-300 bg-green-50 p-3">
            <p className="text-sm text-green-900">The link (shown only now):</p>
            <div className="flex items-center gap-2">
              <code className="min-w-0 flex-1 truncate rounded bg-white px-2 py-1 font-mono text-xs">{made}</code>
              <CopyButton value={made} label="Copy" />
            </div>
          </div>
        )}
        {links && links.length > 0 && (
          <ul className="divide-y divide-border-subtle text-sm">
            {links.map((l) => {
              const s = state(l);
              return (
                <li key={l.id} className="flex items-center gap-3 py-2">
                  <Badge tone={s.tone}>{s.label}</Badge>
                  <span className="min-w-0 flex-1 text-slate-600">
                    until {new Date(l.expires_at).toLocaleString()} · {l.downloads}
                    {l.max_downloads !== null ? ` of ${l.max_downloads}` : ""} downloads
                  </span>
                  {s.label === "Works" && (
                    <button type="button" onClick={() => void stop(l)} className="text-xs text-red-600 hover:underline">
                      Stop
                    </button>
                  )}
                </li>
              );
            })}
          </ul>
        )}
        <div className="flex justify-end">
          <Button variant="ghost" onClick={onClose}>
            Close
          </Button>
        </div>
      </div>
    </Modal>
  );
}
