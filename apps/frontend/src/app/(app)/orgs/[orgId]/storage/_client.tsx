"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { Archive, Files, HardDrive, History } from "lucide-react";
import { api, ApiError, type Organization } from "@/lib/api";
import { EmptyState, ErrorBanner, PageHeader, PageLoading, StatCard, Table, Td, Th, THead, TRow } from "@/components/ui";
import { formatBytes } from "../../../buckets/[bucketId]/format";

export type OrgBucket = {
  id: string;
  name: string;
  project: string;
  project_name: string;
  workspace_name: string;
  versioning_enabled: boolean;
  files: number;
  bytes: number;
  versions: number;
  version_bytes: number;
  trash_files: number;
  trash_bytes: number;
  created_at: string;
};

/** Every bucket in the organization the person may read, and what the organization's storage holds. */
export default function OrgStorageClient({ orgId }: { orgId: string }) {
  const org = useQuery({ queryKey: ["org", orgId], queryFn: () => api.get<Organization>(`/organizations/${orgId}/`) });
  const buckets = useQuery({
    queryKey: ["org", orgId, "buckets"],
    queryFn: () => api.get<OrgBucket[]>(`/organizations/${orgId}/buckets/`),
  });

  if (buckets.isLoading) return <PageLoading />;
  const list = buckets.data ?? [];
  const total = list.reduce(
    (a, b) => ({
      files: a.files + b.files,
      bytes: a.bytes + b.bytes,
      versionBytes: a.versionBytes + b.version_bytes,
      trashBytes: a.trashBytes + b.trash_bytes,
      trashFiles: a.trashFiles + b.trash_files,
    }),
    { files: 0, bytes: 0, versionBytes: 0, trashBytes: 0, trashFiles: 0 },
  );
  const orgName = org.data?.name ?? "Organization";

  return (
    <div>
      <PageHeader
        title="Storage"
        description="Every bucket you may open in this organization, and how much space its files take."
        breadcrumbs={[{ label: "Organizations", href: "/orgs" }, { label: orgName, href: `/orgs/${orgId}` }, { label: "Storage" }]}
      />
      {buckets.isError && (
        <div className="mb-4">
          <ErrorBanner
            message={buckets.error instanceof ApiError ? buckets.error.message : "The buckets could not be loaded."}
            error={buckets.error}
          />
        </div>
      )}
      <div className="mb-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard icon={HardDrive} label="In use" value={formatBytes(total.bytes + total.versionBytes + total.trashBytes)} accent="blue" detail="Files, kept versions and the Trash" />
        <StatCard icon={Files} label="Files" value={total.files.toLocaleString()} accent="green" detail={formatBytes(total.bytes)} />
        <StatCard icon={History} label="Kept earlier versions" value={formatBytes(total.versionBytes)} accent="teal" />
        <StatCard icon={Archive} label="In the Trash" value={formatBytes(total.trashBytes)} accent="amber" detail={`${total.trashFiles.toLocaleString()} files`} />
      </div>
      {list.length === 0 ? (
        <EmptyState
          title="No buckets you can open"
          description="Buckets are made inside a project. If you expected some here, ask an administrator for access."
        />
      ) : (
        <Table>
          <THead>
            <Th>Bucket</Th>
            <Th>Workspace / project</Th>
            <Th>Files</Th>
            <Th>Size</Th>
            <Th>Versions</Th>
            <Th>Trash</Th>
          </THead>
          <tbody>
            {list.map((b) => (
              <TRow key={b.id}>
                <Td>
                  <Link
                    href={`/buckets/${b.id}?name=${encodeURIComponent(b.name)}&project=${b.project}`}
                    className="font-medium text-brand-600 hover:underline"
                  >
                    {b.name}
                  </Link>
                  {b.versioning_enabled && <span className="ml-2 text-xs text-text-muted">keeps versions</span>}
                </Td>
                <Td className="text-text-muted">
                  {b.workspace_name} / {b.project_name}
                </Td>
                <Td className="text-right tabular-nums">{b.files.toLocaleString()}</Td>
                <Td className="text-right tabular-nums">{formatBytes(b.bytes)}</Td>
                <Td className="text-right tabular-nums">{b.versions ? formatBytes(b.version_bytes) : "-"}</Td>
                <Td className="text-right tabular-nums">{b.trash_files ? formatBytes(b.trash_bytes) : "-"}</Td>
              </TRow>
            ))}
          </tbody>
        </Table>
      )}
    </div>
  );
}
