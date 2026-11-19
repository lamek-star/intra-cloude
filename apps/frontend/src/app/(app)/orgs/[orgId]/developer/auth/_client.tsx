"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { type FormEvent, useState } from "react";
import { api, ApiError, type Organization } from "@/lib/api";
import {
  Badge,
  Button,
  Card,
  CopyButton,
  EmptyState,
  ErrorBanner,
  Input,
  Label,
  Modal,
  PageHeader,
  PageLoading,
  SecretReveal,
  Table,
  Td,
  Textarea,
  Th,
  THead,
  TRow,
} from "@/components/ui";
import { DeveloperNav } from "@/components/DeveloperNav";
import { useConfirm } from "@/components/ConfirmProvider";

type OAuthClient = {
  id: string;
  name: string;
  client_id: string;
  redirect_uris: string[];
  enabled: boolean;
  requires_consent: boolean;
  created_at: string;
};
type Discovery = { issuer: string };
const DISCOVERY = "/.well-known/openid-configuration";

/** One address per line; blank lines dropped. The server checks each one (https or localhost, exact match). */
export function parseUris(text: string): string[] {
  return text
    .split(/\r?\n/)
    .map((s) => s.trim())
    .filter(Boolean);
}

export default function AuthClient({ orgId }: { orgId: string }) {
  const confirm = useConfirm();
  const queryClient = useQueryClient();
  const [createOpen, setCreateOpen] = useState(false);
  const [secret, setSecret] = useState<{ title: string; value: string } | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const org = useQuery({ queryKey: ["org", orgId], queryFn: () => api.get<Organization>(`/organizations/${orgId}/`) });
  const clients = useQuery({
    queryKey: ["oauth-clients"],
    queryFn: () => api.get<OAuthClient[]>("/oauth-clients/"),
    retry: (count, err) => !(err instanceof ApiError && err.status === 403) && count < 2,
  });
  const discovery = useQuery({
    queryKey: ["oidc-discovery"],
    queryFn: async () => {
      const res = await fetch(DISCOVERY, { credentials: "omit" });
      if (!res.ok) throw new Error(String(res.status));
      return (await res.json()) as Discovery;
    },
  });
  const refresh = () => queryClient.invalidateQueries({ queryKey: ["oauth-clients"] });

  async function setEnabled(c: OAuthClient, enabled: boolean) {
    if (!enabled) {
      const ok = await confirm({
        title: `Turn off sign-in for "${c.name}"?`,
        description: "Nobody can sign in to it with IntraForge until it is turned on again.",
        confirmLabel: "Turn off",
        danger: true,
      });
      if (!ok) return;
    }
    setActionError(null);
    try {
      await api.patch(`/oauth-clients/${c.id}/`, { enabled });
      await refresh();
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : "The change could not be saved.");
    }
  }

  async function rotate(c: OAuthClient) {
    const ok = await confirm({
      title: `Make a new secret for "${c.name}"?`,
      description: "The old secret stops working at once; put the new one into that application straight away.",
      confirmLabel: "New secret",
      danger: true,
    });
    if (!ok) return;
    setActionError(null);
    try {
      const res = await api.post<{ client_secret: string }>(`/oauth-clients/${c.id}/rotate-secret/`);
      setSecret({ title: `New secret for ${c.name}`, value: res.client_secret });
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : "The secret could not be changed.");
    }
  }

  if (clients.isLoading) return <PageLoading />;
  const orgName = org.data?.name ?? "Organization";
  const notAdmin = clients.error instanceof ApiError && clients.error.status === 403;
  const list = clients.data ?? [];

  return (
    <div>
      <PageHeader
        title="Auth"
        description='"Sign in with IntraForge" for other software: your people use their IntraForge account (with its two-step check) to sign in to another application instead of a separate password.'
        breadcrumbs={[
          { label: "Organizations", href: "/orgs" },
          { label: orgName, href: `/orgs/${orgId}` },
          { label: "Developer", href: `/orgs/${orgId}/developer` },
          { label: "Auth" },
        ]}
      />
      <DeveloperNav orgId={orgId} active="auth" />

      <Card className="mb-6">
        <h2 className="mb-2 text-sm font-semibold text-slate-700">For the application&apos;s developer</h2>
        <p className="mb-3 text-sm text-slate-600">
          Standard OpenID Connect (authorization code flow). Give the developer the discovery address and, from a sign-in
          client below, its client ID and secret.
        </p>
        {discovery.data ? (
          <dl className="grid grid-cols-1 gap-2 text-sm sm:grid-cols-[10rem_1fr]">
            <dt className="text-slate-500">Discovery</dt>
            <dd className="flex items-center gap-2 break-all font-mono text-xs">
              {discovery.data.issuer + DISCOVERY} <CopyButton value={discovery.data.issuer + DISCOVERY} />
            </dd>
            <dt className="text-slate-500">Issuer</dt>
            <dd className="break-all font-mono text-xs">{discovery.data.issuer}</dd>
          </dl>
        ) : (
          <p className="text-sm text-slate-500">{discovery.isError ? "The discovery address could not be read." : "Loading…"}</p>
        )}
        <p className="mt-3 text-xs text-text-muted">
          This signs in people who have an IntraForge account (your staff). Customers without an account, such as a
          website&apos;s visitors, are not covered.
        </p>
      </Card>

      {notAdmin ? (
        <EmptyState
          title="Only the Super Administrator manages sign-in clients"
          description="A sign-in client can sign in anyone on this installation, so it belongs to the whole installation, not one organization. Ask the Super Administrator to register the application."
        />
      ) : (
        <>
          {(clients.isError || actionError) && (
            <div className="mb-4">
              <ErrorBanner message={actionError ?? "The sign-in clients could not be loaded."} error={clients.error} />
            </div>
          )}
          {secret && (
            <div className="mb-4">
              <SecretReveal label={secret.title} secret={secret.value} />
            </div>
          )}
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-slate-600">Sign-in clients (whole installation)</h2>
            <Button size="sm" onClick={() => setCreateOpen(true)}>
              New sign-in client
            </Button>
          </div>
          {list.length === 0 ? (
            <EmptyState
              title="No sign-in clients yet"
              description="Register the application that should offer “Sign in with IntraForge”."
            />
          ) : (
            <Table>
              <THead>
                <Th>Application</Th>
                <Th>Client ID</Th>
                <Th>Return addresses</Th>
                <Th>Asks people first</Th>
                <Th>Status</Th>
                <Th>
                  <span className="sr-only">Actions</span>
                </Th>
              </THead>
              <tbody>
                {list.map((c) => (
                  <TRow key={c.id}>
                    <Td className="font-medium">{c.name}</Td>
                    <Td>
                      <span className="inline-flex items-center gap-1 font-mono text-xs">
                        {c.client_id} <CopyButton value={c.client_id} />
                      </span>
                    </Td>
                    <Td className="break-all font-mono text-xs text-text-muted">{c.redirect_uris.join(", ")}</Td>
                    <Td>{c.requires_consent ? <Badge tone="success">Yes</Badge> : <Badge>No (IntraForge&apos;s own)</Badge>}</Td>
                    <Td>{c.enabled ? <Badge tone="success">On</Badge> : <Badge tone="warning">Off</Badge>}</Td>
                    <Td>
                      <div className="flex justify-end gap-3 text-xs">
                        <button onClick={() => rotate(c)} className="text-brand-600 hover:text-brand-500">
                          New secret
                        </button>
                        <button
                          onClick={() => setEnabled(c, !c.enabled)}
                          className={c.enabled ? "text-red-600 hover:text-red-500" : "text-brand-600 hover:text-brand-500"}
                        >
                          {c.enabled ? "Turn off" : "Turn on"}
                        </button>
                      </div>
                    </Td>
                  </TRow>
                ))}
              </tbody>
            </Table>
          )}
        </>
      )}
      <CreateClientModal
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        onCreated={async (name, value) => {
          setCreateOpen(false);
          setSecret({ title: `Secret for ${name}`, value });
          await refresh();
        }}
      />
    </div>
  );
}

