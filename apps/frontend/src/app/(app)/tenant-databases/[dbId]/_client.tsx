"use client";

import { useEffect, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { LayoutGrid, Table as TableIcon } from "lucide-react";
import {
  api,
  ApiError,
  type Dashboard,
  type DBTable,
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
} from "@/components/ui";
import { ShareSection } from "@/components/ShareSection";

export default function TenantDatabaseClient({ dbId }: { dbId: string }) {
  const router = useRouter();
  const [db, setDb] = useState<TenantDatabase | null>(null);
  const [project, setProject] = useState<Project | null>(null);
  const [organizationId, setOrganizationId] = useState<string | null>(null);
  const [tables, setTables] = useState<DBTable[] | null>(null);
  const [dashboards, setDashboards] = useState<Dashboard[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [dashboardModalOpen, setDashboardModalOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);

  async function load() {
    try {
      const d = await api.get<TenantDatabase>(`/tenant-databases/${dbId}/`);
      setDb(d);
      const [p, t] = await Promise.all([
        api.get<Project>(`/projects/${d.project}/`),
        api.get<DBTable[]>(`/tenant-databases/${dbId}/tables/`),
      ]);
      setProject(p);
      setTables(t);
      // Best-effort, for the Sharing section's organization scope -- the
      // table list above doesn't depend on this resolving.
      api
        .get<Workspace>(`/workspaces/${p.workspace}/`)
        .then((ws) => setOrganizationId(ws.organization))
        .catch(() => {});
      api
        .get<Dashboard[]>(`/tenant-databases/${dbId}/dashboards/`)
        .then(setDashboards)
        .catch(() => setDashboards([]));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load database.");
    }
  }

  useEffect(() => {
    // One-shot fetch-on-mount/param-change, not a state-sync loop.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dbId]);

  async function handleDeleteDatabase() {
    if (!db) return;
    if (
      !confirm(
        `Permanently DROP the "${db.name}" database and all its tables? This cannot be undone.`,
      )
    )
      return;
    setDeleting(true);
    try {
      await api.del(`/tenant-databases/${dbId}/`);
      router.push(`/projects/${db.project}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to delete database.");
      setDeleting(false);
    }
  }

  if (!db && !error) return <PageLoading />;
  if (error && !db) return <ErrorBanner message={error} />;
  if (!db) return null;

  return (
    <div>
      <PageHeader
        title={db.name}
        breadcrumbs={[
          { label: "Organizations", href: "/orgs" },
          ...(project ? [{ label: project.name, href: `/projects/${project.id}` }] : []),
          { label: db.name },
        ]}
        description="A real, isolated PostgreSQL schema — each table below is a genuine table in it."
        actions={
          <>
            <Button variant="danger" size="sm" onClick={handleDeleteDatabase} disabled={deleting}>
              Drop database
            </Button>
            <Button onClick={() => setModalOpen(true)}>New table</Button>
          </>
        }
      />

      {error && (
        <div className="mb-4">
          <ErrorBanner message={error} />
        </div>
      )}

      {tables && tables.length === 0 ? (
        <EmptyState
          title="No tables yet"
          description="Create a table, add columns, then browse/edit its rows like a spreadsheet."
          action={<Button onClick={() => setModalOpen(true)}>New table</Button>}
        />
      ) : (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {tables?.map((t) => (
            <button key={t.id} onClick={() => router.push(`/tables/${t.id}`)} className="text-left">
              <Card className="transition-colors hover:border-indigo-400/40 hover:bg-slate-50">
                <div className="flex items-center gap-2">
                  <TableIcon className="h-4 w-4 text-indigo-600" />
                  <p className="font-medium text-slate-900">{t.name}</p>
                </div>
                <p className="mt-2 text-xs text-slate-500">{t.columns.length} column(s)</p>
                <div className="mt-2 flex flex-wrap gap-1">
                  {t.columns.slice(0, 4).map((c) => (
                    <Badge key={c.id}>{c.name}</Badge>
                  ))}
                  {t.columns.length > 4 && <Badge>+{t.columns.length - 4}</Badge>}
                </div>
              </Card>
            </button>
          ))}
        </div>
      )}

      {dashboards && (
        <div className="mt-8">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-slate-600">Dashboards</h2>
            <Button size="sm" variant="secondary" onClick={() => setDashboardModalOpen(true)}>
              New dashboard
            </Button>
          </div>
          {dashboards.length === 0 ? (
            <EmptyState
              title="No dashboards yet"
              description="A dashboard is a saved set of analytics widgets over this database's tables, re-run live every time it's viewed."
              action={
                <Button size="sm" onClick={() => setDashboardModalOpen(true)}>
                  New dashboard
                </Button>
              }
            />
          ) : (
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {dashboards.map((d) => (
                <button key={d.id} onClick={() => router.push(`/dashboards/${d.id}`)} className="text-left">
                  <Card className="transition-colors hover:border-indigo-400/40 hover:bg-slate-50">
                    <div className="flex items-center gap-2">
                      <LayoutGrid className="h-4 w-4 text-indigo-600" />
                      <p className="font-medium text-slate-900">{d.name}</p>
                    </div>
                    <p className="mt-2 text-xs text-slate-500">
                      {d.widgets.length} widget{d.widgets.length === 1 ? "" : "s"}
                    </p>
                  </Card>
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      {organizationId && (
        <div className="mt-8">
          <ShareSection
            organizationId={organizationId}
            resourceType="databases.tenant_database"
            resourceId={dbId}
          />
        </div>
      )}

      <CreateTableModal
        open={modalOpen}
        dbId={dbId}
        onClose={() => setModalOpen(false)}
        onCreated={(t) => {
          setTables((prev) => [...(prev ?? []), t]);
          setModalOpen(false);
        }}
      />
      <CreateDashboardModal
        open={dashboardModalOpen}
        dbId={dbId}
        onClose={() => setDashboardModalOpen(false)}
        onCreated={(d) => {
          setDashboards((prev) => [...(prev ?? []), d]);
          setDashboardModalOpen(false);
          router.push(`/dashboards/${d.id}`);
        }}
      />
    </div>
  );
}

function CreateTableModal({
  open,
  dbId,
  onClose,
  onCreated,
}: {
  open: boolean;
  dbId: string;
  onClose: () => void;
  onCreated: (t: DBTable) => void;
}) {
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const t = await api.post<DBTable>(`/tenant-databases/${dbId}/tables/`, { name });
      setName("");
      onCreated(t);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to create table.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Modal open={open} onClose={onClose} title="New table">
      <form onSubmit={handleSubmit} className="space-y-4">
        {error && <ErrorBanner message={error} />}
        <div>
          <Label htmlFor="table-name">Name</Label>
          <Input
            id="table-name"
            autoFocus
            required
            pattern="[a-z][a-z0-9_]*"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="contacts"
          />
          <p className="mt-1.5 text-xs text-slate-500">
            lowercase, starts with a letter — gets an <code>id</code> primary key automatically.
          </p>
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

function CreateDashboardModal({
  open,
  dbId,
  onClose,
  onCreated,
}: {
  open: boolean;
  dbId: string;
  onClose: () => void;
  onCreated: (d: Dashboard) => void;
}) {
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const d = await api.post<Dashboard>(`/tenant-databases/${dbId}/dashboards/`, {
        name,
        widgets: [],
      });
      setName("");
      onCreated(d);
    } catch (err) {
      setError(
        err instanceof ApiError && err.status === 403
          ? "You don't have permission to create dashboards in this database."
          : err instanceof ApiError
            ? err.message
            : "Failed to create dashboard.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Modal open={open} onClose={onClose} title="New dashboard">
      <form onSubmit={handleSubmit} className="space-y-4">
        {error && <ErrorBanner message={error} />}
        <div>
          <Label htmlFor="dashboard-name">Name</Label>
          <Input
            id="dashboard-name"
            autoFocus
            required
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Orders overview"
          />
          <p className="mt-1.5 text-xs text-slate-500">
            You&apos;ll add widgets after creating it.
          </p>
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
