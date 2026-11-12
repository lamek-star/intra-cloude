"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { api, ApiError, type Organization } from "@/lib/api";
import { EmptyState, ErrorBanner, PageHeader, PageLoading, Table, Td, Th, THead, TRow } from "@/components/ui";

export type OrgDatabase = {
  id: string;
  name: string;
  project: string;
  project_name: string;
  workspace_name: string;
  tables: number;
  created_at: string;
};

/** Every database in the organization the person may read, across its workspaces and projects. */
export default function OrgDatabasesClient({ orgId }: { orgId: string }) {
  const org = useQuery({ queryKey: ["org", orgId], queryFn: () => api.get<Organization>(`/organizations/${orgId}/`) });
  const dbs = useQuery({
    queryKey: ["org", orgId, "databases"],
    queryFn: () => api.get<OrgDatabase[]>(`/organizations/${orgId}/tenant-databases/`),
  });

  if (dbs.isLoading) return <PageLoading />;
  const list = dbs.data ?? [];
  const orgName = org.data?.name ?? "Organization";

  return (
    <div>
      <PageHeader
        title="Databases"
        description="Every database you may open in this organization."
        breadcrumbs={[{ label: "Organizations", href: "/orgs" }, { label: orgName, href: `/orgs/${orgId}` }, { label: "Databases" }]}
      />
      {dbs.isError && (
        <div className="mb-4">
          <ErrorBanner message={dbs.error instanceof ApiError ? dbs.error.message : "The databases could not be loaded."} error={dbs.error} />
        </div>
      )}
      {list.length === 0 ? (
        <EmptyState
          title="No databases you can open"
          description="Databases are made inside a project. If you expected some here, ask an administrator for access."
        />
      ) : (
        <Table>
          <THead>
            <Th>Database</Th>
            <Th>Workspace / project</Th>
            <Th>Tables</Th>
            <Th>Created</Th>
          </THead>
          <tbody>
            {list.map((d) => (
              <TRow key={d.id}>
                <Td>
                  <Link href={`/tenant-databases/${d.id}`} className="font-medium text-brand-600 hover:underline">
                    {d.name}
                  </Link>
                </Td>
                <Td className="text-text-muted">
                  {d.workspace_name} / {d.project_name}
                </Td>
                <Td className="text-right tabular-nums">{d.tables}</Td>
                <Td className="whitespace-nowrap text-text-muted">{new Date(d.created_at).toLocaleDateString()}</Td>
              </TRow>
            ))}
          </tbody>
        </Table>
      )}
    </div>
  );
}
