"use client";

import { useCallback, useEffect, useId, useState } from "react";
import { ExternalLink, Package, Settings } from "lucide-react";
import { api, ApiError, type Organization } from "@/lib/api";
import {
  openServiceApp,
  STATE_HELP,
  STATE_LABEL,
  STATE_TONE,
  type InstallableApp,
  type ServiceApp,
  type ServiceAppList,
} from "@/lib/service-apps";
import {
  Badge,
  Button,
  Card,
  EmptyState,
  ErrorBanner,
  Input,
  Label,
  LinkButton,
  Modal,
  PageHeader,
  PageLoading,
  Select,
  Spinner,
} from "@/components/ui";

function openError(err: unknown): string {
  if (err instanceof ApiError) {
    if (err.status === 403) return "You don't have access to open this application. Ask an administrator.";
    if (err.status === 404) return "This application is no longer available.";
    return err.message;
  }
  return "The application could not be opened. Please try again.";
}

export default function AppsClient() {
  const [data, setData] = useState<ServiceAppList | null>(null);
  const [orgs, setOrgs] = useState<Organization[]>([]);
  const [error, setError] = useState<unknown>(null);
  const [opening, setOpening] = useState<string | null>(null);
  const [openErr, setOpenErr] = useState<string | null>(null);
  const [installing, setInstalling] = useState<InstallableApp | null>(null);

  const load = useCallback(async () => {
    try {
      const [list, organizations] = await Promise.all([
        api.get<ServiceAppList>("/service-apps/"),
        api.get<Organization[]>("/organizations/"),
      ]);
      setData(list);
      setOrgs(organizations);
      setError(null);
    } catch (err) {
      setError(err);
    }
  }, []);
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [list, organizations] = await Promise.all([
          api.get<ServiceAppList>("/service-apps/"),
          api.get<Organization[]>("/organizations/"),
        ]);
        if (cancelled) return;
        setData(list);
        setOrgs(organizations);
      } catch (err) {
        if (!cancelled) setError(err);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  async function open(app: ServiceApp) {
    setOpening(app.id);
    setOpenErr(null);
    try {
      await openServiceApp(app.id);
    } catch (err) {
      setOpenErr(openError(err));
      setOpening(null);
    }
  }

  if (error && !data) return <ErrorBanner message="The applications could not be loaded." error={error} />;
  if (!data) return <PageLoading />;

  const installed = data.results;
  return (
    <div>
      <PageHeader
        title="Apps"
        description="Applications installed in your organizations. Open one to work in it with your IntraForge sign-in."
      />
      {openErr && <ErrorBanner message={openErr} />}

      <section aria-labelledby="installed-heading" className="mb-8">
        <h2 id="installed-heading" className="mb-3 text-sm font-semibold text-slate-900">
          Installed applications
        </h2>
        {installed.length === 0 ? (
          <EmptyState
            title="No applications yet"
            description={
              data.available.length
                ? "Install one below to get started."
                : "Ask an administrator to install an application for your organization."
            }
          />
        ) : (
          <ul className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {installed.map((app) => {
              const state = app.health?.state ?? "stopped";
              const openable = app.can_open && (state === "running" || state === "degraded");
              return (
                <li key={app.id}>
                  <Card className="flex h-full flex-col gap-3">
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <h3 className="truncate text-base font-semibold text-slate-900">{app.display_name}</h3>
                        <p className="text-sm text-slate-500">
                          {app.name}
                          {orgs.length > 1 ? ` · ${app.organization.name}` : ""}
                        </p>
                      </div>
                      <Badge tone={STATE_TONE[state]}>{STATE_LABEL[state]}</Badge>
                    </div>
                    {STATE_HELP[state] && <p className="text-xs text-slate-500">{STATE_HELP[state]}</p>}
                    {app.version && <p className="text-xs text-text-muted">Version {app.version}</p>}
                    <div className="mt-auto flex flex-wrap gap-2 pt-1">
                      {app.can_open && (
                        <Button onClick={() => open(app)} disabled={!openable || opening === app.id}>
                          {opening === app.id ? <Spinner className="h-4 w-4" /> : <ExternalLink className="h-4 w-4" />}
                          Open
                        </Button>
                      )}
                      {(app.can_configure || app.can_manage) && (
                        <LinkButton href={`/service-apps/${app.id}/settings`}>
                          <Settings className="h-4 w-4" />
                          Settings
                        </LinkButton>
                      )}
                    </div>
                  </Card>
                </li>
              );
            })}
          </ul>
        )}
      </section>

      {data.available.length > 0 && (
        <section aria-labelledby="available-heading">
          <h2 id="available-heading" className="mb-3 text-sm font-semibold text-slate-900">
            Available to install
          </h2>
          <ul className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {data.available.map((a) => (
              <li key={a.deployment}>
                <Card className="flex h-full flex-col gap-3">
                  <div className="flex items-center gap-2">
                    <Package className="h-5 w-5 text-brand-600" aria-hidden="true" />
                    <h3 className="text-base font-semibold text-slate-900">{a.product_name}</h3>
                  </div>
                  <p className="text-sm text-slate-500">{a.description}</p>
                  <div className="mt-auto">
                    <Button onClick={() => setInstalling(a)}>Install</Button>
                  </div>
                </Card>
              </li>
            ))}
          </ul>
        </section>
      )}

      {installing && (
        <InstallDialog
          app={installing}
          organizations={orgs.filter((o) => installing.organizations.includes(o.id))}
          onClose={() => setInstalling(null)}
          onInstalled={async () => {
            setInstalling(null);
            await load();
          }}
        />
      )}
    </div>
  );
}

