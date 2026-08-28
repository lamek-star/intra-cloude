"use client";

import { useEffect, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import {
  Activity,
  AppWindow,
  Database,
  HardDrive,
  KeyRound,
  Layers3,
  RotateCw,
  ScrollText,
  Settings as SettingsIcon,
  ShieldCheck,
  ShieldOff,
  SlidersHorizontal,
  Trash2,
  Webhook as WebhookIcon,
} from "lucide-react";
import {
  api,
  ApiError,
  type Application,
  type ApplicationCredential,
  type AuditEvent,
  type Environment,
  type EnvironmentSecret,
  type EnvironmentVariable,
  type EnvironmentWebhook,
  type Organization,
  type Paginated,
} from "@/lib/api";
import { listOrgResources, type OrgResource } from "@/lib/org-resources";
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
  SecretReveal,
  Select,
  Spinner,
  Table,
  Td,
  Th,
  THead,
  TRow,
} from "@/components/ui";

type TabKey =
  | "overview"
  | "configuration"
  | "secrets"
  | "api-keys"
  | "database"
  | "storage"
  | "auth"
  | "webhooks"
  | "logs"
  | "activity"
  | "settings";

const TABS: { key: TabKey; label: string; icon: React.ComponentType<{ className?: string }> }[] = [
  { key: "overview", label: "Overview", icon: Layers3 },
  { key: "configuration", label: "Configuration", icon: SlidersHorizontal },
  { key: "secrets", label: "Secrets", icon: KeyRound },
  { key: "api-keys", label: "API Keys", icon: AppWindow },
  { key: "database", label: "Database", icon: Database },
  { key: "storage", label: "Storage", icon: HardDrive },
  { key: "auth", label: "Auth", icon: ShieldCheck },
  { key: "webhooks", label: "Webhooks", icon: WebhookIcon },
  { key: "logs", label: "Logs", icon: ScrollText },
  { key: "activity", label: "Activity", icon: Activity },
  { key: "settings", label: "Settings", icon: SettingsIcon },
];

export default function EnvironmentDetailClient({ environmentId }: { environmentId: string }) {
  const router = useRouter();
  const [environment, setEnvironment] = useState<Environment | null>(null);
  const [application, setApplication] = useState<Application | null>(null);
  const [org, setOrg] = useState<Organization | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [errorDetail, setErrorDetail] = useState<unknown>(null);
  const [tab, setTab] = useState<TabKey>("overview");

  async function load() {
    try {
      const env = await api.get<Environment>(`/environments/${environmentId}/`);
      setEnvironment(env);
      const app = await api.get<Application>(`/applications/${env.application}/`);
      setApplication(app);
      api.get<Organization>(`/organizations/${app.organization}/`).then(setOrg).catch(() => {});
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load environment.");
      setErrorDetail(err);
    }
  }

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [environmentId]);

  if (!environment && !error) return <PageLoading />;
  if (error && !environment) return <ErrorBanner message={error} error={errorDetail} />;
  if (!environment) return null;

  return (
    <div>
      <PageHeader
        title={environment.name}
        breadcrumbs={[
          { label: "Organizations", href: "/orgs" },
          ...(org
            ? [
                { label: org.name, href: `/orgs/${org.id}` },
                { label: "Developer", href: `/orgs/${org.id}/developer` },
                { label: "Environments", href: `/orgs/${org.id}/developer/environments` },
              ]
            : []),
          { label: environment.name },
        ]}
        description={application ? `${application.name} · ${environment.environment_type}` : undefined}
        actions={
          <div className="flex items-center gap-2">
            {environment.is_production_tier && <Badge tone="danger">Production</Badge>}
            <Badge tone={environment.status === "active" ? "success" : "default"}>
              {environment.status === "active" ? "Active" : "Disabled"}
            </Badge>
          </div>
        }
      />

      <nav aria-label="Environment sections" className="mb-6 flex flex-wrap gap-1 border-b border-slate-200 pb-2">
        {TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            aria-current={tab === t.key ? "page" : undefined}
            className={`flex shrink-0 items-center gap-1.5 rounded-md px-2.5 py-1.5 text-sm font-medium transition-colors ${
              tab === t.key
                ? "bg-indigo-50 text-indigo-600"
                : "text-slate-500 hover:bg-slate-100 hover:text-slate-800"
            }`}
          >
            <t.icon className="h-3.5 w-3.5" />
            {t.label}
          </button>
        ))}
      </nav>

      {tab === "overview" && <OverviewTab environment={environment} application={application} />}
      {tab === "configuration" && (
        <ConfigurationTab environment={environment} onUpdated={setEnvironment} />
      )}
      {tab === "secrets" && <SecretsTab environmentId={environmentId} />}
      {tab === "api-keys" && <ApiKeysTab environmentId={environmentId} />}
      {tab === "database" && organizationReady(org) && (
        <DatabaseTab environment={environment} organizationId={org!.id} onUpdated={setEnvironment} />
      )}
      {tab === "storage" && organizationReady(org) && (
        <StorageTab environment={environment} organizationId={org!.id} onUpdated={setEnvironment} />
      )}
      {tab === "auth" && <AuthTab environment={environment} onUpdated={setEnvironment} />}
      {tab === "webhooks" && <WebhooksTab environmentId={environmentId} />}
      {tab === "logs" && organizationReady(org) && (
        <LogsTab environmentId={environmentId} organizationId={org!.id} />
      )}
      {tab === "activity" && organizationReady(org) && (
        <ActivityTab environmentId={environmentId} organizationId={org!.id} />
      )}
      {tab === "settings" && (
        <SettingsTab
          environment={environment}
          onUpdated={setEnvironment}
          onDeleted={() => {
            if (org) router.push(`/orgs/${org.id}/developer/environments`);
          }}
        />
      )}
    </div>
  );
}

