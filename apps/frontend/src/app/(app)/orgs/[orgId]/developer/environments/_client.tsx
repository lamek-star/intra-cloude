"use client";

import { useEffect, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { Copy, Database, HardDrive, KeyRound, Trash2 } from "lucide-react";
import {
  api,
  ApiError,
  type Application,
  type Environment,
  type Organization,
} from "@/lib/api";
import {
  Badge,
  Button,
  EmptyState,
  ErrorBanner,
  Input,
  Label,
  Modal,
  PageHeader,
  PageLoading,
  Select,
  Table,
  Td,
  Th,
  THead,
  TRow,
} from "@/components/ui";
import { DeveloperNav } from "@/components/DeveloperNav";

type EnvironmentRow = Environment & { applicationName: string };

const TYPE_TONE: Record<string, "info" | "warning" | "danger" | "default"> = {
  development: "info",
  staging: "warning",
  production: "danger",
};

function statusBadge(status: Environment["status"], isProductionTier: boolean) {
  if (status === "disabled") return <Badge tone="default">Disabled</Badge>;
  return <Badge tone={isProductionTier ? "danger" : "success"}>Active</Badge>;
}

function connectionBadge(status: "connected" | "not_connected") {
  return status === "connected" ? (
    <Badge tone="success">Connected</Badge>
  ) : (
    <Badge tone="default">Not connected</Badge>
  );
}

export default function EnvironmentsClient({ orgId }: { orgId: string }) {
  const router = useRouter();
  const [org, setOrg] = useState<Organization | null>(null);
  const [applications, setApplications] = useState<Application[] | null>(null);
  const [environments, setEnvironments] = useState<EnvironmentRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [errorDetail, setErrorDetail] = useState<unknown>(null);
  const [createOpen, setCreateOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<EnvironmentRow | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  async function load() {
    try {
      const [o, apps] = await Promise.all([
        api.get<Organization>(`/organizations/${orgId}/`),
        api.get<Application[]>(`/organizations/${orgId}/applications/`),
      ]);
      setOrg(o);
      setApplications(apps);

      const perApp = await Promise.all(
        apps.map((app) =>
          api
            .get<Environment[]>(`/applications/${app.id}/environments/`)
            .then((envs) => envs.map((e): EnvironmentRow => ({ ...e, applicationName: app.name })))
            .catch(() => [] as EnvironmentRow[]),
        ),
      );
      setEnvironments(perApp.flat());
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load environments.");
      setErrorDetail(err);
    }
  }

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [orgId]);

  async function disableOrEnable(env: EnvironmentRow) {
    setActionError(null);
    try {
      const action = env.status === "active" ? "disable" : "enable";
      const updated = await api.post<Environment>(`/environments/${env.id}/${action}/`);
      setEnvironments((prev) =>
        prev?.map((e) => (e.id === env.id ? { ...updated, applicationName: env.applicationName } : e)) ?? prev,
      );
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : "Failed to update environment.");
    }
  }

  async function cloneEnvironment(env: EnvironmentRow) {
    setActionError(null);
    const name = window.prompt(`Name for the clone of "${env.name}"`, `${env.name} copy`);
    if (!name) return;
    try {
      const clone = await api.post<Environment>(`/environments/${env.id}/clone/`, { name });
      setEnvironments((prev) => [...(prev ?? []), { ...clone, applicationName: env.applicationName }]);
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : "Failed to clone environment.");
    }
  }

  if (!org && !error) return <PageLoading />;
  if (error && !org) return <ErrorBanner message={error} error={errorDetail} />;
  if (!org || !applications || !environments) return null;

  return (
    <div>
      <PageHeader
        title="Environments"
        breadcrumbs={[
          { label: "Organizations", href: "/orgs" },
          { label: org.name, href: `/orgs/${orgId}` },
          { label: "Developer", href: `/orgs/${orgId}/developer` },
          { label: "Environments" },
        ]}
        description="Isolated Development, Staging, and Production contexts for each application -- separate config, secrets, credentials, database, and storage."
        actions={
          applications.length > 0 && (
            <Button size="sm" onClick={() => setCreateOpen(true)}>
              Create environment
            </Button>
          )
        }
      />

      <DeveloperNav orgId={orgId} active="environments" />

      {actionError && (
        <div className="mb-4">
          <ErrorBanner message={actionError} />
        </div>
      )}

      {applications.length === 0 ? (
        <EmptyState
          title="No applications yet"
          description="Environments belong to an application -- register one first, then create its Development, Staging, and Production environments here."
          action={
            <Button size="sm" onClick={() => router.push(`/orgs/${orgId}/developer/applications`)}>
              Go to Applications
            </Button>
          }
        />
      ) : environments.length === 0 ? (
        <EmptyState
          title="No environments yet"
          description="Create Development, Staging, or Production environments for your applications -- each gets its own configuration, secrets, and credentials that can never reach another environment's resources."
          action={
            <Button size="sm" onClick={() => setCreateOpen(true)}>
              Create environment
            </Button>
          }
        />
      ) : (
        <Table>
          <THead>
            <Th>Name</Th>
            <Th>Application</Th>
            <Th>Type</Th>
            <Th>Status</Th>
            <Th>Database</Th>
            <Th>Storage</Th>
            <Th>API credentials</Th>
            <Th>Created</Th>
            <Th>Last activity</Th>
            <Th>
              <span className="sr-only">Actions</span>
            </Th>
          </THead>
          <tbody>
            {environments.map((env) => (
              <TRow key={env.id} onClick={() => router.push(`/environments/${env.id}`)}>
                <Td className="font-medium text-slate-900">{env.name}</Td>
                <Td className="text-slate-500">{env.applicationName}</Td>
                <Td>
                  <Badge tone={TYPE_TONE[env.environment_type] ?? "default"}>{env.environment_type}</Badge>
                </Td>
                <Td>{statusBadge(env.status, env.is_production_tier)}</Td>
                <Td>
                  <span className="inline-flex items-center gap-1">
                    <Database className="h-3 w-3 text-slate-400" />
                    {connectionBadge(env.database_status)}
                  </span>
                </Td>
                <Td>
                  <span className="inline-flex items-center gap-1">
                    <HardDrive className="h-3 w-3 text-slate-400" />
                    {connectionBadge(env.storage_status)}
                  </span>
                </Td>
                <Td className="text-slate-500">
                  <span className="inline-flex items-center gap-1">
                    <KeyRound className="h-3 w-3 text-slate-400" />
                    {env.credential_count}
                  </span>
                </Td>
                <Td className="text-slate-500">{new Date(env.created_at).toLocaleDateString()}</Td>
                <Td className="text-slate-500">
                  {env.last_activity_at ? new Date(env.last_activity_at).toLocaleDateString() : "Never"}
                </Td>
                <Td>
                  <div
                    className="flex justify-end gap-3 text-xs"
                    onClick={(e) => e.stopPropagation()}
                  >
                    <button
                      onClick={() => cloneEnvironment(env)}
                      className="inline-flex items-center gap-1 text-slate-500 hover:text-indigo-600"
                      title="Clone"
                    >
                      <Copy className="h-3.5 w-3.5" />
                    </button>
                    <button
                      onClick={() => disableOrEnable(env)}
                      className="text-slate-500 hover:text-slate-800"
                    >
                      {env.status === "active" ? "Disable" : "Enable"}
                    </button>
                    <button
                      onClick={() => setDeleteTarget(env)}
                      className="inline-flex items-center gap-1 text-slate-500 hover:text-red-600"
                      title="Delete"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>
                </Td>
              </TRow>
            ))}
          </tbody>
        </Table>
      )}

      <CreateEnvironmentModal
        open={createOpen}
        applications={applications}
        onClose={() => setCreateOpen(false)}
        onCreated={(env, applicationName) => {
          setEnvironments((prev) => [...(prev ?? []), { ...env, applicationName }]);
          setCreateOpen(false);
        }}
      />

      <DeleteEnvironmentModal
        environment={deleteTarget}
        onClose={() => setDeleteTarget(null)}
        onDeleted={(id) => {
          setEnvironments((prev) => prev?.filter((e) => e.id !== id) ?? prev);
          setDeleteTarget(null);
        }}
      />
    </div>
  );
}

