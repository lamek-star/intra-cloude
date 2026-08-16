"use client";

import { useEffect, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import {
  api,
  ApiError,
  type Bucket,
  type Organization,
  type Project,
  type TenantDatabase,
  type Workspace,
} from "@/lib/api";
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

export default function ProjectDetailClient({ projectId }: { projectId: string }) {
  const router = useRouter();
  const [project, setProject] = useState<Project | null>(null);
  const [workspace, setWorkspace] = useState<Workspace | null>(null);
  const [org, setOrg] = useState<Organization | null>(null);
  const [buckets, setBuckets] = useState<Bucket[] | null>(null);
  const [databases, setDatabases] = useState<TenantDatabase[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [bucketModalOpen, setBucketModalOpen] = useState(false);
  const [dbModalOpen, setDbModalOpen] = useState(false);

  async function load() {
    try {
      const p = await api.get<Project>(`/projects/${projectId}/`);
      setProject(p);
      const [ws, b, db] = await Promise.all([
        api.get<Workspace>(`/workspaces/${p.workspace}/`),
        api.get<Bucket[]>(`/projects/${projectId}/buckets/`),
        api.get<TenantDatabase[]>(`/projects/${projectId}/tenant-databases/`),
      ]);
      setWorkspace(ws);
      setBuckets(b);
      setDatabases(db);
      api.get<Organization>(`/organizations/${ws.organization}/`).then(setOrg).catch(() => {});
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load project.");
    }
  }

  useEffect(() => {
    // One-shot fetch-on-mount/param-change, not a state-sync loop.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]);

  if (!project && !error) return <PageLoading />;
  if (error && !project) return <ErrorBanner message={error} />;
  if (!project) return null;

  return (
    <div>
      <PageHeader
        title={project.name}
        breadcrumbs={[
          { label: "Organizations", href: "/orgs" },
          ...(org && workspace
            ? [
                { label: org.name, href: `/orgs/${org.id}` },
                { label: workspace.name, href: `/orgs/${org.id}/workspaces/${workspace.id}` },
              ]
            : []),
          { label: project.name },
        ]}
      />

      <div className="mb-8">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-slate-300">Storage buckets</h2>
          <Button size="sm" onClick={() => setBucketModalOpen(true)}>
            New bucket
          </Button>
        </div>
        {buckets && buckets.length === 0 ? (
          <EmptyState
            title="No buckets yet"
            description="Buckets hold files and folders — like a Drive/S3 storage space."
            action={
              <Button size="sm" onClick={() => setBucketModalOpen(true)}>
                New bucket
              </Button>
            }
          />
        ) : (
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {buckets?.map((b) => (
              <button
                key={b.id}
                onClick={() =>
                  router.push(`/buckets/${b.id}?name=${encodeURIComponent(b.name)}&project=${b.project}`)
                }
                className="text-left"
              >
                <Card className="transition-colors hover:border-indigo-400/40 hover:bg-white/[0.05]">
                  <div className="flex items-center gap-2">
                    <span className="text-lg">🗂️</span>
                    <p className="font-medium text-white">{b.name}</p>
                  </div>
                </Card>
              </button>
            ))}
          </div>
        )}
      </div>

      <div>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-slate-300">Databases</h2>
          <Button size="sm" onClick={() => setDbModalOpen(true)}>
            New database
          </Button>
        </div>
        {databases && databases.length === 0 ? (
          <EmptyState
            title="No databases yet"
            description="Build a relational database with tables, columns, and a spreadsheet-style row editor."
            action={
              <Button size="sm" onClick={() => setDbModalOpen(true)}>
                New database
              </Button>
            }
          />
        ) : (
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {databases?.map((db) => (
              <button
                key={db.id}
                onClick={() => router.push(`/tenant-databases/${db.id}`)}
                className="text-left"
              >
                <Card className="transition-colors hover:border-indigo-400/40 hover:bg-white/[0.05]">
                  <div className="flex items-center gap-2">
                    <span className="text-lg">🗄️</span>
                    <p className="font-medium text-white">{db.name}</p>
                  </div>
                </Card>
              </button>
            ))}
          </div>
        )}
      </div>

      <CreateBucketModal
        open={bucketModalOpen}
        projectId={projectId}
        onClose={() => setBucketModalOpen(false)}
        onCreated={(b) => {
          setBuckets((prev) => [...(prev ?? []), b]);
          setBucketModalOpen(false);
        }}
      />
      <CreateDatabaseModal
        open={dbModalOpen}
        projectId={projectId}
        onClose={() => setDbModalOpen(false)}
        onCreated={(db) => {
          setDatabases((prev) => [...(prev ?? []), db]);
          setDbModalOpen(false);
        }}
      />
    </div>
  );
}

function CreateBucketModal({
  open,
  projectId,
  onClose,
  onCreated,
}: {
  open: boolean;
  projectId: string;
  onClose: () => void;
  onCreated: (b: Bucket) => void;
}) {
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const b = await api.post<Bucket>(`/projects/${projectId}/buckets/`, { name });
      setName("");
      onCreated(b);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to create bucket.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Modal open={open} onClose={onClose} title="New bucket">
      <form onSubmit={handleSubmit} className="space-y-4">
        {error && <ErrorBanner message={error} />}
        <div>
          <Label htmlFor="bucket-name">Name</Label>
          <Input
            id="bucket-name"
            autoFocus
            required
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="shared-docs"
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

function CreateDatabaseModal({
  open,
  projectId,
  onClose,
  onCreated,
}: {
  open: boolean;
  projectId: string;
  onClose: () => void;
  onCreated: (db: TenantDatabase) => void;
}) {
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const db = await api.post<TenantDatabase>(`/projects/${projectId}/tenant-databases/`, { name });
      setName("");
      onCreated(db);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to create database.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Modal open={open} onClose={onClose} title="New database">
      <form onSubmit={handleSubmit} className="space-y-4">
        {error && <ErrorBanner message={error} />}
        <div>
          <Label htmlFor="db-name">Name</Label>
          <Input
            id="db-name"
            autoFocus
            required
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="CRM"
          />
          <p className="mt-1.5 text-xs text-slate-500">Creates a real, isolated PostgreSQL schema.</p>
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