function organizationReady(org: Organization | null): org is Organization {
  return org !== null;
}

// --- Overview -----------------------------------------------------------

function OverviewTab({
  environment,
  application,
}: {
  environment: Environment;
  application: Application | null;
}) {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <Card>
          <p className="text-xs font-medium text-slate-500">Application</p>
          <p className="mt-1 text-sm font-semibold text-slate-900">{application?.name ?? "—"}</p>
        </Card>
        <Card>
          <p className="text-xs font-medium text-slate-500">Database</p>
          <p className="mt-1 text-sm font-semibold text-slate-900">
            {environment.database_status === "connected" ? "Connected" : "Not connected"}
          </p>
        </Card>
        <Card>
          <p className="text-xs font-medium text-slate-500">Storage</p>
          <p className="mt-1 text-sm font-semibold text-slate-900">
            {environment.storage_status === "connected" ? "Connected" : "Not connected"}
          </p>
        </Card>
      </div>
      <Card>
        <h3 className="mb-3 text-sm font-semibold text-slate-700">Details</h3>
        <dl className="grid grid-cols-1 gap-3 text-sm sm:grid-cols-2">
          <div>
            <dt className="text-slate-500">Type</dt>
            <dd className="text-slate-900">{environment.environment_type}</dd>
          </div>
          <div>
            <dt className="text-slate-500">Slug</dt>
            <dd className="font-mono text-slate-900">{environment.slug}</dd>
          </div>
          <div>
            <dt className="text-slate-500">API credentials issued</dt>
            <dd className="text-slate-900">{environment.credential_count}</dd>
          </div>
          <div>
            <dt className="text-slate-500">Created</dt>
            <dd className="text-slate-900">{new Date(environment.created_at).toLocaleString()}</dd>
          </div>
          <div>
            <dt className="text-slate-500">Last activity</dt>
            <dd className="text-slate-900">
              {environment.last_activity_at
                ? new Date(environment.last_activity_at).toLocaleString()
                : "Never"}
            </dd>
          </div>
        </dl>
      </Card>
    </div>
  );
}

// --- Configuration (non-secret variables + raw config) -----------------

function ConfigurationTab({
  environment,
  onUpdated,
}: {
  environment: Environment;
  onUpdated: (env: Environment) => void;
}) {
  const [variables, setVariables] = useState<EnvironmentVariable[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [key, setKey] = useState("");
  const [value, setValue] = useState("");

  useEffect(() => {
    api
      .get<EnvironmentVariable[]>(`/environments/${environment.id}/variables/`)
      .then(setVariables)
      .catch(() => setVariables([]));
  }, [environment.id]);

  async function addVariable(e: FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      const variable = await api.post<EnvironmentVariable>(`/environments/${environment.id}/variables/`, {
        key,
        value,
      });
      setVariables((prev) => [...(prev ?? []).filter((v) => v.key !== variable.key), variable]);
      setKey("");
      setValue("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to save variable.");
    }
  }

  async function removeVariable(variable: EnvironmentVariable) {
    setError(null);
    try {
      await api.del(`/environments/${environment.id}/variables/${variable.id}/`);
      setVariables((prev) => prev?.filter((v) => v.id !== variable.id) ?? prev);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to remove variable.");
    }
  }

  return (
    <div className="space-y-6">
      <Card>
        <h3 className="mb-3 text-sm font-semibold text-slate-700">Environment variables</h3>
        <p className="mb-3 text-xs text-slate-500">
          Plain, non-secret configuration values. For anything sensitive, use the Secrets tab instead.
        </p>
        {error && (
          <div className="mb-3">
            <ErrorBanner message={error} />
          </div>
        )}
        {variables === null ? (
          <Spinner className="h-4 w-4 text-slate-400" />
        ) : variables.length === 0 ? (
          <p className="mb-3 text-sm text-slate-500">No variables yet.</p>
        ) : (
          <Table>
            <THead>
              <Th>Key</Th>
              <Th>Value</Th>
              <Th>
                <span className="sr-only">Actions</span>
              </Th>
            </THead>
            <tbody>
              {variables.map((v) => (
                <TRow key={v.id}>
                  <Td className="font-mono text-xs text-slate-900">{v.key}</Td>
                  <Td className="font-mono text-xs text-slate-600">{v.value}</Td>
                  <Td>
                    <button
                      onClick={() => removeVariable(v)}
                      className="text-xs text-slate-500 hover:text-red-600"
                    >
                      Remove
                    </button>
                  </Td>
                </TRow>
              ))}
            </tbody>
          </Table>
        )}
        <form onSubmit={addVariable} className="mt-4 flex items-end gap-2">
          <div className="flex-1">
            <Label htmlFor="var-key">Key</Label>
            <Input
              id="var-key"
              required
              value={key}
              onChange={(e) => setKey(e.target.value)}
              placeholder="LOG_LEVEL"
            />
          </div>
          <div className="flex-1">
            <Label htmlFor="var-value">Value</Label>
            <Input id="var-value" value={value} onChange={(e) => setValue(e.target.value)} placeholder="debug" />
          </div>
          <Button type="submit" size="sm">
            Save
          </Button>
        </form>
      </Card>

      <ServiceEndpointCard environment={environment} onUpdated={onUpdated} />
    </div>
  );
}

