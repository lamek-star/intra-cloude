"use client";

import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";
import Link from "next/link";
import { ExternalLink, Globe, Server } from "lucide-react";
import { api, ApiError, ensureCsrfCookie, type Organization } from "@/lib/api";
import { formatBytes, runtimeLabel, siteAddress, suggestSlug, type InternetGateway, type Site } from "@/lib/sites";
import {
  Badge,
  Button,
  Card,
  Checkbox,
  CopyButton,
  EmptyState,
  ErrorBanner,
  Input,
  Label,
  Modal,
  PageHeader,
  PageLoading,
  Spinner,
} from "@/components/ui";
import { useConfirm } from "@/components/ConfirmProvider";

/** Organization › Websites (ADR-0019, ADR-0020): finished websites and Node.js apps uploaded as a zip, each
 * served by the proxy on its own port, with every upload kept as a version to switch back to. */
export default function SitesClient({ orgId }: { orgId: string }) {
  const [org, setOrg] = useState<Organization | null>(null);
  const [sites, setSites] = useState<Site[] | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [creating, setCreating] = useState(false);
  const [refused, setRefused] = useState(false);
  const [gate, setGate] = useState<InternetGateway | null>(null);

  const load = useCallback(async () => {
    try {
      const [o, s] = await Promise.all([
        api.get<Organization>(`/organizations/${orgId}/`),
        api.get<Site[]>(`/organizations/${orgId}/sites/`),
      ]);
      setOrg(o);
      setSites(s);
      api.get<InternetGateway>("/internet-gateway/").then(setGate).catch(() => {});
    } catch (err) {
      if (err instanceof ApiError && err.status === 403) {
        setRefused(true);
        setSites([]);
        return;
      }
      setError(err);
      setSites([]);
    }
  }, [orgId]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- one fetch per organization
    void load();
  }, [load]);

  if (sites === null) return <PageLoading />;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Websites"
        description="Publish a finished website by uploading it as a zip. Anyone who can reach this PC opens it in a browser."
        breadcrumbs={[
          { label: "Organizations", href: "/orgs" },
          { label: org?.name ?? "Organization", href: `/orgs/${orgId}` },
          { label: "Websites" },
        ]}
        actions={!refused && <Button onClick={() => setCreating(true)}>New website</Button>}
      />

      {error != null && <ErrorBanner message={error instanceof ApiError ? error.message : "Could not load the websites."} error={error} />}

      {refused ? (
        <EmptyState
          title="You can't see this organization's websites"
          description="Seeing websites needs the sites.read permission; publishing them needs sites.manage."
        />
      ) : sites.length === 0 ? (
        <EmptyState
          title="No websites yet"
          description="Upload a zip of a finished website, or of a Node.js app, to put it online on this PC."
          action={<Button onClick={() => setCreating(true)}>New website</Button>}
        />
      ) : (
        <div className="space-y-4">
          {sites.map((site) => (
            <SiteCard key={site.id} site={site} onChanged={load} />
          ))}
        </div>
      )}

      {gate && (
        <p className="text-xs text-text-muted">
          Internet access is {gate.enabled ? "on" : "off"}: {gate.enabled ? "published websites are reachable from the internet" : "websites are reachable only from this PC and the shop network"}.{" "}
          {gate.can_manage && (
            <Link href="/internet" className="text-brand-600 hover:underline">
              Manage internet access
            </Link>
          )}
        </p>
      )}

      <PublishingHelp />

      {creating && (
        <NewSiteModal
          orgId={orgId}
          onClose={() => setCreating(false)}
          onCreated={async () => {
            setCreating(false);
            await load();
          }}
        />
      )}
    </div>
  );
}

