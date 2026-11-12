"use client";

import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { DatabaseBackup, ShieldAlert } from "lucide-react";
import { api, ApiError, ensureCsrfCookie } from "@/lib/api";
import { Badge, Button, Card, ErrorBanner, PageHeader, PageLoading, Table, Td, Th, THead, TRow } from "@/components/ui";
import { formatBytes } from "../buckets/[bucketId]/format";

type BackupRow = {
  id: string;
  type: string;
  type_label: string;
  status: "running" | "success" | "failed";
  file_name: string;
  size_bytes: number | null;
  error: string;
  started_at: string;
  completed_at: string | null;
  verified_restorable: boolean;
  verified_at: string | null;
  verification_error: string;
  restored_at: string | null;
};
type Backups = { latest: Record<string, { label: string; last_success: string | null; verified: boolean }>; backups: BackupRow[] };

const when = (iso: string | null) => (iso ? new Date(iso).toLocaleString() : "never");

/** This installation's backups (Super Administrator only): the last good backup of each kind, whether its restore
 * test passed, every attempt, and Back up now. Restoring replaces live data, so it is done in the Control Center
 * on the shop PC, not here. */
export default function BackupsPage() {
  const qc = useQueryClient();
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [actionError, setActionError] = useState<unknown>(null);
  const backups = useQuery({
    queryKey: ["system", "backups"],
    queryFn: () => api.get<Backups>("/system/backups/"),
    retry: false,
    refetchInterval: (q) => (q.state.data?.backups.some((b) => b.status === "running") ? 5000 : false),
  });

  async function backUpNow() {
    setBusy(true);
    setNotice(null);
    setActionError(null);
    try {
      await ensureCsrfCookie();
      const r = await api.post<{ started: string[]; already_running: string[] }>("/system/backups/run/", { type: "all" });
      setNotice(
        r.started.length
          ? `Backing up now (${r.started.length} ${r.started.length === 1 ? "kind" : "kinds"}). This page updates by itself.`
          : "A backup is already running.",
      );
      await qc.invalidateQueries({ queryKey: ["system", "backups"] });
    } catch (err) {
      setActionError(err);
    } finally {
      setBusy(false);
    }
  }

  if (backups.isLoading) return <PageLoading />;
  const forbidden = backups.error instanceof ApiError && backups.error.status === 403;

  return (
    <div className="max-w-5xl space-y-6">
      <PageHeader
        title="Backups"
        description="IntraForge backs itself up every night and tests that each backup can be restored."
        actions={
          backups.data && (
            <Button onClick={() => void backUpNow()} disabled={busy}>
              <DatabaseBackup aria-hidden="true" className="h-4 w-4" />
              {busy ? "Starting..." : "Back up now"}
            </Button>
          )
        }
      />
      {forbidden ? (
        <Card className="flex items-start gap-3">
          <ShieldAlert aria-hidden="true" className="mt-0.5 h-5 w-5 text-text-muted" />
          <p className="text-sm text-slate-600">Only the Super Administrator can see this installation&apos;s backups.</p>
        </Card>
      ) : (
        <>
          {backups.isError && <ErrorBanner message="The backups could not be loaded." error={backups.error} />}
          {actionError != null && (
            <ErrorBanner message={actionError instanceof ApiError ? actionError.message : "The backup did not start."} error={actionError} />
          )}
          {notice && (
            <p role="status" className="text-sm text-green-700">
              {notice}
            </p>
          )}
          {backups.data && (
            <>
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                {Object.entries(backups.data.latest).map(([type, l]) => (
                  <Card key={type}>
                    <p className="text-xs font-medium text-slate-500">{l.label}</p>
                    <p className="mt-1 text-sm font-semibold text-slate-900">{l.last_success ? when(l.last_success) : "No backup yet"}</p>
                    <div className="mt-2">
                      {l.last_success ? (
                        <Badge tone={l.verified ? "success" : "warning"}>{l.verified ? "Restore tested" : "Not yet tested"}</Badge>
                      ) : (
                        <Badge tone="danger">Missing</Badge>
                      )}
                    </div>
                  </Card>
                ))}
              </div>
              <Card>
                <p className="text-sm text-slate-600">
                  <strong>To restore</strong> a backup, use the <strong>IntraForge Control Center</strong> on the shop PC (Backup &amp;
                  Restore). Restoring replaces today&apos;s data with the backup&apos;s, so it is never done from a browser.
                </p>
              </Card>
              <Table>
                <THead>
                  <Th>Started</Th>
                  <Th>Kind</Th>
                  <Th>Result</Th>
                  <Th>Size</Th>
                  <Th>Restore test</Th>
                </THead>
                <tbody>
                  {backups.data.backups.map((b) => (
                    <TRow key={b.id}>
                      <Td className="whitespace-nowrap">{when(b.started_at)}</Td>
                      <Td>{b.type_label}</Td>
                      <Td>
                        <Badge tone={b.status === "success" ? "success" : b.status === "failed" ? "danger" : "info"}>
                          {b.status === "success" ? "Done" : b.status === "failed" ? "Failed" : "Running"}
                        </Badge>
                        {b.error && <p className="mt-1 max-w-xs truncate text-xs text-red-600" title={b.error}>{b.error}</p>}
                      </Td>
                      <Td className="tabular-nums">{b.size_bytes != null ? formatBytes(b.size_bytes) : "-"}</Td>
                      <Td className="text-sm">
                        {b.verified_restorable ? (
                          <span className="text-green-700">Passed {b.verified_at ? new Date(b.verified_at).toLocaleDateString() : ""}</span>
                        ) : b.verification_error ? (
                          <span className="text-red-600" title={b.verification_error}>
                            Failed
                          </span>
                        ) : (
                          <span className="text-text-muted">-</span>
                        )}
                      </Td>
                    </TRow>
                  ))}
                </tbody>
              </Table>
            </>
          )}
        </>
      )}
    </div>
  );
}