/** A focused editor for `config.service_endpoint` -- the one structured,
 * non-secret setting most integrations actually need (where this
 * environment's application should call back to). The rest of `config`
 * is free-form JSON the backend already accepts; this deliberately
 * doesn't expose a raw JSON textarea (an easy way to submit invalid
 * JSON with no helpful error), matching the "useful operational
 * information" bar for this tab. */
function ServiceEndpointCard({
  environment,
  onUpdated,
}: {
  environment: Environment;
  onUpdated: (env: Environment) => void;
}) {
  const [endpoint, setEndpoint] = useState(
    typeof environment.config.service_endpoint === "string" ? environment.config.service_endpoint : "",
  );
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  async function save(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSaving(true);
    setSaved(false);
    try {
      const updated = await api.patch<Environment>(`/environments/${environment.id}/`, {
        config: { ...environment.config, service_endpoint: endpoint },
      });
      onUpdated(updated);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to save.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Card>
      <h3 className="mb-3 text-sm font-semibold text-slate-700">Service endpoint</h3>
      {error && (
        <div className="mb-3">
          <ErrorBanner message={error} />
        </div>
      )}
      <form onSubmit={save} className="flex items-end gap-2">
        <div className="flex-1">
          <Label htmlFor="service-endpoint">Base URL this environment&apos;s application should call</Label>
          <Input
            id="service-endpoint"
            value={endpoint}
            onChange={(e) => setEndpoint(e.target.value)}
            placeholder="https://staging.example.com"
          />
        </div>
        <Button type="submit" size="sm" disabled={saving}>
          {saving ? "..." : saved ? "Saved" : "Save"}
        </Button>
      </form>
    </Card>
  );
}

// --- Secrets --------------------------------------------------------------

function SecretsTab({ environmentId }: { environmentId: string }) {
  const [secrets, setSecrets] = useState<EnvironmentSecret[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [reveal, setReveal] = useState<{ title: string; secret: string } | null>(null);
  const [createOpen, setCreateOpen] = useState(false);

  useEffect(() => {
    api
      .get<EnvironmentSecret[]>(`/environments/${environmentId}/secrets/`)
      .then(setSecrets)
      .catch((err) =>
        setError(
          err instanceof ApiError && err.status === 403
            ? "You don't have permission to manage this environment's secrets."
            : "Failed to load secrets.",
        ),
      );
  }, [environmentId]);

  async function rotate(secret: EnvironmentSecret) {
    const value = window.prompt(`New value for "${secret.key}"`);
    if (!value) return;
    try {
      const rotated = await api.post<EnvironmentSecret>(
        `/environments/${environmentId}/secrets/${secret.id}/rotate/`,
        { value },
      );
      setSecrets((prev) => prev?.map((s) => (s.id === secret.id ? { ...rotated, value: undefined } : s)) ?? prev);
      setReveal({ title: `Rotated "${secret.key}"`, secret: rotated.value! });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to rotate secret.");
    }
  }

  async function remove(secret: EnvironmentSecret) {
    try {
      await api.del(`/environments/${environmentId}/secrets/${secret.id}/`);
      setSecrets((prev) => prev?.filter((s) => s.id !== secret.id) ?? prev);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to delete secret.");
    }
  }

  return (
    <Card>
      <div className="mb-3 flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold text-slate-700">Secrets</h3>
          <p className="text-xs text-slate-500">
            Values are encrypted at rest and shown only once, right after creation or rotation.
          </p>
        </div>
        <Button size="sm" onClick={() => setCreateOpen(true)}>
          New secret
        </Button>
      </div>
      {error && (
        <div className="mb-3">
          <ErrorBanner message={error} />
        </div>
      )}
      {reveal && (
        <div className="mb-3">
          <SecretReveal label={reveal.title} secret={reveal.secret} />
        </div>
      )}
      {secrets === null ? (
        <Spinner className="h-4 w-4 text-slate-400" />
      ) : secrets.length === 0 ? (
        <EmptyState title="No secrets yet" description="Create one for an API key, password, or token." />
      ) : (
        <Table>
          <THead>
            <Th>Key</Th>
            <Th>Created</Th>
            <Th>Rotated</Th>
            <Th>
              <span className="sr-only">Actions</span>
            </Th>
          </THead>
          <tbody>
            {secrets.map((s) => (
              <TRow key={s.id}>
                <Td className="font-mono text-xs text-slate-900">{s.key}</Td>
                <Td className="text-slate-500">{new Date(s.created_at).toLocaleDateString()}</Td>
                <Td className="text-slate-500">
                  {s.rotated_at ? new Date(s.rotated_at).toLocaleDateString() : "Never"}
                </Td>
                <Td>
                  <div className="flex justify-end gap-3 text-xs">
                    <button onClick={() => rotate(s)} className="inline-flex items-center gap-1 text-indigo-600 hover:text-indigo-500">
                      <RotateCw className="h-3.5 w-3.5" /> Rotate
                    </button>
                    <button onClick={() => remove(s)} className="inline-flex items-center gap-1 text-slate-500 hover:text-red-600">
                      <Trash2 className="h-3.5 w-3.5" /> Delete
                    </button>
                  </div>
                </Td>
              </TRow>
            ))}
          </tbody>
        </Table>
      )}

      <Modal open={createOpen} onClose={() => setCreateOpen(false)} title="New secret">
        <CreateSecretForm
          environmentId={environmentId}
          onCreated={(secret) => {
            setSecrets((prev) => [...(prev ?? []), { ...secret, value: undefined }]);
            setReveal({ title: `Created "${secret.key}"`, secret: secret.value! });
            setCreateOpen(false);
          }}
          onClose={() => setCreateOpen(false)}
        />
      </Modal>
    </Card>
  );
}

function CreateSecretForm({
  environmentId,
  onCreated,
  onClose,
}: {
  environmentId: string;
  onCreated: (secret: EnvironmentSecret) => void;
  onClose: () => void;
}) {
  const [key, setKey] = useState("");
  const [value, setValue] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const secret = await api.post<EnvironmentSecret>(`/environments/${environmentId}/secrets/`, {
        key,
        value,
      });
      onCreated(secret);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to create secret.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {error && <ErrorBanner message={error} />}
      <div>
        <Label htmlFor="secret-key">Key</Label>
        <Input id="secret-key" autoFocus required value={key} onChange={(e) => setKey(e.target.value)} placeholder="STRIPE_API_KEY" />
      </div>
      <div>
        <Label htmlFor="secret-value">Value</Label>
        <Input
          id="secret-value"
          required
          type="password"
          value={value}
          onChange={(e) => setValue(e.target.value)}
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
  );
}

// --- API Keys (environment-scoped credentials) ---------------------------

function credentialStatus(c: ApplicationCredential): { label: string; tone: "success" | "danger" | "warning" } {
  if (c.revoked_at) return { label: "Revoked", tone: "danger" };
  if (c.expires_at && new Date(c.expires_at) < new Date()) return { label: "Expired", tone: "warning" };
  return { label: "Active", tone: "success" };
}

function ApiKeysTab({ environmentId }: { environmentId: string }) {
  const [credentials, setCredentials] = useState<ApplicationCredential[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [reveal, setReveal] = useState<{ title: string; secret: string } | null>(null);

  useEffect(() => {
    api
      .get<ApplicationCredential[]>(`/environments/${environmentId}/credentials/`)
      .then(setCredentials)
      .catch((err) =>
        setError(
          err instanceof ApiError && err.status === 403
            ? "You don't have permission to manage this environment's credentials."
            : "Failed to load credentials.",
        ),
      );
  }, [environmentId]);

  async function issue() {
    setError(null);
    try {
      const credential = await api.post<ApplicationCredential>(`/environments/${environmentId}/credentials/`);
      setCredentials((prev) => [credential, ...(prev ?? [])]);
      setReveal({ title: "New credential secret", secret: credential.secret! });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to issue credential.");
    }
  }

  async function revoke(credential: ApplicationCredential) {
    setError(null);
    try {
      const updated = await api.post<ApplicationCredential>(
        `/environments/${environmentId}/credentials/${credential.id}/revoke/`,
      );
      setCredentials((prev) => prev?.map((c) => (c.id === updated.id ? updated : c)) ?? prev);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to revoke credential.");
    }
  }

  async function rotate(credential: ApplicationCredential) {
    setError(null);
    try {
      const fresh = await api.post<ApplicationCredential>(
        `/environments/${environmentId}/credentials/${credential.id}/rotate/`,
      );
      setCredentials((prev) => {
        const withoutOld = (prev ?? []).map((c) =>
          c.id === credential.id ? { ...c, revoked_at: new Date().toISOString() } : c,
        );
        return [fresh, ...withoutOld];
      });
      setReveal({ title: "Rotated credential secret", secret: fresh.secret! });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to rotate credential.");
    }
  }

  return (
    <Card>
      <div className="mb-3 flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold text-slate-700">API credentials</h3>
          <p className="text-xs text-slate-500">
            Scoped to this environment only -- they can never reach another environment&apos;s database or storage,
            even if a broader permission grant exists.
          </p>
        </div>
        <Button size="sm" onClick={issue}>
          New credential
        </Button>
      </div>
      {error && (
        <div className="mb-3">
          <ErrorBanner message={error} />
        </div>
      )}
      {reveal && (
        <div className="mb-3">
          <SecretReveal label={reveal.title} secret={reveal.secret} />
        </div>
      )}
      {credentials === null ? (
        <Spinner className="h-4 w-4 text-slate-400" />
      ) : credentials.length === 0 ? (
        <EmptyState
          title="No credentials yet"
          description="Issue one to let this environment's application authenticate against exactly this environment's resources."
        />
      ) : (
        <Table>
          <THead>
            <Th>Credential</Th>
            <Th>Status</Th>
            <Th>Created</Th>
            <Th>Last used</Th>
            <Th>
              <span className="sr-only">Actions</span>
            </Th>
          </THead>
          <tbody>
            {credentials.map((c) => {
              const { label, tone } = credentialStatus(c);
              const active = tone === "success";
              return (
                <TRow key={c.id}>
                  <Td className="font-mono text-xs text-slate-400">{c.id.slice(0, 8)}...</Td>
                  <Td>
                    <Badge tone={tone}>{label}</Badge>
                  </Td>
                  <Td className="text-slate-500">{new Date(c.created_at).toLocaleString()}</Td>
                  <Td className="text-slate-500">{c.last_used_at ? new Date(c.last_used_at).toLocaleString() : "Never"}</Td>
                  <Td>
                    {active && (
                      <div className="flex justify-end gap-3 text-xs">
                        <button onClick={() => rotate(c)} className="inline-flex items-center gap-1 text-indigo-600 hover:text-indigo-500">
                          <RotateCw className="h-3.5 w-3.5" /> Rotate
                        </button>
                        <button onClick={() => revoke(c)} className="inline-flex items-center gap-1 text-slate-500 hover:text-red-600">
                          <ShieldOff className="h-3.5 w-3.5" /> Revoke
                        </button>
                      </div>
                    )}
                  </Td>
                </TRow>
              );
            })}
          </tbody>
        </Table>
      )}
    </Card>
  );
}

// --- Database / Storage bindings ------------------------------------------

function DatabaseTab({
  environment,
  organizationId,
  onUpdated,
}: {
  environment: Environment;
  organizationId: string;
  onUpdated: (env: Environment) => void;
}) {
  const [resources, setResources] = useState<OrgResource[] | null>(null);
  const [selected, setSelected] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listOrgResources(organizationId)
      .then((r) => setResources(r.filter((x) => x.kind === "database")))
      .catch(() => setResources([]));
  }, [organizationId]);

  async function bind() {
    setError(null);
    try {
      const updated = await api.patch<Environment>(`/environments/${environment.id}/database/`, {
        tenant_database_id: selected,
      });
      onUpdated(updated);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to connect database.");
    }
  }

  async function unbind() {
    setError(null);
    try {
      const updated = await api.patch<Environment>(`/environments/${environment.id}/database/`, {
        tenant_database_id: null,
      });
      onUpdated(updated);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to disconnect database.");
    }
  }

  return (
    <Card>
      <h3 className="mb-3 text-sm font-semibold text-slate-700">Database</h3>
      <p className="mb-4 text-xs text-slate-500">
        Bind an existing tenant database to this environment -- this reuses the platform&apos;s own database
        engine, never a duplicate. A credential scoped to a different environment can never reach it.
      </p>
      {error && (
        <div className="mb-3">
          <ErrorBanner message={error} />
        </div>
      )}
      {environment.database_status === "connected" ? (
        <div className="flex items-center justify-between rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2.5">
          <span className="flex items-center gap-2 text-sm text-emerald-800">
            <Database className="h-4 w-4" /> Connected
          </span>
          <Button size="sm" variant="secondary" onClick={unbind}>
            Disconnect
          </Button>
        </div>
      ) : resources === null ? (
        <Spinner className="h-4 w-4 text-slate-400" />
      ) : resources.length === 0 ? (
        <p className="text-sm text-slate-500">No tenant databases exist in this organization yet.</p>
      ) : (
        <div className="flex items-end gap-2">
          <div className="flex-1">
            <Label htmlFor="db-select">Tenant database</Label>
            <Select id="db-select" value={selected} onChange={(e) => setSelected(e.target.value)}>
              <option value="">Select a database…</option>
              {resources.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.projectName} / {r.name}
                </option>
              ))}
            </Select>
          </div>
          <Button size="sm" disabled={!selected} onClick={bind}>
            Connect
          </Button>
        </div>
      )}
    </Card>
  );
}

