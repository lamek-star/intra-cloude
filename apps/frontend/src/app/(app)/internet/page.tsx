"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";
import { Globe2, ShieldAlert } from "lucide-react";
import { api, ApiError, ensureCsrfCookie, type Organization } from "@/lib/api";
import type { InternetGateway, Site } from "@/lib/sites";
import { Badge, Button, Card, EmptyState, ErrorBanner, Input, Label, PageHeader, PageLoading, Select } from "@/components/ui";
import { useConfirm } from "@/components/ConfirmProvider";

/** Internet access (ADR-0020 decision 4): off by default. Only the Super Administrator, with password and
 * two-step sign-in, switches the Cloudflare Tunnel on and publishes sites one by one under a public name.
 * IntraForge itself is never published. */
export default function InternetPage() {
  const confirm = useConfirm();
  const [gate, setGate] = useState<InternetGateway | null>(null);
  const [sites, setSites] = useState<(Site & { orgName: string })[]>([]);
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      const g = await api.get<InternetGateway>("/internet-gateway/");
      setGate(g);
      if (g.can_manage) {
        const orgs = await api.get<Organization[]>("/organizations/");
        const lists = await Promise.all(
          orgs.map((o) =>
            api
              .get<Site[]>(`/organizations/${o.id}/sites/`)
              .then((list) => list.map((s) => ({ ...s, orgName: o.name })))
              .catch(() => []),
          ),
        );
        setSites(lists.flat());
      }
    } catch (err) {
      setError(err);
    }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- one fetch on open
    void load();
  }, [load]);

  async function act(action: () => Promise<unknown>) {
    setBusy(true);
    setError(null);
    try {
      await ensureCsrfCookie();
      await action();
      await load();
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  if (!gate && !error) return <PageLoading />;

  return (
    <div className="max-w-3xl space-y-6">
      <PageHeader
        title="Internet access"
        description="Off by default. When it is on, chosen websites are reachable from the internet through a Cloudflare Tunnel. IntraForge itself is never published."
      />
      {error != null && <ErrorBanner message={error instanceof ApiError ? error.message : "That did not work."} error={error} />}

      {gate && !gate.can_manage && (
        <Card className="flex items-start gap-3">
          <ShieldAlert aria-hidden="true" className="mt-0.5 h-5 w-5 text-text-muted" />
          <p className="text-sm text-slate-600">
            Internet access is <strong>{gate.enabled ? "on" : "off"}</strong>. Only the Super Administrator can switch it
            or publish a website.
          </p>
        </Card>
      )}

      {gate?.can_manage && (
        <>
          <Card className="space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="flex items-center gap-3">
                <Globe2 aria-hidden="true" className="h-5 w-5 text-brand-600" />
                <h2 className="text-sm font-semibold text-text-primary">The internet gate</h2>
              </div>
              <div className="flex gap-1.5">
                <Badge tone={gate.enabled ? "warning" : "default"}>{gate.enabled ? "On" : "Off"}</Badge>
                {gate.enabled && gate.tunnel && <Badge tone={gate.tunnel.state === "running" ? "success" : "danger"}>Tunnel: {gate.tunnel.state}</Badge>}
              </div>
            </div>
            {gate.changed_at && <p className="text-xs text-text-muted">Last changed {new Date(gate.changed_at).toLocaleString()}.</p>}
            {gate.enabled && gate.tunnel?.log && (
              <pre className="max-h-40 overflow-auto rounded-md bg-surface-sunken p-2 font-mono text-xs whitespace-pre-wrap text-text-body">
                {gate.tunnel.log}
              </pre>
            )}
            {gate.enabled ? (
              <Button
                variant="danger"
                disabled={busy}
                onClick={async () => {
                  const ok = await confirm({
                    title: "Switch internet access off?",
                    description: "The tunnel stops and every published website loses its public name at once.",
                    confirmLabel: "Switch off",
                    danger: true,
                  });
                  if (ok) await act(() => api.post("/internet-gateway/disable/"));
                }}
              >
                Switch off (revoke all)
              </Button>
            ) : (
              <EnableForm busy={busy} onEnable={(token, password) => act(() => api.post("/internet-gateway/enable/", { token, password }))} />
            )}
          </Card>

          <Card className="space-y-3">
            <h2 className="text-sm font-semibold text-text-primary">Published websites</h2>
            {(gate.published?.length ?? 0) === 0 ? (
              <p className="text-sm text-text-muted">Nothing is published.</p>
            ) : (
              <ul className="divide-y divide-border-subtle">
                {gate.published!.map((p) => (
                  <li key={p.site} className="flex flex-wrap items-center justify-between gap-2 py-2 text-sm">
                    <div>
                      <span className="font-medium text-text-primary">{p.name}</span>{" "}
                      <span className="text-text-muted">({p.organization})</span>
                      <p className="font-mono text-xs text-text-muted">https://{p.internet_hostname}/</p>
                    </div>
                    <Button
                      size="sm"
                      variant="ghost"
                      disabled={busy}
                      onClick={() => void act(() => api.del(`/sites/${p.site}/internet/`))}
                    >
                      Revoke
                    </Button>
                  </li>
                ))}
              </ul>
            )}
            {gate.enabled && <PublishForm sites={sites} busy={busy} onPublish={(id, name) => act(() => api.post(`/sites/${id}/internet/`, { hostname: name }))} />}
          </Card>
        </>
      )}
      {gate?.can_manage && sites.length === 0 && (
        <EmptyState title="No websites to publish" description="Publish a website under an organization's Websites first." />
      )}
    </div>
  );
}

function EnableForm({ busy, onEnable }: { busy: boolean; onEnable: (token: string, password: string) => Promise<void> }) {
  const [token, setToken] = useState("");
  const [password, setPassword] = useState("");
  return (
    <form
      className="space-y-3"
      onSubmit={(e: FormEvent) => {
        e.preventDefault();
        void onEnable(token.trim(), password).then(() => setPassword(""));
      }}
    >
      <p className="text-sm text-slate-600">
        Needs two-step sign-in on your account. The token comes from Cloudflare (Zero Trust › Networks › Tunnels › your
        tunnel) and is stored encrypted.
      </p>
      <div>
        <Label htmlFor="tunnel-token">Tunnel token</Label>
        <Input id="tunnel-token" required autoComplete="off" value={token} onChange={(e) => setToken(e.target.value)} />
      </div>
      <div>
        <Label htmlFor="gate-password">Your IntraForge password</Label>
        <Input
          id="gate-password"
          type="password"
          required
          autoComplete="current-password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
      </div>
      <Button type="submit" disabled={busy || !token.trim() || !password}>
        Switch on
      </Button>
    </form>
  );
}

function PublishForm({
  sites,
  busy,
  onPublish,
}: {
  sites: (Site & { orgName: string })[];
  busy: boolean;
  onPublish: (siteId: string, hostname: string) => Promise<void>;
}) {
  const candidates = sites.filter((s) => s.status === "active" && !s.internet_hostname);
  const [siteId, setSiteId] = useState("");
  const [name, setName] = useState("");
  if (candidates.length === 0) return null;
  return (
    <form
      className="grid gap-3 border-t border-border-subtle pt-3 sm:grid-cols-[1fr_1fr_auto] sm:items-end"
      onSubmit={(e: FormEvent) => {
        e.preventDefault();
        void onPublish(siteId || candidates[0].id, name.trim().toLowerCase()).then(() => setName(""));
      }}
    >
      <div>
        <Label htmlFor="publish-site">Website</Label>
        <Select id="publish-site" value={siteId || candidates[0].id} onChange={(e) => setSiteId(e.target.value)}>
          {candidates.map((s) => (
            <option key={s.id} value={s.id}>
              {s.name} ({s.orgName})
            </option>
          ))}
        </Select>
      </div>
      <div>
        <Label htmlFor="publish-name">Public name</Label>
        <Input id="publish-name" required placeholder="www.myshop.com" value={name} onChange={(e) => setName(e.target.value)} />
      </div>
      <Button type="submit" disabled={busy || !name.trim()}>
        Publish
      </Button>
    </form>
  );
}
