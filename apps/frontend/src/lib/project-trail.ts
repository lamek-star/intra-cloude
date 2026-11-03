import { useEffect, useState } from "react";
import { api, type Organization, type Project, type Workspace } from "@/lib/api";

export type Crumb = { label: string; href?: string };

/** The Organization / Workspace / Project breadcrumb segments above a project's resource (bucket,
 * tenant database, table), per DESIGN.md §7.2: every level is linked, none skipped. Each lookup is
 * best-effort -- a missing level (no permission on the workspace, a failed request) is left out
 * rather than blocking the page, the same way the pages already treated their project lookup. */
export function useProjectTrail(projectId: string | null | undefined): Crumb[] {
  const [trail, setTrail] = useState<Crumb[]>([]);

  useEffect(() => {
    if (!projectId) return;
    let cancelled = false;
    (async () => {
      const project = await api.get<Project>(`/projects/${projectId}/`).catch(() => null);
      if (!project) return;
      const projectCrumb: Crumb = { label: project.name, href: `/projects/${project.id}` };
      const workspace = await api.get<Workspace>(`/workspaces/${project.workspace}/`).catch(() => null);
      const org = workspace
        ? await api.get<Organization>(`/organizations/${workspace.organization}/`).catch(() => null)
        : null;
      if (cancelled) return;
      setTrail([
        ...(org ? [{ label: org.name, href: `/orgs/${org.id}` }] : []),
        ...(org && workspace ? [{ label: workspace.name, href: `/orgs/${org.id}/workspaces/${workspace.id}` }] : []),
        projectCrumb,
      ]);
    })();
    return () => {
      cancelled = true;
    };
  }, [projectId]);

  return trail;
}