function StorageTab({
  environment,
  organizationId,
  onUpdated,
}: {
  environment: Environment;
  organizationId: string;
  onUpdated: (env: Environment) => void;
}) {
  const [resources, setResources] = useState<OrgResource[] | null>(null);
  const [selected, setSelected] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listOrgResources(organizationId)
      .then((r) => setResources(r.filter((x) => x.kind === "bucket")))
      .catch(() => setResources([]));
  }, [organizationId]);

  async function bind() {
    setError(null);
    try {
      const updated = await api.patch<Environment>(`/environments/${environment.id}/storage/`, {
        bucket_id: selected,
      });
      onUpdated(updated);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to connect storage.");
    }
  }

  async function unbind() {
    setError(null);
    try {
      const updated = await api.patch<Environment>(`/environments/${environment.id}/storage/`, {
        bucket_id: null,
      });
      onUpdated(updated);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to disconnect storage.");
    }
  }

  return (
    <Card>
      <h3 className="mb-3 text-sm font-semibold text-slate-700">Storage</h3>
      <p className="mb-4 text-xs text-slate-500">
        Bind an existing bucket to this environment. Example: this application&apos;s Development environment
        uses &quot;dev-files&quot;; Production uses &quot;production-files&quot; -- a Development credential can never read
        Production&apos;s bucket.
      </p>
      {error && (
        <div className="mb-3">
          <ErrorBanner message={error} />
        </div>
      )}
      {environment.storage_status === "connected" ? (
        <div className="flex items-center justify-between rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2.5">
          <span className="flex items-center gap-2 text-sm text-emerald-800">
            <HardDrive className="h-4 w-4" /> Connected
          </span>
          <Button size="sm" variant="secondary" onClick={unbind}>
            Disconnect
          </Button>
        </div>
      ) : resources === null ? (
        <Spinner className="h-4 w-4 text-slate-400" />
      ) : resources.length === 0 ? (
        <p className="text-sm text-slate-500">No buckets exist in this organization yet.</p>
      ) : (
        <div className="flex items-end gap-2">
          <div className="flex-1">
            <Label htmlFor="bucket-select">Bucket</Label>
            <Select id="bucket-select" value={selected} onChange={(e) => setSelected(e.target.value)}>
              <option value="">Select a bucket…</option>
              {resources.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.projectName} / {r.name}
                </option>
              ))}
            </Select>
          </div>
          <Button size="sm" disabled={!selected} onClick={bind}>
            Connect
          </Button>
        </div>
      )}
    </Card>
  );
}

