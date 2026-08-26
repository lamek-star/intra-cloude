"use client";

import { useEffect, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { api, ApiError, type Organization, type Project, type Workspace } from "@/lib/api";
import {
  Button,
  Card,
  EmptyState,
  ErrorBanner,
  Input,
  Label,
  Modal,
  PageHeader,
  PageLoading,
} from "@/components/ui";

export default function WorkspaceDetailClient({
  orgId,
  workspaceId,
}: {
  orgId: string;
  workspaceId: string;
}) {
  const router = useRouter();
  const [org, setOrg] = useState<Organization | null>(null);
  const [workspace, setWorkspace] = useState<Workspace | null>(null);
  const [projects, setProjects] = useState<Project[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [errorDetail, setErrorDetail] = useState<unknown>(null);
  const [modalOpen, setModalOpen] = useState(false);

  async function load() {
    try {
      const [o, ws, projs] = await Promise.all([
        api.get<Organization>(`/organizations/${orgId}/`),
        api.get<Workspace>(`/workspaces/${workspaceId}/`),
        api.get<Project[]>(`/workspaces/${workspaceId}/projects/`),
      ]);
      setOrg(o);
      setWorkspace(ws);
      setProjects(projs);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load workspace.");
      setErrorDetail(err);
    }
  }

  useEffect(() => {
    // One-shot fetch-on-mount/param-change, not a state-sync loop.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [workspaceId]);

  if (!workspace && !error) return <PageLoading />;
  if (error && !workspace) return <ErrorBanner message={error} error={errorDetail} />;
  if (!workspace) return null;

  return (
    <div>
      <PageHeader
        title={workspace.name}
        breadcrumbs={[
          { label: "Organizations", href: "/orgs" },
          { label: org?.name ?? "…", href: `/orgs/${orgId}` },
          { label: workspace.name },
        ]}
        description="Projects group storage buckets and databases together."
        actions={<Button onClick={() => setModalOpen(true)}>New project</Button>}
      />

      {projects && projects.length === 0 ? (
        <EmptyState
          title="No projects yet"
          description="Create a project to start adding storage buckets and databases."
          action={<Button onClick={() => setModalOpen(true)}>New project</Button>}
        />
      ) : (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {projects?.map((p) => (
            <button key={p.id} onClick={() => router.push(`/projects/${p.id}`)} className="text-left">
              <Card className="transition-colors hover:border-indigo-400/40 hover:bg-slate-50">
                <p className="font-medium text-slate-900">{p.name}</p>
                <p className="mt-1 text-xs text-slate-500">
                  Created {new Date(p.created_at).toLocaleDateString()}
                </p>
              </Card>
            </button>
          ))}
        </div>
      )}

      <CreateProjectModal
        open={modalOpen}
        workspaceId={workspaceId}
        onClose={() => setModalOpen(false)}
        onCreated={(p) => {
          setProjects((prev) => [...(prev ?? []), p]);
          setModalOpen(false);
        }}
      />
    </div>
  );
}

function CreateProjectModal({
  open,
  workspaceId,
  onClose,
  onCreated,
}: {
  open: boolean;
  workspaceId: string;
  onClose: () => void;
  onCreated: (p: Project) => void;
}) {
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [errorDetail, setErrorDetail] = useState<unknown>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const p = await api.post<Project>(`/workspaces/${workspaceId}/projects/`, { name });
      setName("");
      onCreated(p);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to create project.");
      setErrorDetail(err);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Modal open={open} onClose={onClose} title="New project">
      <form onSubmit={handleSubmit} className="space-y-4">
        {error && <ErrorBanner message={error} error={errorDetail} />}
        <div>
          <Label htmlFor="project-name">Name</Label>
          <Input
            id="project-name"
            autoFocus
            required
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Demo Project"
          />
        </div>
        <div className="flex justify-end gap-2">
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" disabled={submitting}>
            {submitting ? "..." : "Create"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
