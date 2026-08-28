"use client";

import { useEffect, useState, type FormEvent } from "react";
import Link from "next/link";
import { CheckCircle2, Layers3, RotateCw, ShieldOff, XCircle } from "lucide-react";
import {
  api,
  ApiError,
  type Application,
  type ApplicationCredential,
  type Environment,
  type Organization,
  type ResourceGrant,
} from "@/lib/api";
import { listOrgResources, type OrgResource } from "@/lib/org-resources";
import {
  Badge,
  Button,
  Card,
  ErrorBanner,
  Input,
  Label,
  Modal,
  PageHeader,
  PageLoading,
  Select,
  SecretReveal,
  Spinner,
  Table,
  Td,
  Th,
  THead,
  TRow,
} from "@/components/ui";

const STORAGE_RESOURCE = "storage.bucket";
const DATABASE_RESOURCE = "databases.tenant_database";

function isActiveGrant(g: ResourceGrant): boolean {
  return !g.expires_at || new Date(g.expires_at) > new Date();
}

/** Translates the application's real ResourceGrants into plain-language
 * CAN/CANNOT statements against every resource the organization actually
 * has (Section 16 of the professionalization brief) -- generated
 * entirely from live grants and a live resource list, never a fixed or
 * assumed set. Resources with no grant at all, and resources with a
 * read-only grant missing write, both surface under CANNOT by name --
 * not a fabricated abstract category. */
function AccessSummary({ resources, grants }: { resources: OrgResource[]; grants: ResourceGrant[] }) {
  const active = grants.filter(isActiveGrant);
  const can: string[] = [];
  const cannot: string[] = [];

  for (const r of resources) {
    const resourceType = r.kind === "bucket" ? STORAGE_RESOURCE : DATABASE_RESOURCE;
    const readCode = r.kind === "bucket" ? "storage.read" : "database.read";
    const writeCode = r.kind === "bucket" ? "storage.write" : "database.write";
    const matching = active.filter((g) => g.resource_type === resourceType && g.resource_id === r.id);
    const canRead = matching.some((g) => g.permission === readCode);
    const canWrite = matching.some((g) => g.permission === writeCode);
    const noun = r.kind === "bucket" ? "files in" : "data in";

    if (canRead && canWrite) can.push(`Read and write ${noun} "${r.name}"`);
    else if (canRead) can.push(`Read ${noun} "${r.name}"`);
    else if (canWrite) can.push(`Write ${noun} "${r.name}" (without read)`);

    if (!canWrite) cannot.push(`${canRead ? "Modify" : "Access"} ${noun} "${r.name}"`);
  }

  const CANNOT_LIMIT = 6;
  const shownCannot = cannot.slice(0, CANNOT_LIMIT);
  const hiddenCannotCount = cannot.length - shownCannot.length;

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
      <Card>
        <h3 className="mb-2 flex items-center gap-1.5 text-sm font-semibold text-emerald-700">
          <CheckCircle2 className="h-4 w-4" /> This application CAN
        </h3>
        {can.length === 0 ? (
          <p className="text-sm text-slate-500">Nothing yet — grant it access to a bucket or database below.</p>
        ) : (
          <ul className="space-y-1.5 text-sm text-slate-700">
            {can.map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ul>
        )}
      </Card>
      <Card>
        <h3 className="mb-2 flex items-center gap-1.5 text-sm font-semibold text-red-700">
          <XCircle className="h-4 w-4" /> This application CANNOT
        </h3>
        {shownCannot.length === 0 ? (
          <p className="text-sm text-slate-500">
            It has full read/write access to everything in this organization.
          </p>
        ) : (
          <ul className="space-y-1.5 text-sm text-slate-700">
            {shownCannot.map((line) => (
              <li key={line}>{line}</li>
            ))}
            {hiddenCannotCount > 0 && <li className="text-slate-400">+{hiddenCannotCount} more</li>}
          </ul>
        )}
      </Card>
    </div>
  );
}

function credentialStatus(c: ApplicationCredential): { label: string; tone: "success" | "danger" | "warning" } {
  if (c.revoked_at) return { label: "Revoked", tone: "danger" };
  if (c.expires_at && new Date(c.expires_at) < new Date()) return { label: "Expired", tone: "warning" };
  return { label: "Active", tone: "success" };
}