// --- Auth (a focused slice of config.auth) --------------------------------

function AuthTab({
  environment,
  onUpdated,
}: {
  environment: Environment;
  onUpdated: (env: Environment) => void;
}) {
  const authConfig = (environment.config.auth as Record<string, unknown>) ?? {};
  const [allowedOrigins, setAllowedOrigins] = useState(
    typeof authConfig.allowed_origins === "string" ? authConfig.allowed_origins : "",
  );
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  async function save(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSaving(true);
    setSaved(false);
    try {
      const updated = await api.patch<Environment>(`/environments/${environment.id}/`, {
        config: { ...environment.config, auth: { ...authConfig, allowed_origins: allowedOrigins } },
      });
      onUpdated(updated);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to save.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Card>
      <h3 className="mb-3 text-sm font-semibold text-slate-700">Authentication configuration</h3>
      <p className="mb-4 text-xs text-slate-500">
        Non-secret authentication settings for this environment&apos;s application (e.g. allowed CORS origins for
        this environment specifically). Credentials themselves live under API Keys.
      </p>
      {error && (
        <div className="mb-3">
          <ErrorBanner message={error} />
        </div>
      )}
      <form onSubmit={save} className="space-y-3">
        <div>
          <Label htmlFor="allowed-origins">Allowed origins (comma-separated)</Label>
          <Input
            id="allowed-origins"
            value={allowedOrigins}
            onChange={(e) => setAllowedOrigins(e.target.value)}
            placeholder="https://staging.example.com, https://staging-preview.example.com"
          />
        </div>
        <div className="flex justify-end">
          <Button type="submit" size="sm" disabled={saving}>
            {saving ? "..." : saved ? "Saved" : "Save"}
          </Button>
        </div>
      </form>
    </Card>
  );
}

// --- Webhooks --------------------------------------------------------------

function WebhooksTab({ environmentId }: { environmentId: string }) {
  const [webhooks, setWebhooks] = useState<EnvironmentWebhook[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [reveal, setReveal] = useState<{ title: string; secret: string } | null>(null);
  const [createOpen, setCreateOpen] = useState(false);

  useEffect(() => {
    api
      .get<EnvironmentWebhook[]>(`/environments/${environmentId}/webhooks/`)
      .then(setWebhooks)
      .catch(() => setWebhooks([]));
  }, [environmentId]);

  async function toggle(webhook: EnvironmentWebhook) {
    setError(null);
    try {
      const updated = await api.patch<EnvironmentWebhook>(
        `/environments/${environmentId}/webhooks/${webhook.id}/`,
        { enabled: !webhook.enabled },
      );
      setWebhooks((prev) => prev?.map((w) => (w.id === webhook.id ? updated : w)) ?? prev);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to update webhook.");
    }
  }

  async function remove(webhook: EnvironmentWebhook) {
    setError(null);
    try {
      await api.del(`/environments/${environmentId}/webhooks/${webhook.id}/`);
      setWebhooks((prev) => prev?.filter((w) => w.id !== webhook.id) ?? prev);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to delete webhook.");
    }
  }

  return (
    <Card>
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-slate-700">Webhooks</h3>
        <Button size="sm" onClick={() => setCreateOpen(true)}>
          New webhook
        </Button>
      </div>
      {error && (
        <div className="mb-3">
          <ErrorBanner message={error} />
        </div>
      )}
      {reveal && (
        <div className="mb-3">
          <SecretReveal label={reveal.title} secret={reveal.secret} />
        </div>
      )}
      {webhooks === null ? (
        <Spinner className="h-4 w-4 text-slate-400" />
      ) : webhooks.length === 0 ? (
        <EmptyState title="No webhooks yet" description="Notify an external URL when events happen in this environment." />
      ) : (
        <Table>
          <THead>
            <Th>URL</Th>
            <Th>Events</Th>
            <Th>Status</Th>
            <Th>
              <span className="sr-only">Actions</span>
            </Th>
          </THead>
          <tbody>
            {webhooks.map((w) => (
              <TRow key={w.id}>
                <Td className="font-mono text-xs text-slate-900">{w.url}</Td>
                <Td className="text-slate-500">{w.event_types.join(", ") || "—"}</Td>
                <Td>
                  <Badge tone={w.enabled ? "success" : "default"}>{w.enabled ? "Enabled" : "Disabled"}</Badge>
                </Td>
                <Td>
                  <div className="flex justify-end gap-3 text-xs">
                    <button onClick={() => toggle(w)} className="text-slate-500 hover:text-slate-800">
                      {w.enabled ? "Disable" : "Enable"}
                    </button>
                    <button onClick={() => remove(w)} className="text-slate-500 hover:text-red-600">
                      Delete
                    </button>
                  </div>
                </Td>
              </TRow>
            ))}
          </tbody>
        </Table>
      )}

      <Modal open={createOpen} onClose={() => setCreateOpen(false)} title="New webhook">
        <CreateWebhookForm
          environmentId={environmentId}
          onCreated={(webhook) => {
            setWebhooks((prev) => [{ ...webhook, signing_secret: undefined }, ...(prev ?? [])]);
            setReveal({ title: "Webhook signing secret", secret: webhook.signing_secret! });
            setCreateOpen(false);
          }}
          onClose={() => setCreateOpen(false)}
        />
      </Modal>
    </Card>
  );
}

function CreateWebhookForm({
  environmentId,
  onCreated,
  onClose,
}: {
  environmentId: string;
  onCreated: (webhook: EnvironmentWebhook) => void;
  onClose: () => void;
}) {
  const [url, setUrl] = useState("");
  const [events, setEvents] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const webhook = await api.post<EnvironmentWebhook>(`/environments/${environmentId}/webhooks/`, {
        url,
        event_types: events
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean),
      });
      onCreated(webhook);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to create webhook.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {error && <ErrorBanner message={error} />}
      <div>
        <Label htmlFor="webhook-url">URL</Label>
        <Input
          id="webhook-url"
          type="url"
          autoFocus
          required
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="https://hooks.example.com/staging"
        />
      </div>
      <div>
        <Label htmlFor="webhook-events">Event types (comma-separated)</Label>
        <Input
          id="webhook-events"
          value={events}
          onChange={(e) => setEvents(e.target.value)}
          placeholder="file.uploaded, database.row.created"
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
  );
}

