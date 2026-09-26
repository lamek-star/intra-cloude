"use client";

import { useCallback, useEffect, useId, useState } from "react";
import { useRouter } from "next/navigation";
import { AlertTriangle } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import {
  STATE_LABEL,
  STATE_TONE,
  type ServiceApp,
  type ServiceAppConfig,
} from "@/lib/service-apps";
import {
  Badge,
  Button,
  Card,
  Checkbox,
  ErrorBanner,
  Input,
  Label,
  PageHeader,
  PageLoading,
  Spinner,
  Textarea,
} from "@/components/ui";

type Removal = {
  display_name: string;
  schema: string;
  rows: Record<string, number>;
  files: number;
  external_backups_touched: boolean;
};

const TEXT_FIELDS: { key: keyof ServiceAppConfig; label: string; long?: boolean }[] = [
  { key: "shopName", label: "Shop name (printed on documents)" },
  { key: "address", label: "Address", long: true },
  { key: "phone", label: "Phone" },
  { key: "email", label: "Email" },
  { key: "taxRegistration", label: "Tax registration number" },
  { key: "quotationTerms", label: "Quotation terms", long: true },
  { key: "invoiceNotes", label: "Invoice notes", long: true },
];

export default function SettingsClient({ appId }: { appId: string }) {
  const [app, setApp] = useState<ServiceApp | null>(null);
  const [error, setError] = useState<unknown>(null);
  const load = useCallback(async () => {
    try {
      setApp(await api.get<ServiceApp>(`/service-apps/${appId}/`));
    } catch (err) {
      setError(err);
    }
  }, [appId]);
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const loaded = await api.get<ServiceApp>(`/service-apps/${appId}/`);
        if (!cancelled) setApp(loaded);
      } catch (err) {
        if (!cancelled) setError(err);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [appId]);

  if (error && !app) return <ErrorBanner message="This application could not be loaded." error={error} />;
  if (!app) return <PageLoading />;
  const state = app.health?.state ?? "stopped";
  return (
    <div className="max-w-3xl">
      <PageHeader
        title={`${app.display_name} settings`}
        description={`${app.name} · ${app.organization.name}`}
        breadcrumbs={[{ label: "Apps", href: "/apps" }, { label: app.display_name }]}
        actions={<Badge tone={STATE_TONE[state]}>{STATE_LABEL[state]}</Badge>}
      />
      {app.removed ? (
        <Reinstate app={app} onDone={load} />
      ) : (
        <>
          {app.can_configure && app.config && <ConfigForm app={app} onSaved={setApp} />}
          {app.can_manage && <Availability app={app} onSaved={setApp} />}
          {app.can_manage && <Remove app={app} />}
        </>
      )}
    </div>
  );
}