function SiteCard({ site, onChanged }: { site: Site; onChanged: () => Promise<void> }) {
  const confirm = useConfirm();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [dialog, setDialog] = useState<"versions" | "name" | null>(null);
  const uploadRef = useRef<HTMLInputElement>(null);
  const host = typeof window === "undefined" ? "localhost" : window.location.hostname;
  const address = siteAddress(site, host);
  const online = site.status === "active";
  const runtime = runtimeLabel(site);
  const version = site.active_version;

  async function run(action: () => Promise<unknown>) {
    setBusy(true);
    setError(null);
    try {
      await ensureCsrfCookie();
      await action();
      await onChanged();
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  async function uploadVersion(files: FileList | null) {
    const file = files?.[0];
    if (!file) return;
    const form = new FormData();
    form.append("file", file);
    form.append("activate", "true");
    await run(() => api.postForm(`/sites/${site.id}/versions/`, form));
    if (uploadRef.current) uploadRef.current.value = "";
  }

  async function remove() {
    const ok = await confirm({
      title: `Delete "${site.name}"?`,
      description: `${site.name} goes offline and every version of it is deleted. This cannot be undone.`,
      confirmLabel: "Delete",
      danger: true,
    });
    if (ok) await run(() => api.del(`/sites/${site.id}/`));
  }

  return (
    <Card className="space-y-3">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex min-w-0 items-start gap-3">
          {site.kind === "node" ? (
            <Server aria-hidden="true" className="mt-0.5 h-5 w-5 shrink-0 text-brand-600" />
          ) : (
            <Globe aria-hidden="true" className="mt-0.5 h-5 w-5 shrink-0 text-brand-600" />
          )}
          <div className="min-w-0">
            <h2 className="truncate text-sm font-semibold text-text-primary">{site.name}</h2>
            <p className="truncate font-mono text-xs text-text-muted">{address}</p>
            {site.internet_hostname && (
              <p className="truncate font-mono text-xs text-text-muted">On the internet: https://{site.internet_hostname}/</p>
            )}
          </div>
        </div>
        <div className="flex flex-wrap gap-1.5">
          <Badge tone={online ? "success" : "default"}>{online ? "Online" : "Offline"}</Badge>
          {site.kind === "node" && <Badge tone="info">Node.js app</Badge>}
          {runtime && <Badge tone={site.runtime_state === "failed" ? "danger" : "default"}>{runtime}</Badge>}
        </div>
      </div>

      {version && (
        <p className="text-xs text-text-muted">
          Version {version.number} · {version.file_count} files · {formatBytes(version.total_bytes)}
          {version.uploaded_by_email && ` · by ${version.uploaded_by_email}`} · {new Date(version.created_at).toLocaleString()}
        </p>
      )}

      {site.kind === "node" && site.runtime_state === "failed" && site.runtime_log && (
        <details className="text-xs">
          <summary className="cursor-pointer text-danger-fg">Why it did not start</summary>
          <pre className="mt-1 max-h-48 overflow-auto rounded-md bg-surface-sunken p-2 font-mono whitespace-pre-wrap text-text-body">
            {site.runtime_log}
          </pre>
        </details>
      )}

      {error != null && <ErrorBanner message={error instanceof ApiError ? error.message : "That did not work."} error={error} />}

      <div className="flex flex-wrap items-center gap-2">
        {online && (
          <a
            href={address}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-1.5 rounded-lg bg-brand-600 px-2.5 py-1.5 text-xs font-medium text-white hover:bg-accent-hover"
          >
            <ExternalLink aria-hidden="true" className="h-3.5 w-3.5" />
            Open
          </a>
        )}
        <CopyButton value={address} label="Copy address" />
        <input
          ref={uploadRef}
          type="file"
          accept=".zip,application/zip"
          className="hidden"
          aria-label={`Zip for a new version of ${site.name}`}
          onChange={(e) => void uploadVersion(e.target.files)}
        />
        <Button size="sm" variant="secondary" disabled={busy} onClick={() => uploadRef.current?.click()}>
          {busy && <Spinner className="h-3.5 w-3.5" />}
          Upload new version
        </Button>
        <Button size="sm" variant="secondary" disabled={busy} onClick={() => setDialog("name")}>
          {site.hostname ? "Change its name" : "Give it a name"}
        </Button>
        <Button size="sm" variant="secondary" disabled={busy} onClick={() => setDialog("versions")}>
          Versions
        </Button>
        {site.application && (
          <Link href={`/applications/${site.application}`} className="text-xs text-brand-600 hover:underline">
            Its application (data, files and Pay access)
          </Link>
        )}
        <span className="flex-1" />
        <Button
          size="sm"
          variant="ghost"
          disabled={busy}
          onClick={() => void run(() => api.patch(`/sites/${site.id}/`, { status: online ? "disabled" : "active" }))}
        >
          {online ? "Take offline" : "Bring online"}
        </Button>
        <Button size="sm" variant="danger" disabled={busy} onClick={() => void remove()}>
          Delete
        </Button>
      </div>

      {dialog === "versions" && <VersionsModal site={site} onClose={() => setDialog(null)} onChanged={onChanged} />}
      {dialog === "name" && <NameModal site={site} onClose={() => setDialog(null)} onChanged={onChanged} />}
    </Card>
  );
}

function NewSiteModal({ orgId, onClose, onCreated }: { orgId: string; onClose: () => void; onCreated: () => Promise<void> }) {
  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [slugTouched, setSlugTouched] = useState(false);
  const [spa, setSpa] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (!file) return;
    setBusy(true);
    setError(null);
    try {
      await ensureCsrfCookie();
      const form = new FormData();
      form.append("name", name.trim());
      form.append("slug", slug.trim());
      form.append("single_page_app", spa ? "true" : "false");
      form.append("file", file);
      await api.postForm(`/organizations/${orgId}/sites/`, form);
      await onCreated();
    } catch (err) {
      setError(err);
      setBusy(false);
    }
  }

  return (
    <Modal open onClose={onClose} title="New website">
      <form onSubmit={submit} className="space-y-4">
        {error != null && <ErrorBanner message={error instanceof ApiError ? error.message : "The website could not be published."} error={error} />}
        <div>
          <Label htmlFor="site-name">Name</Label>
          <Input
            id="site-name"
            required
            maxLength={120}
            value={name}
            onChange={(e) => {
              setName(e.target.value);
              if (!slugTouched) setSlug(suggestSlug(e.target.value));
            }}
            placeholder="Shop price list"
          />
        </div>
        <div>
          <Label htmlFor="site-slug">Address</Label>
          <Input
            id="site-slug"
            required
            maxLength={50}
            pattern="[a-z0-9]([a-z0-9-]*[a-z0-9])?"
            value={slug}
            onChange={(e) => {
              setSlugTouched(true);
              setSlug(e.target.value.toLowerCase());
            }}
            placeholder="price-list"
          />
          <p className="mt-1 text-xs text-text-muted">Lowercase letters, digits and hyphens. The site opens at …/{slug || "address"}/.</p>
        </div>
        <div>
          <Label htmlFor="site-zip">Zip of the finished site</Label>
          <Input id="site-zip" type="file" required accept=".zip,application/zip" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
        </div>
        <label className="flex items-start gap-2 text-sm text-slate-600">
          <Checkbox checked={spa} onChange={(e) => setSpa(e.target.checked)} />
          <span>
            Single-page app: unknown paths open index.html (for sites built with React, Vue and similar).
          </span>
        </label>
        <div className="flex justify-end gap-2">
          <Button type="button" variant="ghost" onClick={onClose} disabled={busy}>
            Cancel
          </Button>
          <Button type="submit" disabled={busy || !file || !name.trim() || !slug.trim()}>
            {busy && <Spinner className="h-4 w-4" />}
            Publish
          </Button>
        </div>
      </form>
    </Modal>
  );
}

function VersionsModal({ site, onClose, onChanged }: { site: Site; onClose: () => void; onChanged: () => Promise<void> }) {
  const confirm = useConfirm();
  const [detail, setDetail] = useState<Site | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      setDetail(await api.get<Site>(`/sites/${site.id}/`));
    } catch (err) {
      setError(err);
    }
  }, [site.id]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- one fetch per open dialog
    void load();
  }, [load]);

  async function act(action: () => Promise<unknown>) {
    setBusy(true);
    setError(null);
    try {
      await ensureCsrfCookie();
      await action();
      await Promise.all([load(), onChanged()]);
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  const activeId = detail?.active_version?.id;

  return (
    <Modal open onClose={onClose} title={`Versions of ${site.name}`}>
      <div className="space-y-3">
        {error != null && <ErrorBanner message={error instanceof ApiError ? error.message : "That did not work."} error={error} />}
        {!detail && !error && (
          <div className="flex justify-center py-4 text-text-muted">
            <Spinner className="h-5 w-5" />
          </div>
        )}
        {detail?.versions?.length === 0 && <p className="text-sm text-text-muted">No versions.</p>}
        <ul className="divide-y divide-border-subtle">
          {detail?.versions?.map((v) => (
            <li key={v.id} className="flex flex-wrap items-center justify-between gap-2 py-2 text-sm">
              <div>
                <span className="font-medium text-text-primary">Version {v.number}</span>
                {v.id === activeId && (
                  <span className="ml-2">
                    <Badge tone="success">In use</Badge>
                  </span>
                )}
                <p className="text-xs text-text-muted">
                  {v.file_count} files · {formatBytes(v.total_bytes)} · {v.uploaded_by_email || "unknown"} ·{" "}
                  {new Date(v.created_at).toLocaleString()}
                </p>
              </div>
              {v.id !== activeId && (
                <div className="flex gap-2">
                  <Button
                    size="sm"
                    variant="secondary"
                    disabled={busy}
                    onClick={() => void act(() => api.post(`/sites/${site.id}/versions/${v.id}/activate/`))}
                  >
                    Switch to this version
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    disabled={busy}
                    onClick={async () => {
                      const ok = await confirm({
                        title: `Delete version ${v.number}?`,
                        description: "Its files are removed. The version in use is not affected.",
                        confirmLabel: "Delete",
                        danger: true,
                      });
                      if (ok) await act(() => api.del(`/sites/${site.id}/versions/${v.id}/`));
                    }}
                  >
                    Delete
                  </Button>
                </div>
              )}
            </li>
          ))}
        </ul>
        <div className="flex justify-end">
          <Button variant="ghost" onClick={onClose}>
            Close
          </Button>
        </div>
      </div>
    </Modal>
  );
}

function NameModal({ site, onClose, onChanged }: { site: Site; onClose: () => void; onChanged: () => Promise<void> }) {
  const [hostname, setHostname] = useState(site.hostname ?? "");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);

  async function save(value: string) {
    setBusy(true);
    setError(null);
    try {
      await ensureCsrfCookie();
      await api.patch(`/sites/${site.id}/`, { hostname: value });
      await onChanged();
      onClose();
    } catch (err) {
      setError(err);
      setBusy(false);
    }
  }

  return (
    <Modal open onClose={onClose} title={`A name for ${site.name}`}>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          void save(hostname.trim().toLowerCase());
        }}
        className="space-y-4"
      >
        {error != null && <ErrorBanner message={error instanceof ApiError ? error.message : "The name could not be saved."} error={error} />}
        <div>
          <Label htmlFor="site-hostname">Name on the shop network</Label>
          <Input
            id="site-hostname"
            value={hostname}
            onChange={(e) => setHostname(e.target.value)}
            placeholder="myshop.lan"
          />
          <p className="mt-1 text-xs text-text-muted">
            The site then opens at https://{hostname || "myshop.lan"}:{site.public_port}/.{" "}
            {site.lan_address
              ? `On the shop's other PCs, point the name to ${site.lan_address} (hosts file or router).`
              : "Switch the shop network on first for other PCs and phones to use it."}
          </p>
        </div>
        <div className="flex justify-end gap-2">
          {site.hostname && (
            <Button type="button" variant="ghost" disabled={busy} onClick={() => void save("")}>
              Remove the name
            </Button>
          )}
          <Button type="button" variant="ghost" onClick={onClose} disabled={busy}>
            Cancel
          </Button>
          <Button type="submit" disabled={busy || !hostname.trim()}>
            Save
          </Button>
        </div>
      </form>
    </Modal>
  );
}