// --- Logs (full paginated audit trail for this environment) ---------------

const LOG_PAGE_SIZE = 25;

function LogsTab({ environmentId, organizationId }: { environmentId: string; organizationId: string }) {
  const [events, setEvents] = useState<AuditEvent[] | null>(null);
  const [count, setCount] = useState(0);
  const [offset, setOffset] = useState(0);
  const [error, setError] = useState<string | null>(null);

  async function load(currentOffset: number) {
    try {
      const page = await api.get<Paginated<AuditEvent>>(
        `/organizations/${organizationId}/audit/?resource_type=environment&resource_id=${environmentId}` +
          `&limit=${LOG_PAGE_SIZE}&offset=${currentOffset}`,
      );
      setEvents(page.results);
      setCount(page.count);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load logs.");
      setEvents([]);
    }
  }

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    load(0);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [environmentId]);

  if (events === null && !error) return <Spinner className="h-4 w-4 text-slate-400" />;

  return (
    <Card>
      <h3 className="mb-3 text-sm font-semibold text-slate-700">Logs</h3>
      {error && (
        <div className="mb-3">
          <ErrorBanner message={error} />
        </div>
      )}
      {events && events.length === 0 ? (
        <EmptyState title="No log entries yet" description="Actions on this environment will appear here." />
      ) : (
        <>
          <Table>
            <THead>
              <Th>Time</Th>
              <Th>Action</Th>
              <Th>Result</Th>
            </THead>
            <tbody>
              {events?.map((event) => (
                <TRow key={event.id}>
                  <Td className="whitespace-nowrap text-slate-400">{new Date(event.timestamp).toLocaleString()}</Td>
                  <Td className="font-medium text-slate-900">{event.action}</Td>
                  <Td>
                    <Badge tone={event.result === "success" ? "success" : event.result === "denied" ? "warning" : "danger"}>
                      {event.result}
                    </Badge>
                  </Td>
                </TRow>
              ))}
            </tbody>
          </Table>
          <div className="mt-4 flex items-center justify-between text-sm text-slate-500">
            <span>
              {count === 0 ? "0 events" : `${offset + 1}-${Math.min(offset + LOG_PAGE_SIZE, count)} of ${count}`}
            </span>
            <div className="flex gap-2">
              <Button
                variant="secondary"
                size="sm"
                disabled={offset === 0}
                onClick={() => {
                  const next = Math.max(0, offset - LOG_PAGE_SIZE);
                  setOffset(next);
                  load(next);
                }}
              >
                Previous
              </Button>
              <Button
                variant="secondary"
                size="sm"
                disabled={offset + LOG_PAGE_SIZE >= count}
                onClick={() => {
                  const next = offset + LOG_PAGE_SIZE;
                  setOffset(next);
                  load(next);
                }}
              >
                Next
              </Button>
            </div>
          </div>
        </>
      )}
    </Card>
  );
}

