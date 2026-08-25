import { api, type Bucket, type Project, type TenantDatabase, type Workspace } from "@/lib/api";

export type OrgResource = {
  kind: "bucket" | "database";
  id: string;
  name: string;
  projectName: string;
};

/** Every bucket and tenant database across an organization's projects,
 * via the bounded workspace -> project -> (buckets, tenant-databases)
 * fan-out -- there's no org-wide storage/database list endpoint (Unit
 * 4's Developer "Storage"/"Database" tabs are stubs for exactly this
 * reason). Bounded by however many workspaces/projects the org actually
 * has, same accepted pattern as /dashboard's per-org workspace count.
 * Shared between the Connect Application wizard's data-access step and
 * an application's real-permission summary, rather than duplicated. */
export async function listOrgResources(organizationId: string): Promise<OrgResource[]> {
  const workspaces = await api.get<Workspace[]>(`/organizations/${organizationId}/workspaces/`);
  const projectLists = await Promise.all(
    workspaces.map((ws) => api.get<Project[]>(`/workspaces/${ws.id}/projects/`).catch(() => [] as Project[])),
  );
  const projects = projectLists.flat();
  const perProject = await Promise.all(
    projects.map(async (p) => {
      const [buckets, dbs] = await Promise.all([
        api.get<Bucket[]>(`/projects/${p.id}/buckets/`).catch(() => [] as Bucket[]),
        api.get<TenantDatabase[]>(`/projects/${p.id}/tenant-databases/`).catch(() => [] as TenantDatabase[]),
      ]);
      const options: OrgResource[] = [
        ...buckets.map((b) => ({ kind: "bucket" as const, id: b.id, name: b.name, projectName: p.name })),
        ...dbs.map((d) => ({ kind: "database" as const, id: d.id, name: d.name, projectName: p.name })),
      ];
      return options;
    }),
  );
  return perProject.flat();
}