function CreateClientModal({
  open,
  onClose,
  onCreated,
}: {
  open: boolean;
  onClose: () => void;
  onCreated: (name: string, secret: string) => void;
}) {
  const [name, setName] = useState("");
  const [uris, setUris] = useState("");
  const [consent, setConsent] = useState(true);
  const [error, setError] = useState<unknown>(null);
  const [submitting, setSubmitting] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const created = await api.post<OAuthClient & { client_secret: string }>("/oauth-clients/", {
        name: name.trim(),
        redirect_uris: parseUris(uris),
        requires_consent: consent,
      });
      setName("");
      setUris("");
      setConsent(true);
      onCreated(created.name, created.client_secret);
    } catch (err) {
      setError(err);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Modal open={open} onClose={onClose} title="New sign-in client">
      <form onSubmit={submit} className="space-y-4">
        {Boolean(error) && (
          <ErrorBanner message={error instanceof ApiError ? error.message : "The client could not be created."} error={error} />
        )}
        <div>
          <Label htmlFor="oauth-name">Application name</Label>
          <Input
            id="oauth-name"
            required
            maxLength={200}
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Accounting system"
          />
        </div>
        <div>
          <Label htmlFor="oauth-uris">Return addresses (one per line)</Label>
          <Textarea
            id="oauth-uris"
            required
            rows={3}
            value={uris}
            onChange={(e) => setUris(e.target.value)}
            placeholder="https://accounting.example.com/auth/callback"
          />
          <p className="mt-1 text-xs text-text-muted">Where IntraForge sends people back after signing in. Must match exactly.</p>
        </div>
        <label className="flex items-start gap-2 text-sm text-slate-700">
          <input type="checkbox" className="mt-1" checked={consent} onChange={(e) => setConsent(e.target.checked)} />
          <span>
            Ask each person before sharing their name and email with it
            <span className="block text-xs text-text-muted">Untick only for IntraForge&apos;s own applications.</span>
          </span>
        </label>
        <div className="flex justify-end gap-2">
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" disabled={submitting}>
            {submitting ? "Creating…" : "Create"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
