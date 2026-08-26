"use client";

import { useEffect, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { Database, Folder, Plug } from "lucide-react";
import {
  api,
  ApiError,
  type Bucket,
  type ConnectedDatabase,
  type Organization,
  type Project,
  type TenantDatabase,
  type Workspace,
} from "@/lib/api";
import {
  Badge,
  Button,
  Card,
  EmptyState,
  ErrorBanner,
  Input,
  Label,
  Modal,
  PageHeader,
  PageLoading,
  Select,
} from "@/components/ui";

const CONNECTED_DB_STATUS_TONE = {
  untested: "default",
  connected: "success",
  unreachable: "danger",
} as const;

export default function ProjectDetailClient({ projectId }: { projectId: string }) {
  const router = useRouter();
  const [project, setProject] = useState<Project | null>(null);
  const [workspace, setWorkspace] = useState<Workspace | null>(null);
  const [org, setOrg] = useState<Organization | null>(null);
  const [buckets, setBuckets] = useState<Bucket[] | null>(null);
  const [databases, setDatabases] = useState<TenantDatabase[] | null>(null);
  const [connectedDatabases, setConnectedDatabases] = useState<ConnectedDatabase[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [errorDetail, setErrorDetail] = useState<unknown>(null);
  const [bucketModalOpen, setBucketModalOpen] = useState(false);
  const [dbModalOpen, setDbModalOpen] = useState(false);
  const [connectedDbModalOpen, setConnectedDbModalOpen] = useState(false);

  async function load() {
    try {
      const p = await api.get<Project>(`/projects/${projectId}/`);
      setProject(p);
      const [ws, b, db, cdb] = await Promise.all([
        api.get<Workspace>(`/workspaces/${p.workspace}/`),
        api.get<Bucket[]>(`/projects/${projectId}/buckets/`),
        api.get<TenantDatabase[]>(`/projects/${projectId}/tenant-databases/`),
        api.get<ConnectedDatabase[]>(`/projects/${projectId}/connected-databases/`),
      ]);
      setWorkspace(ws);
      setBuckets(b);
      setDatabases(db);
      setConnectedDatabases(cdb);
      api.get<Organization>(`/organizations/${ws.organization}/`).then(setOrg).catch(() => {});
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load project.");
      setErrorDetail(err);
    }
  }

  useEffect(() => {
    // One-shot fetch-on-mount/param-change, not a state-sync loop.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]);

  if (!project && !error) return <PageLoading />;
  if (error && !project) return <ErrorBanner message={error} error={errorDetail} />;
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
          <h2 className="text-sm font-semibold text-slate-600">Storage buckets</h2>
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
                <Card className="transition-colors hover:border-indigo-400/40 hover:bg-slate-50">
                  <div className="flex items-center gap-2">
                    <Folder className="h-4 w-4 text-indigo-600" />
                    <p className="font-medium text-slate-900">{b.name}</p>
                  </div>
                </Card>
              </button>
            ))}
          </div>
        )}
      </div>

      <div>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-slate-600">Databases</h2>
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
                <Card className="transition-colors hover:border-indigo-400/40 hover:bg-slate-50">
                  <div className="flex items-center gap-2">
                    <Database className="h-4 w-4 text-indigo-600" />
                    <p className="font-medium text-slate-900">{db.name}</p>
                  </div>
                </Card>
              </button>
            ))}
          </div>
        )}
      </div>

      <div className="mt-8">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-slate-600">Connected databases</h2>
          <Button size="sm" onClick={() => setConnectedDbModalOpen(true)}>
            New connection
          </Button>
        </div>
        {connectedDatabases && connectedDatabases.length === 0 ? (
          <EmptyState
            title="No connected databases yet"
            description="Connect an existing external PostgreSQL database for read-only, proxied access -- nothing is copied in."
            action={
              <Button size="sm" onClick={() => setConnectedDbModalOpen(true)}>
                New connection
              </Button>
            }
          />
        ) : (
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {connectedDatabases?.map((cdb) => (
              <button
                key={cdb.id}
                onClick={() => router.push(`/connected-databases/${cdb.id}`)}
                className="text-left"
              >
                <Card className="transition-colors hover:border-indigo-400/40 hover:bg-slate-50">
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <Plug className="h-4 w-4 text-indigo-600" />
                      <p className="font-medium text-slate-900">{cdb.name}</p>
                    </div>
                    <Badge tone={CONNECTED_DB_STATUS_TONE[cdb.status]}>{cdb.status}</Badge>
                  </div>
                  <p className="mt-1.5 truncate text-xs text-slate-500">
                    {cdb.host}:{cdb.port}/{cdb.database_name}
                  </p>
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
      <CreateConnectedDatabaseModal
        open={connectedDbModalOpen}
        projectId={projectId}
        onClose={() => setConnectedDbModalOpen(false)}
        onCreated={(cdb) => {
          setConnectedDatabases((prev) => [...(prev ?? []), cdb]);
          setConnectedDbModalOpen(false);
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
  const [errorDetail, setErrorDetail] = useState<unknown>(null);
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
      setErrorDetail(err);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Modal open={open} onClose={onClose} title="New bucket">
      <form onSubmit={handleSubmit} className="space-y-4">
        {error && <ErrorBanner message={error} error={errorDetail} />}
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
  const [errorDetail, setErrorDetail] = useState<unknown>(null);
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
      setErrorDetail(err);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Modal open={open} onClose={onClose} title="New database">
      <form onSubmit={handleSubmit} className="space-y-4">
        {error && <ErrorBanner message={error} error={errorDetail} />}
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

function CreateConnectedDatabaseModal({
  open,
  projectId,
  onClose,
  onCreated,
}: {
  open: boolean;
  projectId: string;
  onClose: () => void;
  onCreated: (cdb: ConnectedDatabase) => void;
}) {
  const [name, setName] = useState("");
  const [host, setHost] = useState("");
  const [port, setPort] = useState("5432");
  const [databaseName, setDatabaseName] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [sslmode, setSslmode] = useState("require");
  const [error, setError] = useState<string | null>(null);
  const [errorDetail, setErrorDetail] = useState<unknown>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const cdb = await api.post<ConnectedDatabase>(`/projects/${projectId}/connected-databases/`, {
        name,
        host,
        port: Number(port),
        database_name: databaseName,
        username,
        password,
        sslmode,
      });
      setName("");
      setHost("");
      setPort("5432");
      setDatabaseName("");
      setUsername("");
      setPassword("");
      onCreated(cdb);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to connect to that database.");
      setErrorDetail(err);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Modal open={open} onClose={onClose} title="Connect a database">
      <form onSubmit={handleSubmit} className="space-y-4">
        {error && <ErrorBanner message={error} error={errorDetail} />}
        <div>
          <Label htmlFor="cdb-name">Name</Label>
          <Input
            id="cdb-name"
            autoFocus
            required
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Analytics warehouse"
          />
        </div>
        <div className="grid grid-cols-3 gap-3">
          <div className="col-span-2">
            <Label htmlFor="cdb-host">Host</Label>
            <Input
              id="cdb-host"
              required
              value={host}
              onChange={(e) => setHost(e.target.value)}
              placeholder="db.example.com"
            />
          </div>
          <div>
            <Label htmlFor="cdb-port">Port</Label>
            <Input
              id="cdb-port"
              type="number"
              required
              value={port}
              onChange={(e) => setPort(e.target.value)}
            />
          </div>
        </div>
        <div>
          <Label htmlFor="cdb-database">Database name</Label>
          <Input
            id="cdb-database"
            required
            value={databaseName}
            onChange={(e) => setDatabaseName(e.target.value)}
            placeholder="warehouse"
          />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <Label htmlFor="cdb-username">Username</Label>
            <Input
              id="cdb-username"
              required
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoComplete="off"
            />
          </div>
          <div>
            <Label htmlFor="cdb-password">Password</Label>
            <Input
              id="cdb-password"
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="new-password"
            />
          </div>
        </div>
        <div>
          <Label htmlFor="cdb-sslmode">SSL mode</Label>
          <Select id="cdb-sslmode" value={sslmode} onChange={(e) => setSslmode(e.target.value)}>
            <option value="disable">Disable</option>
            <option value="prefer">Prefer</option>
            <option value="require">Require</option>
            <option value="verify-full">Verify full</option>
          </Select>
        </div>
        <p className="text-xs text-slate-500">
          The password is encrypted at rest and never shown again after this form -- not even to you.
        </p>
        <div className="flex justify-end gap-2">
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" disabled={submitting}>
            {submitting ? "..." : "Connect"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
