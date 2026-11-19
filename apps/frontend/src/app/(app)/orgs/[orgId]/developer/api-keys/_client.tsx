"use client";

import Link from "next/link";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { AlertTriangle, KeyRound, ShieldOff } from "lucide-react";
import { api, ApiError, type Application, type ApplicationCredential, type Organization } from "@/lib/api";
import { Badge, EmptyState, ErrorBanner, PageHeader, PageLoading, StatCard, Table, Td, Th, THead, TRow } from "@/components/ui";
import { DeveloperNav } from "@/components/DeveloperNav";
import { useConfirm } from "@/components/ConfirmProvider";

/** A key nobody has used for this long is flagged: it is either forgotten or leaked-and-unused. */
const STALE_DAYS = 30;
const DAY_MS = 24 * 60 * 60 * 1000;

type Row = ApplicationCredential & { application: Application };
type Loaded = { rows: Row[]; hidden: string[] };

export function keyStatus(c: ApplicationCredential, now: number): { label: string; tone: "success" | "danger" | "warning" } {
  if (c.revoked_at) return { label: "Revoked", tone: "danger" };
  if (c.expires_at && Date.parse(c.expires_at) < now) return { label: "Expired", tone: "warning" };
  return { label: "Active", tone: "success" };
}

/** Active, but never used or not used for STALE_DAYS: worth a look. */
export function isStale(c: ApplicationCredential, now: number): boolean {
  if (keyStatus(c, now).label !== "Active") return false;
  const last = Date.parse(c.last_used_at ?? c.created_at);
  return now - last > STALE_DAYS * DAY_MS;
}

/** Every application's keys in one list. Uses each application's own credentials endpoint, so the same
 * permission check applies as on the application's page; an application whose keys the person may not see is
 * named, never guessed at. */
async function loadKeys(orgId: string): Promise<Loaded> {
  const apps = await api.get<Application[]>(`/organizations/${orgId}/applications/`);
  const results = await Promise.all(
    apps.map(async (application) => {
      try {
        const creds = await api.get<ApplicationCredential[]>(`/applications/${application.id}/credentials/`);
        return { application, creds };
      } catch (err) {
        if (err instanceof ApiError && (err.status === 403 || err.status === 404)) return { application, creds: null };
        throw err;
      }
    }),
  );
  const rows: Row[] = [];
  const hidden: string[] = [];
  for (const { application, creds } of results) {
    if (creds === null) hidden.push(application.name);
    else for (const c of creds) rows.push({ ...c, application });
  }
  rows.sort(
    (a, b) => Number(Boolean(a.revoked_at)) - Number(Boolean(b.revoked_at)) || b.created_at.localeCompare(a.created_at),
  );
  return { rows, hidden };
}