export default function ApplicationDetailClient({ applicationId }: { applicationId: string }) {
  const [application, setApplication] = useState<Application | null>(null);
  const [org, setOrg] = useState<Organization | null>(null);
  const [credentials, setCredentials] = useState<ApplicationCredential[] | null>(null);
  const [credentialsError, setCredentialsError] = useState<string | null>(null);
  const [grants, setGrants] = useState<ResourceGrant[] | null>(null);
  const [grantsError, setGrantsError] = useState<string | null>(null);
  const [resources, setResources] = useState<OrgResource[] | null>(null);
  const [environments, setEnvironments] = useState<Environment[] | null>(null);
  const [environmentsError, setEnvironmentsError] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [errorDetail, setErrorDetail] = useState<unknown>(null);
  const [revealSecret, setRevealSecret] = useState<{ title: string; secret: string } | null>(null);
  const [grantModalOpen, setGrantModalOpen] = useState(false);
  const [createEnvOpen, setCreateEnvOpen] = useState(false);

  async function load() {
    try {
      const app = await api.get<Application>(`/applications/${applicationId}/`);
      setApplication(app);
      api.get<Organization>(`/organizations/${app.organization}/`).then(setOrg).catch(() => {});
      listOrgResources(app.organization)
        .then(setResources)
        .catch(() => setResources([]));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load application.");
      setErrorDetail(err);
      return;
    }
    try {
      setEnvironments(await api.get<Environment[]>(`/applications/${applicationId}/environments/`));
    } catch (err) {
      setEnvironments([]);
      setEnvironmentsError(
        err instanceof ApiError && err.status === 403
          ? "You don't have permission to view this application's environments."
          : "Failed to load environments.",
      );
    }
    try {
      setCredentials(await api.get<ApplicationCredential[]>(`/applications/${applicationId}/credentials/`));
    } catch (err) {
      setCredentials([]);
      setCredentialsError(
        err instanceof ApiError && err.status === 403
          ? "You don't have permission to manage this application's credentials."
          : "Failed to load credentials.",
      );
    }
    try {
      setGrants(await api.get<ResourceGrant[]>(`/applications/${applicationId}/resource-grants/`));
    } catch (err) {
      setGrants([]);
      setGrantsError(
        err instanceof ApiError && err.status === 403
          ? "You don't have permission to manage this application's permissions."
          : "Failed to load permissions.",
      );
    }
  }

  useEffect(() => {
    // One-shot fetch-on-mount/param-change, not a state-sync loop.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [applicationId]);

  async function issueCredential() {
    setCredentialsError(null);
    try {
      const credential = await api.post<ApplicationCredential>(
        `/applications/${applicationId}/credentials/`,
      );
      setCredentials((prev) => [credential, ...(prev ?? [])]);
      setRevealSecret({ title: "New credential secret", secret: credential.secret! });
    } catch (err) {
      setCredentialsError(err instanceof ApiError ? err.message : "Failed to create credential.");
    }
  }

  async function revoke(credential: ApplicationCredential) {
    setCredentialsError(null);
    try {
      const updated = await api.post<ApplicationCredential>(
        `/applications/${applicationId}/credentials/${credential.id}/revoke/`,
      );
      setCredentials((prev) => prev?.map((c) => (c.id === updated.id ? updated : c)) ?? prev);
    } catch (err) {
      setCredentialsError(err instanceof ApiError ? err.message : "Failed to revoke credential.");
    }
  }

  async function rotate(credential: ApplicationCredential) {
    setCredentialsError(null);
    try {
      const fresh = await api.post<ApplicationCredential>(
        `/applications/${applicationId}/credentials/${credential.id}/rotate/`,
      );
      setCredentials((prev) => {
        const withoutOld = (prev ?? []).map((c) =>
          c.id === credential.id ? { ...c, revoked_at: new Date().toISOString() } : c,
        );
        return [fresh, ...withoutOld];
      });
      setRevealSecret({ title: "Rotated credential secret", secret: fresh.secret! });
    } catch (err) {
      setCredentialsError(err instanceof ApiError ? err.message : "Failed to rotate credential.");
    }
  }

  if (!application && !error) return <PageLoading />;
  if (error && !application) return <ErrorBanner message={error} error={errorDetail} />;
  if (!application) return null;

  return (
    <div className="space-y-8">
      <PageHeader
        title={application.name}
        breadcrumbs={[
          { label: "Organizations", href: "/orgs" },
          ...(org
            ? [
                { label: org.name, href: `/orgs/${org.id}` },
                { label: "Developer", href: `/orgs/${org.id}/developer` },
                { label: "Applications", href: `/orgs/${org.id}/developer/applications` },
              ]
            : []),
          { label: application.name },
        ]}
        description={application.description || undefined}
      />

      <section>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-slate-600">Environments</h2>
          <Button size="sm" onClick={() => setCreateEnvOpen(true)}>
            New environment
          </Button>
        </div>
        {environmentsError && (
          <div className="mb-3">
            <ErrorBanner message={environmentsError} />
          </div>
        )}
        {environments && environments.length > 0 && (
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {environments.map((env) => (
              <Link key={env.id} href={`/environments/${env.id}`} className="block">
                <Card className="transition-colors hover:border-indigo-400/40 hover:bg-slate-50">
                  <div className="flex items-center justify-between">
                    <span className="flex items-center gap-2 font-medium text-slate-900">
                      <Layers3 className="h-4 w-4 text-indigo-600" />
                      {env.name}
                    </span>
                    {env.is_production_tier && <Badge tone="danger">Production</Badge>}
                  </div>
                  <p className="mt-1.5 text-xs text-slate-500">
                    {env.environment_type} · {env.status === "active" ? "Active" : "Disabled"}
                  </p>
                </Card>
              </Link>
            ))}
          </div>
        )}
        {environments && environments.length === 0 && !environmentsError && (
          <p className="text-sm text-slate-500">
            No environments yet -- create Development, Staging, or Production for this application.
          </p>
        )}
      </section>

      <section>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-slate-600">Credentials</h2>
          <Button size="sm" onClick={issueCredential}>
            New credential
          </Button>
        </div>
        {credentialsError && (
          <div className="mb-3">
            <ErrorBanner message={credentialsError} />
          </div>
        )}
        {revealSecret && (
          <div className="mb-3">
            <SecretReveal label={revealSecret.title} secret={revealSecret.secret} />
          </div>
        )}
        {credentials && credentials.length > 0 && (
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
                    <Td className="text-slate-500">
                      {c.last_used_at ? new Date(c.last_used_at).toLocaleString() : "Never"}
                    </Td>
                    <Td>
                      {active && (
                        <div className="flex justify-end gap-3 text-xs">
                          <button
                            onClick={() => rotate(c)}
                            className="inline-flex items-center gap-1 text-indigo-600 hover:text-indigo-500"
                          >
                            <RotateCw className="h-3.5 w-3.5" />
                            Rotate
                          </button>
                          <button
                            onClick={() => revoke(c)}
                            className="inline-flex items-center gap-1 text-slate-500 hover:text-red-600"
                          >
                            <ShieldOff className="h-3.5 w-3.5" />
                            Revoke
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
        {credentials && credentials.length === 0 && !credentialsError && (
          <p className="text-sm text-slate-500">
            No credentials yet. Issue one for this application to authenticate as its service account.
          </p>
        )}
      </section>

      {grants && (
        <section>
          <h2 className="mb-3 text-sm font-semibold text-slate-600">Access summary</h2>
          {resources === null ? (
            <div className="flex items-center gap-2 text-sm text-slate-400">
              <Spinner className="h-4 w-4" /> Building access summary…
            </div>
          ) : (
            <AccessSummary resources={resources} grants={grants} />
          )}
        </section>
      )}

      <section>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-slate-600">Resource permissions</h2>
          {grants && (
            <Button size="sm" onClick={() => setGrantModalOpen(true)}>
              Grant permission
            </Button>
          )}
        </div>
        {grantsError && (
          <div className="mb-3">
            <ErrorBanner message={grantsError} />
          </div>
        )}
        {grants && grants.length > 0 && (
          <Table>
            <THead>
              <Th>Permission</Th>
              <Th>Resource</Th>
              <Th>Expires</Th>
              <Th>Granted</Th>
            </THead>
            <tbody>
              {grants.map((g) => {
                const kind = g.resource_type === STORAGE_RESOURCE ? "bucket" : g.resource_type === DATABASE_RESOURCE ? "database" : null;
                const resolved = resources?.find((r) => r.kind === kind && r.id === g.resource_id);
                return (
                  <TRow key={g.id}>
                    <Td className="font-medium text-slate-900">{g.permission}</Td>
                    <Td className="text-slate-500">
                      <span title={`${g.resource_type}:${g.resource_id}`}>
                        {resolved ? resolved.name : `${g.resource_type}:${g.resource_id}`}
                      </span>
                    </Td>
                    <Td className="text-slate-500">
                      {g.expires_at ? new Date(g.expires_at).toLocaleString() : "Never"}
                    </Td>
                    <Td className="text-slate-500">{new Date(g.created_at).toLocaleString()}</Td>
                  </TRow>
                );
              })}
            </tbody>
          </Table>
        )}
        {grants && grants.length === 0 && !grantsError && (
          <p className="text-sm text-slate-500">
            This application has no scoped permissions yet — it can authenticate but cannot access any
            resource until you grant it one.
          </p>
        )}
      </section>

      <GrantPermissionModal
        open={grantModalOpen}
        applicationId={applicationId}
        onClose={() => setGrantModalOpen(false)}
        onCreated={(grant) => {
          setGrants((prev) => [...(prev ?? []), grant]);
          setGrantModalOpen(false);
        }}
      />

      <CreateEnvironmentModal
        open={createEnvOpen}
        applicationId={applicationId}
        onClose={() => setCreateEnvOpen(false)}
        onCreated={(env) => {
          setEnvironments((prev) => [...(prev ?? []), env]);
          setCreateEnvOpen(false);
        }}
      />
    </div>
  );
}

function GrantPermissionModal({
  open,
  applicationId,
  onClose,
  onCreated,
}: {
  open: boolean;
  applicationId: string;
  onClose: () => void;
  onCreated: (grant: ResourceGrant) => void;
}) {
  const [permissionCode, setPermissionCode] = useState("");
  const [resourceType, setResourceType] = useState("");
  const [resourceId, setResourceId] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [errorDetail, setErrorDetail] = useState<unknown>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const grant = await api.post<ResourceGrant>(`/applications/${applicationId}/resource-grants/`, {
        permission_code: permissionCode,
        resource_type: resourceType,
        resource_id: resourceId,
      });
      setPermissionCode("");
      setResourceType("");
      setResourceId("");
      onCreated(grant);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to grant permission.");
      setErrorDetail(err);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Modal open={open} onClose={onClose} title="Grant permission">
      <form onSubmit={handleSubmit} className="space-y-4">
        {error && <ErrorBanner message={error} error={errorDetail} />}
        <div>
          <Label htmlFor="grant-permission">Permission code</Label>
          <Input
            id="grant-permission"
            autoFocus
            required
            value={permissionCode}
            onChange={(e) => setPermissionCode(e.target.value)}
            placeholder="storage.files.read"
          />
        </div>
        <div>
          <Label htmlFor="grant-resource-type">Resource type</Label>
          <Input
            id="grant-resource-type"
            required
            value={resourceType}
            onChange={(e) => setResourceType(e.target.value)}
            placeholder="bucket"
          />
        </div>
        <div>
          <Label htmlFor="grant-resource-id">Resource ID</Label>
          <Input
            id="grant-resource-id"
            required
            value={resourceId}
            onChange={(e) => setResourceId(e.target.value)}
            placeholder="the bucket's UUID"
          />
        </div>
        <div className="flex justify-end gap-2">
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" disabled={submitting}>
            {submitting ? "..." : "Grant"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

const ENVIRONMENT_TYPES = ["development", "staging", "production", "custom"];

function CreateEnvironmentModal({
  open,
  applicationId,
  onClose,
  onCreated,
}: {
  open: boolean;
  applicationId: string;
  onClose: () => void;
  onCreated: (env: Environment) => void;
}) {
  const [name, setName] = useState("");
  const [environmentType, setEnvironmentType] = useState("development");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const env = await api.post<Environment>(`/applications/${applicationId}/environments/`, {
        name,
        environment_type: environmentType,
      });
      setName("");
      setEnvironmentType("development");
      onCreated(env);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to create environment.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Modal open={open} onClose={onClose} title="New environment">
      <form onSubmit={handleSubmit} className="space-y-4">
        {error && <ErrorBanner message={error} />}
        <div>
          <Label htmlFor="app-env-name">Name</Label>
          <Input
            id="app-env-name"
            autoFocus
            required
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Production"
          />
        </div>
        <div>
          <Label htmlFor="app-env-type">Type</Label>
          <Select id="app-env-type" value={environmentType} onChange={(e) => setEnvironmentType(e.target.value)}>
            {ENVIRONMENT_TYPES.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </Select>
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