const ENVIRONMENT_TYPES = ["development", "staging", "production", "custom"];

function CreateEnvironmentModal({
  open,
  applications,
  onClose,
  onCreated,
}: {
  open: boolean;
  applications: Application[];
  onClose: () => void;
  onCreated: (env: Environment, applicationName: string) => void;
}) {
  const [applicationId, setApplicationId] = useState(applications[0]?.id ?? "");
  const [name, setName] = useState("");
  const [environmentType, setEnvironmentType] = useState("development");
  const [error, setError] = useState<string | null>(null);
  const [errorDetail, setErrorDetail] = useState<unknown>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    if (open) setApplicationId(applications[0]?.id ?? "");
  }, [open, applications]);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const env = await api.post<Environment>(`/applications/${applicationId}/environments/`, {
        name,
        environment_type: environmentType,
      });
      const applicationName = applications.find((a) => a.id === applicationId)?.name ?? "";
      setName("");
      setEnvironmentType("development");
      onCreated(env, applicationName);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to create environment.");
      setErrorDetail(err);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Modal open={open} onClose={onClose} title="Create environment">
      <form onSubmit={handleSubmit} className="space-y-4">
        {error && <ErrorBanner message={error} error={errorDetail} />}
        <div>
          <Label htmlFor="env-application">Application</Label>
          <Select
            id="env-application"
            required
            value={applicationId}
            onChange={(e) => setApplicationId(e.target.value)}
          >
            {applications.map((app) => (
              <option key={app.id} value={app.id}>
                {app.name}
              </option>
            ))}
          </Select>
        </div>
        <div>
          <Label htmlFor="env-name">Name</Label>
          <Input
            id="env-name"
            autoFocus
            required
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Production"
          />
        </div>
        <div>
          <Label htmlFor="env-type">Type</Label>
          <Select id="env-type" value={environmentType} onChange={(e) => setEnvironmentType(e.target.value)}>
            {ENVIRONMENT_TYPES.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </Select>
          {environmentType === "production" && (
            <p className="mt-1.5 text-xs text-amber-700">
              Production environments get an extra permission gate -- only an organization administrator
              (or a role explicitly granted it) can manage or delete them.
            </p>
          )}
        </div>
        <div className="flex justify-end gap-2">
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" disabled={submitting || !applicationId}>
            {submitting ? "..." : "Create"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

function DeleteEnvironmentModal({
  environment,
  onClose,
  onDeleted,
}: {
  environment: EnvironmentRow | null;
  onClose: () => void;
  onDeleted: (id: string) => void;
}) {
  const [confirmName, setConfirmName] = useState("");
  const [confirmProduction, setConfirmProduction] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setConfirmName("");
    setConfirmProduction(false);
    setError(null);
  }, [environment]);

  if (!environment) return null;

  const nameMatches = confirmName === environment.name;
  const canSubmit = nameMatches && (!environment.is_production_tier || confirmProduction);

  async function handleDelete() {
    if (!canSubmit || !environment) return;
    setSubmitting(true);
    setError(null);
    try {
      await api.del(`/environments/${environment.id}/`, {
        confirm_name: confirmName,
        confirm_production_understanding: confirmProduction,
      });
      onDeleted(environment.id);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to delete environment.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Modal open={!!environment} onClose={onClose} title={`Delete "${environment.name}"?`}>
      <div className="space-y-4">
        <ErrorBanner
          message={
            environment.is_production_tier
              ? "This is a PRODUCTION environment. Deleting it removes its configuration, variables, webhooks, and credentials permanently. This cannot be undone."
              : "This removes the environment's configuration, variables, webhooks, and credentials permanently. This cannot be undone."
          }
        />
        {error && <ErrorBanner message={error} />}
        <div>
          <Label htmlFor="confirm-env-name">
            Type <span className="font-mono font-semibold">{environment.name}</span> to confirm
          </Label>
          <Input
            id="confirm-env-name"
            autoFocus
            value={confirmName}
            onChange={(e) => setConfirmName(e.target.value)}
          />
        </div>
        {environment.is_production_tier && (
          <label className="flex items-start gap-2 text-sm text-slate-700">
            <input
              type="checkbox"
              className="mt-0.5 h-4 w-4 rounded border-slate-300 text-red-600 focus:ring-red-500/30"
              checked={confirmProduction}
              onChange={(e) => setConfirmProduction(e.target.checked)}
            />
            I understand this is a production environment and I want to permanently delete it.
          </label>
        )}
        <div className="flex justify-end gap-2">
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button type="button" variant="danger" disabled={!canSubmit || submitting} onClick={handleDelete}>
            {submitting ? "..." : "Delete environment"}
          </Button>
        </div>
      </div>
    </Modal>
  );
}