export default function ApiKeysClient({ orgId }: { orgId: string }) {
  const confirm = useConfirm();
  const queryClient = useQueryClient();
  const [actionError, setActionError] = useState<string | null>(null);
  const [showRevoked, setShowRevoked] = useState(false);
  const org = useQuery({ queryKey: ["org", orgId], queryFn: () => api.get<Organization>(`/organizations/${orgId}/`) });
  const keys = useQuery({ queryKey: ["org", orgId, "api-keys"], queryFn: () => loadKeys(orgId) });

  async function revoke(row: Row) {
    const ok = await confirm({
      title: `Revoke this key of "${row.application.name}"?`,
      description: "Anything using it stops working at once. This cannot be undone; issue a new key on the application's page.",
      confirmLabel: "Revoke",
      danger: true,
    });
    if (!ok) return;
    setActionError(null);
    try {
      await api.post(`/applications/${row.application.id}/credentials/${row.id}/revoke/`);
      await queryClient.invalidateQueries({ queryKey: ["org", orgId, "api-keys"] });
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : "The key could not be revoked.");
    }
  }

  if (keys.isLoading) return <PageLoading />;
  // "Now" = when the list was loaded (pure during render; refreshes with the data).
  const now = keys.dataUpdatedAt;
  const rows = keys.data?.rows ?? [];
  const active = rows.filter((r) => keyStatus(r, now).label === "Active");
  const stale = active.filter((r) => isStale(r, now));
  const shown = showRevoked ? rows : rows.filter((r) => keyStatus(r, now).label !== "Revoked");
  const orgName = org.data?.name ?? "Organization";

  return (
    <div>
      <PageHeader
        title="API Keys"
        description="Every application's keys in one place. Keys are issued and rotated on each application's page."
        breadcrumbs={[
          { label: "Organizations", href: "/orgs" },
          { label: orgName, href: `/orgs/${orgId}` },
          { label: "Developer", href: `/orgs/${orgId}/developer` },
          { label: "API Keys" },
        ]}
      />
      <DeveloperNav orgId={orgId} active="api-keys" />
      {(keys.isError || actionError) && (
        <div className="mb-4">
          <ErrorBanner
            message={actionError ?? (keys.error instanceof ApiError ? keys.error.message : "The keys could not be loaded.")}
            error={keys.error}
          />
        </div>
      )}
      <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-3">
        <StatCard icon={KeyRound} label="Active keys" value={active.length} accent="green" />
        <StatCard
          icon={AlertTriangle}
          label={`Unused for ${STALE_DAYS}+ days`}
          value={stale.length}
          accent="amber"
          detail={stale.length ? "Revoke the ones nothing needs" : undefined}
        />
        <StatCard icon={ShieldOff} label="Revoked or expired" value={rows.length - active.length} accent="blue" />
      </div>
      {keys.data && keys.data.hidden.length > 0 && (
        <p className="mb-3 text-sm text-slate-500">
          Not shown (you may not manage their keys): {keys.data.hidden.join(", ")}.
        </p>
      )}
      {rows.length === 0 ? (
        <EmptyState
          title="No keys yet"
          description="Open an application under Applications and press New credential to issue its first key."
        />
      ) : (
        <>
          <label className="mb-3 flex items-center gap-2 text-sm text-slate-600">
            <input type="checkbox" checked={showRevoked} onChange={(e) => setShowRevoked(e.target.checked)} />
            Show revoked keys
          </label>
          <Table>
            <THead>
              <Th>Application</Th>
              <Th>Key</Th>
              <Th>Status</Th>
              <Th>Created</Th>
              <Th>Last used</Th>
              <Th>Expires</Th>
              <Th>
                <span className="sr-only">Actions</span>
              </Th>
            </THead>
            <tbody>
              {shown.map((r) => {
                const status = keyStatus(r, now);
                return (
                  <TRow key={r.id}>
                    <Td>
                      <Link href={`/applications/${r.application.id}`} className="font-medium text-brand-600 hover:underline">
                        {r.application.name}
                      </Link>
                    </Td>
                    <Td className="font-mono text-xs text-text-muted">{r.id.slice(0, 8)}…</Td>
                    <Td>
                      <span className="inline-flex items-center gap-1.5">
                        <Badge tone={status.tone}>{status.label}</Badge>
                        {isStale(r, now) && <Badge tone="warning">Unused</Badge>}
                      </span>
                    </Td>
                    <Td className="text-slate-500">{new Date(r.created_at).toLocaleDateString()}</Td>
                    <Td className="text-slate-500">{r.last_used_at ? new Date(r.last_used_at).toLocaleString() : "Never"}</Td>
                    <Td className="text-slate-500">{r.expires_at ? new Date(r.expires_at).toLocaleDateString() : "Never"}</Td>
                    <Td>
                      {status.label === "Active" && (
                        <button onClick={() => revoke(r)} className="text-xs text-red-600 hover:text-red-500">
                          Revoke
                        </button>
                      )}
                    </Td>
                  </TRow>
                );
              })}
            </tbody>
          </Table>
        </>
      )}
    </div>
  );
}
