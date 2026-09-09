"use client";

import { useEffect, useState, type FormEvent } from "react";
import Link from "next/link";
import { Database, Folder, Layers, Plug } from "lucide-react";
import {
  api,
  ApiError,
  type AppInstance,
  type AppTemplate,
  type AppTemplateVersion,
  type Bucket,
  type ConnectedDatabase,
  type Organization,
  type Paginated,
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
  const [project, setProject] = useState<Project | null>(null);
  const [workspace, setWorkspace] = useState<Workspace | null>(null);
  const [org, setOrg] = useState<Organization | null>(null);
  const [buckets, setBuckets] = useState<Bucket[] | null>(null);
  const [databases, setDatabases] = useState<TenantDatabase[] | null>(null);
  const [connectedDatabases, setConnectedDatabases] = useState<ConnectedDatabase[] | null>(null);
  const [appInstances, setAppInstances] = useState<AppInstance[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [errorDetail, setErrorDetail] = useState<unknown>(null);
  const [bucketModalOpen, setBucketModalOpen] = useState(false);
  const [dbModalOpen, setDbModalOpen] = useState(false);
  const [connectedDbModalOpen, setConnectedDbModalOpen] = useState(false);
  const [installModalOpen, setInstallModalOpen] = useState(false);

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
      // Best-effort -- a member without app_instance.read simply sees an
      // empty section rather than a page-level error.
      api
        .get<Paginated<AppInstance>>(`/projects/${projectId}/app-instances/?limit=100`)
        .then((page) => setAppInstances(page.results))
        .catch(() => setAppInstances([]));
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
              <Link
                key={b.id}
                href={`/buckets/${b.id}?name=${encodeURIComponent(b.name)}&project=${b.project}`}
                className="block text-left"
              >
                <Card className="transition-colors hover:border-brand-400/40 hover:bg-slate-50">
                  <div className="flex items-center gap-2">
                    <Folder className="h-4 w-4 text-brand-600" />
                    <p className="font-medium text-slate-900">{b.name}</p>
                  </div>
                </Card>
              </Link>
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
              <Link
                key={db.id}
                href={`/tenant-databases/${db.id}`}
                className="block text-left"
              >
                <Card className="transition-colors hover:border-brand-400/40 hover:bg-slate-50">
                  <div className="flex items-center gap-2">
                    <Database className="h-4 w-4 text-brand-600" />
                    <p className="font-medium text-slate-900">{db.name}</p>
                  </div>
                </Card>
              </Link>
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
              <Link
                key={cdb.id}
                href={`/connected-databases/${cdb.id}`}
                className="block text-left"
              >
                <Card className="transition-colors hover:border-brand-400/40 hover:bg-slate-50">
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <Plug className="h-4 w-4 text-brand-600" />
                      <p className="font-medium text-slate-900">{cdb.name}</p>
                    </div>
                    <Badge tone={CONNECTED_DB_STATUS_TONE[cdb.status]}>{cdb.status}</Badge>
                  </div>
                  <p className="mt-1.5 truncate text-xs text-slate-500">
                    {cdb.host}:{cdb.port}/{cdb.database_name}
                  </p>
                </Card>
              </Link>
            ))}
          </div>
        )}
      </div>

      {appInstances && (
        <div className="mt-8">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-slate-600">Apps</h2>
            {org && (
              <Button size="sm" onClick={() => setInstallModalOpen(true)}>
                Install app
              </Button>
            )}
          </div>
          {appInstances.length === 0 ? (
            <EmptyState
              title="No apps installed yet"
              description="Install a published app template to get a real, provisioned data model with record screens."
              action={
                org && (
                  <Button size="sm" onClick={() => setInstallModalOpen(true)}>
                    Install app
                  </Button>
                )
              }
            />
          ) : (
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {appInstances.map((inst) => (
                <Link key={inst.id} href={`/app-instances/${inst.id}`} className="block text-left">
                  <Card className="transition-colors hover:border-brand-400/40 hover:bg-slate-50">
                    <div className="flex items-center gap-2">
                      <Layers className="h-4 w-4 text-brand-600" />
                      <p className="font-medium text-slate-900">{inst.label}</p>
                    </div>
                    {inst.archived && (
                      <div className="mt-1.5">
                        <Badge tone="warning">Archived</Badge>
                      </div>
                    )}
                  </Card>
                </Link>
              ))}
            </div>
          )}
        </div>
      )}

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
      {org && (
        <InstallAppModal
          open={installModalOpen}
          projectId={projectId}
          organizationId={org.id}
          onClose={() => setInstallModalOpen(false)}
          onInstalled={(inst) => {
            setAppInstances((prev) => [...(prev ?? []), inst]);
            setInstallModalOpen(false);
          }}
        />
      )}
    </div>
  );
}