// --- Activity (recent summary, not paginated) -----------------------------

function ActivityTab({ environmentId, organizationId }: { environmentId: string; organizationId: string }) {
  const [events, setEvents] = useState<AuditEvent[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .get<Paginated<AuditEvent>>(
        `/organizations/${organizationId}/audit/?resource_type=environment&resource_id=${environmentId}` +
          `&limit=10&offset=0`,
      )
      .then((page) => setEvents(page.results))
      .catch(() => {
        setError("Failed to load recent activity.");
        setEvents([]);
      });
  }, [environmentId, organizationId]);

  return (
    <Card>
      <h3 className="mb-3 text-sm font-semibold text-slate-700">Recent activity</h3>
      {error && (
        <div className="mb-3">
          <ErrorBanner message={error} />
        </div>
      )}
      {events === null ? (
        <Spinner className="h-4 w-4 text-slate-400" />
      ) : events.length === 0 ? (
        <p className="text-sm text-slate-500">No recent activity.</p>
      ) : (
        <ul className="space-y-2 text-sm">
          {events.map((event) => (
            <li key={event.id} className="flex items-center justify-between border-b border-slate-100 pb-2 last:border-0">
              <span className="text-slate-800">{event.action}</span>
              <span className="text-xs text-slate-400">{new Date(event.timestamp).toLocaleString()}</span>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

// --- Settings --------------------------------------------------------------

function SettingsTab({
  environment,
  onUpdated,
  onDeleted,
}: {
  environment: Environment;
  onUpdated: (env: Environment) => void;
  onDeleted: () => void;
}) {
  const [name, setName] = useState(environment.name);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);

  async function saveName(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSaving(true);
    try {
      const updated = await api.patch<Environment>(`/environments/${environment.id}/`, { name });
      onUpdated(updated);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to save.");
    } finally {
      setSaving(false);
    }
  }

  async function toggleStatus() {
    setError(null);
    try {
      const action = environment.status === "active" ? "disable" : "enable";
      const updated = await api.post<Environment>(`/environments/${environment.id}/${action}/`);
      onUpdated(updated);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to update status.");
    }
  }

  return (
    <div className="space-y-6">
      <Card>
        <h3 className="mb-3 text-sm font-semibold text-slate-700">General</h3>
        {error && (
          <div className="mb-3">
            <ErrorBanner message={error} />
          </div>
        )}
        <form onSubmit={saveName} className="flex items-end gap-2">
          <div className="flex-1">
            <Label htmlFor="settings-name">Name</Label>
            <Input id="settings-name" value={name} onChange={(e) => setName(e.target.value)} />
          </div>
          <Button type="submit" size="sm" disabled={saving}>
            {saving ? "..." : "Save"}
          </Button>
        </form>
      </Card>

      <Card>
        <h3 className="mb-3 text-sm font-semibold text-slate-700">Lifecycle</h3>
        <div className="flex flex-wrap gap-2">
          <Button variant="secondary" size="sm" onClick={toggleStatus}>
            {environment.status === "active" ? "Disable environment" : "Enable environment"}
          </Button>
          <Button variant="danger" size="sm" onClick={() => setDeleteOpen(true)}>
            Delete environment
          </Button>
        </div>
      </Card>

      <SettingsDeleteModal
        open={deleteOpen}
        environment={environment}
        onClose={() => setDeleteOpen(false)}
        onDeleted={onDeleted}
      />
    </div>
  );
}

function SettingsDeleteModal({
  open,
  environment,
  onClose,
  onDeleted,
}: {
  open: boolean;
  environment: Environment;
  onClose: () => void;
  onDeleted: () => void;
}) {
  const [confirmName, setConfirmName] = useState("");
  const [confirmProduction, setConfirmProduction] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (open) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setConfirmName("");
      setConfirmProduction(false);
      setError(null);
    }
  }, [open]);

  const nameMatches = confirmName === environment.name;
  const canSubmit = nameMatches && (!environment.is_production_tier || confirmProduction);

  async function handleDelete() {
    if (!canSubmit) return;
    setSubmitting(true);
    setError(null);
    try {
      await api.del(`/environments/${environment.id}/`, {
        confirm_name: confirmName,
        confirm_production_understanding: confirmProduction,
      });
      onDeleted();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to delete environment.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Modal open={open} onClose={onClose} title={`Delete "${environment.name}"?`}>
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
          <Label htmlFor="settings-confirm-name">
            Type <span className="font-mono font-semibold">{environment.name}</span> to confirm
          </Label>
          <Input id="settings-confirm-name" autoFocus value={confirmName} onChange={(e) => setConfirmName(e.target.value)} />
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