function ConfigForm({ app, onSaved }: { app: ServiceApp; onSaved: (a: ServiceApp) => void }) {
  const [displayName, setDisplayName] = useState(app.display_name);
  const [config, setConfig] = useState<ServiceAppConfig>(app.config!);
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState(false);
  const [err, setErr] = useState<unknown>(null);
  const baseId = useId();
  const set = <K extends keyof ServiceAppConfig>(key: K, value: ServiceAppConfig[K]) =>
    setConfig((c) => ({ ...c, [key]: value }));

  async function save(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setSaved(false);
    setErr(null);
    try {
      onSaved(await api.patch<ServiceApp>(`/service-apps/${app.id}/`, { display_name: displayName, config }));
      setSaved(true);
    } catch (error) {
      setErr(error);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card className="mb-6">
      <form onSubmit={save} className="flex flex-col gap-4">
        <h2 className="text-sm font-semibold text-slate-900">Shop and documents</h2>
        {err != null && <ErrorBanner message={err instanceof ApiError ? err.message : "Not saved."} error={err} />}
        <div>
          <Label htmlFor={`${baseId}-dn`}>Name in Apps</Label>
          <Input id={`${baseId}-dn`} required maxLength={200} value={displayName} onChange={(e) => setDisplayName(e.target.value)} />
        </div>
        {TEXT_FIELDS.map((f) => (
          <div key={f.key}>
            <Label htmlFor={`${baseId}-${f.key}`}>{f.label}</Label>
            {f.long ? (
              <Textarea
                id={`${baseId}-${f.key}`}
                rows={3}
                maxLength={2000}
                value={String(config[f.key] ?? "")}
                onChange={(e) => set(f.key, e.target.value as never)}
              />
            ) : (
              <Input
                id={`${baseId}-${f.key}`}
                maxLength={f.key === "shopName" ? 200 : 254}
                value={String(config[f.key] ?? "")}
                onChange={(e) => set(f.key, e.target.value as never)}
              />
            )}
          </div>
        ))}
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <Label htmlFor={`${baseId}-cur`}>Currency</Label>
            <Input id={`${baseId}-cur`} maxLength={3} pattern="[A-Za-z]{3}" value={config.currency} onChange={(e) => set("currency", e.target.value.toUpperCase())} />
          </div>
          <div>
            <Label htmlFor={`${baseId}-tax`}>Default tax rate (%)</Label>
            <Input
              id={`${baseId}-tax`}
              type="number"
              min={0}
              max={1000}
              step="0.01"
              value={config.defaultTaxBp / 100}
              onChange={(e) => set("defaultTaxBp", Math.round(Number(e.target.value) * 100))}
            />
          </div>
          <div>
            <Label htmlFor={`${baseId}-qv`}>Quotations valid for (days)</Label>
            <Input id={`${baseId}-qv`} type="number" min={0} max={3650} value={config.quotationValidityDays} onChange={(e) => set("quotationValidityDays", Number(e.target.value))} />
          </div>
          <div>
            <Label htmlFor={`${baseId}-due`}>Invoices due after (days)</Label>
            <Input id={`${baseId}-due`} type="number" min={0} max={3650} value={config.invoiceDueDays} onChange={(e) => set("invoiceDueDays", Number(e.target.value))} />
          </div>
        </div>
        <div className="flex items-center gap-3">
          <Button type="submit" disabled={busy}>
            {busy && <Spinner className="h-4 w-4" />}
            Save
          </Button>
          {saved && <span className="text-sm text-green-700" role="status">Saved.</span>}
        </div>
      </form>
    </Card>
  );
}

function Availability({ app, onSaved }: { app: ServiceApp; onSaved: (a: ServiceApp) => void }) {
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<unknown>(null);
  async function toggle() {
    setBusy(true);
    setErr(null);
    try {
      onSaved(await api.patch<ServiceApp>(`/service-apps/${app.id}/`, { enabled: !app.enabled }));
    } catch (error) {
      setErr(error);
    } finally {
      setBusy(false);
    }
  }
  return (
    <Card className="mb-6">
      <h2 className="text-sm font-semibold text-slate-900">Availability</h2>
      <p className="mt-1 text-sm text-slate-500">
        {app.enabled
          ? "People with access can open this application."
          : "Nobody can open this application until it is enabled again. Its data is kept."}
      </p>
      {err != null && <ErrorBanner message="The change was not saved." error={err} />}
      <Button className="mt-3" variant="secondary" onClick={toggle} disabled={busy}>
        {app.enabled ? "Disable" : "Enable"}
      </Button>
    </Card>
  );
}

function Remove({ app }: { app: ServiceApp }) {
  const router = useRouter();
  const [preview, setPreview] = useState<Removal | null>(null);
  const [deleteData, setDeleteData] = useState(false);
  const [confirm, setConfirm] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<unknown>(null);
  const ids = { confirm: useId(), del: useId() };

  async function start() {
    setErr(null);
    try {
      setPreview(await api.get<Removal>(`/service-apps/${app.id}/removal-preview/`));
    } catch (error) {
      setErr(error);
    }
  }
  async function remove() {
    setBusy(true);
    setErr(null);
    try {
      await api.del(`/service-apps/${app.id}/`, { confirm_name: confirm, delete_data: deleteData });
      router.push("/apps");
    } catch (error) {
      setErr(error);
      setBusy(false);
    }
  }

  return (
    <Card className="border-red-200">
      <h2 className="text-sm font-semibold text-slate-900">Remove this application</h2>
      <p className="mt-1 text-sm text-slate-500">
        Removing it never touches IntraForge itself, other applications, or your backup files.
      </p>
      {err != null && <ErrorBanner message={err instanceof ApiError ? err.message : "Removal failed."} error={err} />}
      {!preview ? (
        <Button className="mt-3" variant="secondary" onClick={start}>
          Remove...
        </Button>
      ) : (
        <div className="mt-4 flex flex-col gap-4">
          <div className="rounded-lg bg-slate-50 p-3 text-sm text-slate-700">
            <p className="font-medium">What this application holds</p>
            <ul className="mt-1 list-disc pl-5">
              {Object.entries(preview.rows).map(([table, n]) => (
                <li key={table}>
                  {n.toLocaleString()} {table.replace(/_/g, " ")}
                </li>
              ))}
              <li>{preview.files.toLocaleString()} stored files</li>
            </ul>
          </div>
          <label htmlFor={ids.del} className="flex items-start gap-2 text-sm text-slate-700">
            <Checkbox id={ids.del} checked={deleteData} onChange={(e) => setDeleteData(e.target.checked)} />
            <span>
              Also <strong>delete all of its data</strong> (products, stock, customers, documents, catalogue and files).
              A backup is taken first; nothing is deleted if the backup fails.
            </span>
          </label>
          {deleteData && (
            <p className="flex items-start gap-2 rounded-lg bg-red-50 p-3 text-sm text-red-700">
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
              This cannot be undone here. The data can only come back by restoring that backup.
            </p>
          )}
          {!deleteData && (
            <p className="text-sm text-slate-500">
              Without deleting data, the application is closed and hidden, and can be reinstated later with everything
              intact.
            </p>
          )}
          <div>
            <Label htmlFor={ids.confirm}>
              Type <strong>{app.display_name}</strong> to confirm
            </Label>
            <Input id={ids.confirm} value={confirm} onChange={(e) => setConfirm(e.target.value)} autoComplete="off" />
          </div>
          <div className="flex gap-2">
            <Button variant="danger" onClick={remove} disabled={busy || confirm !== app.display_name}>
              {busy && <Spinner className="h-4 w-4" />}
              {deleteData ? "Back up, then delete everything" : "Remove, keep data"}
            </Button>
            <Button variant="secondary" onClick={() => setPreview(null)} disabled={busy}>
              Cancel
            </Button>
          </div>
        </div>
      )}
    </Card>
  );
}

function Reinstate({ app, onDone }: { app: ServiceApp; onDone: () => Promise<void> }) {
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<unknown>(null);
  async function go() {
    setBusy(true);
    try {
      await api.post(`/service-apps/${app.id}/reinstate/`);
      await onDone();
    } catch (error) {
      setErr(error);
      setBusy(false);
    }
  }
  return (
    <Card>
      <h2 className="text-sm font-semibold text-slate-900">This application was removed</h2>
      <p className="mt-1 text-sm text-slate-500">Its data was kept. Reinstating opens it again with everything intact.</p>
      {err != null && <ErrorBanner message="It could not be reinstated." error={err} />}
      {app.can_manage && (
        <Button className="mt-3" onClick={go} disabled={busy}>
          {busy && <Spinner className="h-4 w-4" />}
          Reinstate
        </Button>
      )}
    </Card>
  );
}