function InstallAppModal({
  open,
  projectId,
  organizationId,
  onClose,
  onInstalled,
}: {
  open: boolean;
  projectId: string;
  organizationId: string;
  onClose: () => void;
  onInstalled: (inst: AppInstance) => void;
}) {
  const [templates, setTemplates] = useState<AppTemplate[] | null>(null);
  const [templateId, setTemplateId] = useState("");
  const [versions, setVersions] = useState<AppTemplateVersion[] | null>(null);
  const [versionId, setVersionId] = useState("");
  const [label, setLabel] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!open) return;
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setTemplates(null);
    setTemplateId("");
    setVersions(null);
    setVersionId("");
    setLabel("");
    setError(null);
    api
      .get<Paginated<AppTemplate>>(`/organizations/${organizationId}/app-templates/?limit=100`)
      .then((page) => setTemplates(page.results.filter((t) => !t.archived)))
      .catch(() => setTemplates([]));
  }, [open, organizationId]);

  useEffect(() => {
    if (!templateId) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setVersions(null);
      return;
    }
    api
      .get<Paginated<AppTemplateVersion>>(`/app-templates/${templateId}/versions/?limit=100`)
      .then((page) => {
        setVersions(page.results);
        setVersionId(page.results.at(-1)?.id ?? "");
      })
      .catch(() => setVersions([]));
  }, [templateId]);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!versionId || !label) return;
    setError(null);
    setSubmitting(true);
    try {
      const inst = await api.post<AppInstance>(`/projects/${projectId}/app-instances/`, {
        template_version: versionId,
        label,
      });
      onInstalled(inst);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to install this app.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Modal open={open} onClose={onClose} title="Install app">
      <form onSubmit={handleSubmit} className="space-y-4">
        {error && <ErrorBanner message={error} />}
        <div>
          <Label htmlFor="install-template">Template</Label>
          {templates === null ? (
            <p className="text-xs text-slate-500">Loading templates…</p>
          ) : templates.length === 0 ? (
            <p className="text-xs text-slate-500">
              No app templates in this organization yet -- create one first.
            </p>
          ) : (
            <Select id="install-template" value={templateId} onChange={(e) => setTemplateId(e.target.value)}>
              <option value="">Select a template…</option>
              {templates.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.label}
                </option>
              ))}
            </Select>
          )}
        </div>
        {templateId && (
          <div>
            <Label htmlFor="install-version">Version</Label>
            {versions === null ? (
              <p className="text-xs text-slate-500">Loading versions…</p>
            ) : versions.length === 0 ? (
              <p className="text-xs text-slate-500">This template has no published versions yet.</p>
            ) : (
              <Select id="install-version" value={versionId} onChange={(e) => setVersionId(e.target.value)}>
                {versions.map((v) => (
                  <option key={v.id} value={v.id}>
                    Version {v.number}
                  </option>
                ))}
              </Select>
            )}
          </div>
        )}
        {versionId && (
          <div>
            <Label htmlFor="install-label">Name this installed app</Label>
            <Input
              id="install-label"
              autoFocus
              required
              value={label}
              onChange={(e) => setLabel(e.target.value)}
              placeholder="Warehouse inventory"
            />
          </div>
        )}
        <div className="flex justify-end gap-2">
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" disabled={submitting || !versionId || !label}>
            {submitting ? "..." : "Install"}
          </Button>
        </div>
      </form>
    </Modal>
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