function PublishingHelp() {
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Card className="space-y-2 text-sm text-slate-600">
        <h2 className="text-sm font-semibold text-text-primary">How to publish a website</h2>
        <ol className="list-decimal space-y-1 pl-5">
          <li>Put the finished site in one folder, with the first page named index.html.</li>
          <li>
            Zip that folder (right-click › Send to › Compressed folder). A single top folder such as public_html or dist
            is removed automatically.
          </li>
          <li>Click New website, give it a name and an address, and choose the zip.</li>
          <li>To change the site later, upload a new zip on its card. The previous version is kept, so you can switch back.</li>
        </ol>
        <p className="text-xs text-text-muted">
          Websites run in a protected space: they cannot use browser cookies or local storage, and they can never act as a
          signed-in IntraForge user. Other PCs and phones open them when the shop network is switched on.
        </p>
      </Card>
      <Card className="space-y-2 text-sm text-slate-600">
        <h2 className="text-sm font-semibold text-text-primary">How to publish a Node.js app</h2>
        <ol className="list-decimal space-y-1 pl-5">
          <li>
            Add <code className="font-mono text-xs">intraforge.json</code> at the top of the app:{" "}
            <code className="font-mono text-xs">{'{"runtime": "node", "entry": "server.js"}'}</code>. The app must listen
            on the port in <code className="font-mono text-xs">PORT</code>.
          </li>
          <li>
            Run <code className="font-mono text-xs">npm ci --omit=dev</code> so node_modules is in the folder: the app has
            no internet, nothing is installed for it.
          </li>
          <li>
            Zip the folder and publish it like a website. It runs in its own locked container and is served at its address
            with the address removed from the path (<code className="font-mono text-xs">IF_BASE_PATH</code> tells it its
            prefix).
          </li>
          <li>
            For IntraForge data, files and Pay, share them with the app&apos;s application (link on its card). The app calls{" "}
            <code className="font-mono text-xs">IF_API_URL</code> with the bearer token in{" "}
            <code className="font-mono text-xs">IF_API_TOKEN</code>.
          </li>
        </ol>
      </Card>
    </div>
  );
}