function InstallDialog({
  app,
  organizations,
  onClose,
  onInstalled,
}: {
  app: InstallableApp;
  organizations: Organization[];
  onClose: () => void;
  onInstalled: () => Promise<void>;
}) {
  const [org, setOrg] = useState(organizations[0]?.id ?? "");
  const [name, setName] = useState("");
  const [currency, setCurrency] = useState("AED");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<unknown>(null);
  const ids = { org: useId(), name: useId(), currency: useId() };

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setErr(null);
    try {
      await api.post("/service-apps/", {
        deployment: app.deployment,
        organization: org,
        display_name: name.trim(),
        config: { currency: currency.trim().toUpperCase() },
      });
      await onInstalled();
    } catch (error) {
      setErr(error);
      setBusy(false);
    }
  }

  return (
    <Modal open onClose={onClose} title={`Install ${app.product_name}`}>
      <form onSubmit={submit} className="flex flex-col gap-4">
        {err != null && <ErrorBanner message={err instanceof ApiError ? err.message : "Installation failed."} error={err} />}
        {organizations.length > 1 && (
          <div>
            <Label htmlFor={ids.org}>Organization</Label>
            <Select id={ids.org} value={org} onChange={(e) => setOrg(e.target.value)}>
              {organizations.map((o) => (
                <option key={o.id} value={o.id}>
                  {o.name}
                </option>
              ))}
            </Select>
          </div>
        )}
        <div>
          <Label htmlFor={ids.name}>Shop name</Label>
          <Input
            id={ids.name}
            required
            maxLength={200}
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="The name on your quotations and invoices"
          />
        </div>
        <div>
          <Label htmlFor={ids.currency}>Currency</Label>
          <Input
            id={ids.currency}
            required
            pattern="[A-Za-z]{3}"
            maxLength={3}
            value={currency}
            onChange={(e) => setCurrency(e.target.value)}
          />
        </div>
        <p className="text-xs text-slate-500">
          IntraForge creates the application&apos;s storage, keeps its data in your IntraForge backups, and lets people
          open it with their IntraForge sign-in. You can change these settings later.
        </p>
        <div className="flex justify-end gap-2">
          <Button type="button" variant="secondary" onClick={onClose} disabled={busy}>
            Cancel
          </Button>
          <Button type="submit" disabled={busy || !name.trim() || !org}>
            {busy && <Spinner className="h-4 w-4" />}
            Install
          </Button>
        </div>
      </form>
    </Modal>
  );
}
