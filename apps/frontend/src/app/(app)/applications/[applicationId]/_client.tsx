"use client";

import { useEffect, useState, type FormEvent } from "react";
import { RotateCw, ShieldOff } from "lucide-react";
import {
  api,
  ApiError,
  type Application,
  type ApplicationCredential,
  type Organization,
  type ResourceGrant,
} from "@/lib/api";
import {
  Badge,
  Button,
  ErrorBanner,
  Input,
  Label,
  Modal,
  PageHeader,
  PageLoading,
  SecretReveal,
  Table,
  Td,
  Th,
  THead,
  TRow,
} from "@/components/ui";

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
  const [error, setError] = useState<string | null>(null);
  const [revealSecret, setRevealSecret] = useState<{ title: string; secret: string } | null>(null);
  const [grantModalOpen, setGrantModalOpen] = useState(false);

  async function load() {
    try {
      const app = await api.get<Application>(`/applications/${applicationId}/`);
      setApplication(app);
      api.get<Organization>(`/organizations/${app.organization}/`).then(setOrg).catch(() => {});
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load application.");
      return;
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
  if (error && !application) return <ErrorBanner message={error} />;
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
              {grants.map((g) => (
                <TRow key={g.id}>
                  <Td className="font-medium text-slate-900">{g.permission}</Td>
                  <Td className="text-slate-400">
                    {g.resource_type}:{g.resource_id}
                  </Td>
                  <Td className="text-slate-500">
                    {g.expires_at ? new Date(g.expires_at).toLocaleString() : "Never"}
                  </Td>
                  <Td className="text-slate-500">{new Date(g.created_at).toLocaleString()}</Td>
                </TRow>
              ))}
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
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Modal open={open} onClose={onClose} title="Grant permission">
      <form onSubmit={handleSubmit} className="space-y-4">
        {error && <ErrorBanner message={error} />}
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
