"use client";

import Link from "next/link";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { api, ApiError, type Application, type Organization } from "@/lib/api";
import { Badge, Button, EmptyState, ErrorBanner, PageHeader, PageLoading, Select, Table, Td, Th, THead, TRow } from "@/components/ui";
import { DeveloperNav } from "@/components/DeveloperNav";

const PAGE = 50;
const METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE"];

export type LoggedRequest = {
  id: number;
  application: string;
  application_name: string;
  method: string;
  path: string;
  status: number;
  duration_ms: number;
  at: string;
  credential: string | null;
};
type Page = { count: number; next: string | null; results: LoggedRequest[] };

export function statusTone(code: number): "danger" | "warning" | "success" {
  return code >= 500 ? "danger" : code >= 400 ? "warning" : "success";
}

/** What a status means for an owner reading the log, not for a developer. */
export function statusHint(code: number): string {
  if (code === 401) return "No valid key";
  if (code === 403) return "Not permitted: check the application's permissions";
  if (code === 404) return "Not found";
  if (code === 429) return "Too many requests";
  if (code >= 500) return "Server error";
  if (code >= 400) return "Refused";
  return "";
}

export default function ApiLogsClient({ orgId }: { orgId: string }) {
  const [application, setApplication] = useState("");
  const [errorsOnly, setErrorsOnly] = useState(false);
  const [method, setMethod] = useState("");
  const [offset, setOffset] = useState(0);
  const org = useQuery({ queryKey: ["org", orgId], queryFn: () => api.get<Organization>(`/organizations/${orgId}/`) });
  const apps = useQuery({
    queryKey: ["org", orgId, "applications"],
    queryFn: () => api.get<Application[]>(`/organizations/${orgId}/applications/`),
  });
  const params = new URLSearchParams({ limit: String(PAGE), offset: String(offset) });
  if (application) params.set("application", application);
  if (errorsOnly) params.set("errors", "1");
  if (method) params.set("method", method);
  const page = useQuery({
    queryKey: ["org", orgId, "api-requests", params.toString()],
    queryFn: () => api.get<Page>(`/organizations/${orgId}/api-requests/?${params}`),
    placeholderData: keepPreviousData,
  });

  const filter = (set: () => void) => {
    set();
    setOffset(0);
  };

  if (page.isLoading) return <PageLoading />;
  const rows = page.data?.results ?? [];
  const orgName = org.data?.name ?? "Organization";
  const forbidden = page.error instanceof ApiError && page.error.status === 403;

  return (
    <div>
      <PageHeader
        title="API Logs"
        description="Every request an application made with its key: what it called, the answer and how long it took. Kept 30 days; never the data sent."
        breadcrumbs={[
          { label: "Organizations", href: "/orgs" },
          { label: orgName, href: `/orgs/${orgId}` },
          { label: "Developer", href: `/orgs/${orgId}/developer` },
          { label: "API Logs" },
        ]}
      />
      <DeveloperNav orgId={orgId} active="api-logs" />
      {page.isError && (
        <div className="mb-4">
          <ErrorBanner
            message={forbidden ? "You don't have permission to see applications' requests." : "The log could not be loaded."}
            error={page.error}
          />
        </div>
      )}
      <div className="mb-4 flex flex-wrap items-end gap-3">
        <label className="text-sm text-slate-600">
          Application
          <Select value={application} onChange={(e) => filter(() => setApplication(e.target.value))} className="mt-1">
            <option value="">All applications</option>
            {(apps.data ?? []).map((a) => (
              <option key={a.id} value={a.id}>
                {a.name}
              </option>
            ))}
          </Select>
        </label>
        <label className="text-sm text-slate-600">
          Method
          <Select value={method} onChange={(e) => filter(() => setMethod(e.target.value))} className="mt-1">
            <option value="">Any</option>
            {METHODS.map((m) => (
              <option key={m}>{m}</option>
            ))}
          </Select>
        </label>
        <label className="flex items-center gap-2 pb-2 text-sm text-slate-600">
          <input type="checkbox" checked={errorsOnly} onChange={(e) => filter(() => setErrorsOnly(e.target.checked))} />
          Only failed requests
        </label>
      </div>
      {!page.isError && rows.length === 0 ? (
        <EmptyState
          title={application || errorsOnly || method ? "No requests match" : "No requests yet"}
          description="Requests appear here as soon as an application calls IntraForge with one of its keys."
        />
      ) : (
        rows.length > 0 && (
          <>
            <Table>
              <THead>
                <Th>Time</Th>
                <Th>Application</Th>
                <Th>Request</Th>
                <Th>Answer</Th>
                <Th>Took</Th>
              </THead>
              <tbody>
                {rows.map((r) => (
                  <TRow key={r.id}>
                    <Td className="whitespace-nowrap text-text-muted">{new Date(r.at).toLocaleString()}</Td>
                    <Td>
                      <Link href={`/applications/${r.application}`} className="text-brand-600 hover:underline">
                        {r.application_name}
                      </Link>
                    </Td>
                    <Td className="break-all font-mono text-xs">
                      {r.method} {r.path}
                    </Td>
                    <Td>
                      <span className="inline-flex items-center gap-2">
                        <Badge tone={statusTone(r.status)}>{r.status}</Badge>
                        <span className="text-xs text-text-muted">{statusHint(r.status)}</span>
                      </span>
                    </Td>
                    <Td className="tabular-nums text-text-muted">{r.duration_ms} ms</Td>
                  </TRow>
                ))}
              </tbody>
            </Table>
            <div className="mt-2 flex items-center justify-end gap-2 text-xs text-slate-600">
              <span>
                {offset + 1}–{offset + rows.length} of {page.data?.count ?? 0}
              </span>
              <Button size="sm" variant="ghost" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - PAGE))}>
                Newer
              </Button>
              <Button size="sm" variant="ghost" disabled={!page.data?.next} onClick={() => setOffset(offset + PAGE)}>
                Older
              </Button>
            </div>
          </>
        )
      )}
    </div>
  );
}
