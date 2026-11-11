"use client";

import { useCallback, useEffect, useId, useState } from "react";
import { api, ApiError, type AppInstance, type Project } from "@/lib/api";
import {
  isPreview,
  isReady,
  openHref,
  runtimeLabel,
  statusTone,
  type CatalogApp,
  type InstalledApp,
} from "@/lib/built-in-apps";
import {
  Badge,
  Button,
  Card,
  Checkbox,
  EmptyState,
  ErrorBanner,
  Input,
  Label,
  LinkButton,
  Modal,
  PageHeader,
  PageLoading,
  Spinner,
} from "@/components/ui";

type InstallPhase = "review" | "installing" | "done" | "failed";

type InstallState = {
  app: CatalogApp;
  phase: InstallPhase;
  label: string;
  acknowledged: boolean;
  error: string | null;
  /** The instance created by an install that then failed to finish setup -- retried, never duplicated. */
  incompleteId: string | null;
  openId: string | null;
};

function installErrorMessage(err: unknown): string {
  if (err instanceof ApiError) {
    if (err.status === 403) return "You don't have permission to install applications here. Ask an administrator.";
    if (err.status === 404) return "This application isn't available.";
    return err.message;
  }
  return "The application could not be installed. Nothing is lost; please try again.";
}

export default function AppGalleryClient({ projectId }: { projectId: string }) {
  const [project, setProject] = useState<Project | null>(null);
  const [apps, setApps] = useState<CatalogApp[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [errorDetail, setErrorDetail] = useState<unknown>(null);
  const [install, setInstall] = useState<InstallState | null>(null);
  const [retryingId, setRetryingId] = useState<string | null>(null);
  const [retryError, setRetryError] = useState<string | null>(null);

  const loadCatalog = useCallback(async (): Promise<CatalogApp[]> => {
    const catalog = await api.get<{ results: CatalogApp[] }>(`/built-in-apps/?project=${projectId}`);
    return catalog.results;
  }, [projectId]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [p, catalog] = await Promise.all([api.get<Project>(`/projects/${projectId}/`), loadCatalog()]);
        if (cancelled) return;
        setProject(p);
        setApps(catalog);
      } catch (err) {
        if (cancelled) return;
        setError(err instanceof ApiError && err.status === 404 ? "That project wasn't found." : "The applications couldn't be loaded.");
        setErrorDetail(err);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [projectId, loadCatalog]);

  function openInstall(app: CatalogApp) {
    setInstall({ app, phase: "review", label: app.label, acknowledged: !isPreview(app), error: null, incompleteId: null, openId: null });
  }

  async function runInstall() {
    if (!install) return;
    const { app, label, incompleteId } = install;
    setInstall({ ...install, phase: "installing", error: null });
    try {
      let instanceId: string;
      if (incompleteId) {
        // A previous attempt created the instance but did not finish preparing it: finish that one.
        const instance = await api.post<AppInstance>(`/app-instances/${incompleteId}/built-in/retry/`, {});
        instanceId = instance.id;
      } else {
        const instance = await api.post<AppInstance>(`/projects/${projectId}/built-in-apps/${app.key}/install/`, { label });
        instanceId = instance.id;
      }
      setApps(await loadCatalog());
      setInstall((current) => (current ? { ...current, phase: "done", openId: instanceId } : current));
    } catch (err) {
      let stranded: string | null = incompleteId;
      try {
        const fresh = await loadCatalog();
        setApps(fresh);
        // The install may have created the instance before failing to prepare it.
        const known = new Set(app.installed.map((i) => i.id));
        stranded =
          incompleteId ??
          fresh.find((a) => a.key === app.key)?.installed.find((i) => !known.has(i.id) && !isReady(i))?.id ??
          null;
      } catch {
        /* keep the original error; the list refreshes on the next visit */
      }
      setInstall((current) =>
        current ? { ...current, phase: "failed", error: installErrorMessage(err), incompleteId: stranded } : current,
      );
    }
  }

  async function retryExisting(app: CatalogApp, installed: InstalledApp) {
    setRetryError(null);
    setRetryingId(installed.id);
    try {
      await api.post<AppInstance>(`/app-instances/${installed.id}/built-in/retry/`, {});
      setApps(await loadCatalog());
    } catch (err) {
      setRetryError(`${app.label} could not be finished: ${installErrorMessage(err)}`);
      try {
        setApps(await loadCatalog());
      } catch {
        /* ignore */
      }
    } finally {
      setRetryingId(null);
    }
  }

  if (error) return <ErrorBanner message={error} error={errorDetail} />;
  if (!apps || !project) return <PageLoading />;

  return (
    <div>
      <PageHeader
        title="Applications"
        description="Ready-made business applications that run privately on your own computer."
        breadcrumbs={[
          { label: "Organizations", href: "/orgs" },
          { label: project.name, href: `/projects/${projectId}` },
          { label: "Applications" },
        ]}
      />

      {retryError && (
        <div className="mb-4">
          <ErrorBanner message={retryError} />
        </div>
      )}

      {apps.length === 0 ? (
        <EmptyState
          title="No applications are available yet"
          description="Applications appear here once they have completed qualification for this edition. Nothing has been installed or changed."
        />
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          {apps.map((app) => (
            <AppCard
              key={app.key}
              app={app}
              retryingId={retryingId}
              onInstall={() => openInstall(app)}
              onRetry={(installed) => retryExisting(app, installed)}
            />
          ))}
        </div>
      )}

      {install && (
        <InstallDialog
          state={install}
          onChange={(patch) => setInstall((current) => (current ? { ...current, ...patch } : current))}
          onInstall={runInstall}
          onClose={() => install.phase !== "installing" && setInstall(null)}
        />
      )}
    </div>
  );
}

function AppCard({
  app,
  retryingId,
  onInstall,
  onRetry,
}: {
  app: CatalogApp;
  retryingId: string | null;
  onInstall: () => void;
  onRetry: (installed: InstalledApp) => void;
}) {
  const titleId = useId();
  const preview = isPreview(app);
  const installedAny = app.installed.length > 0;
  return (
    <article aria-labelledby={titleId}>
      <Card className="h-full">
        <div className="flex items-start justify-between gap-2">
          <h2 id={titleId} className="text-base font-semibold text-slate-900">
            {app.label}
          </h2>
          <Badge tone={statusTone(app.status)}>{app.status_label}</Badge>
        </div>
        <p className="mt-1.5 text-sm text-slate-600">{app.summary}</p>
        <ul className="mt-3 flex flex-wrap gap-1.5" aria-label={`${app.label} includes`}>
          {app.highlights.map((h) => (
            <li key={h}>
              <Badge>{h}</Badge>
            </li>
          ))}
        </ul>
        {preview && (
          <p className="mt-3 rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-800">
            {app.status === "partially_qualified"
              ? "Pilot preview: this application has not completed production qualification. Use it alongside your existing process."
              : "Experimental: not qualified for production use."}
          </p>
        )}

        {installedAny && (
          <ul className="mt-4 space-y-2" aria-label={`Installed ${app.label}`}>
            {app.installed.map((installed) => (
              <li
                key={installed.id}
                className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-slate-200 px-3 py-2"
              >
                <span className="text-sm font-medium text-slate-800">{installed.label}</span>
                <span className="flex items-center gap-2">
                  <Badge tone={isReady(installed) ? "success" : "warning"}>{runtimeLabel(installed.runtime)}</Badge>
                  {isReady(installed) ? (
                    <LinkButton href={openHref(app.key, installed.id)} variant="primary" size="sm">
                      Open
                    </LinkButton>
                  ) : (
                    <Button size="sm" disabled={retryingId === installed.id} onClick={() => onRetry(installed)}>
                      {retryingId === installed.id ? "Finishing…" : "Finish setup"}
                    </Button>
                  )}
                </span>
              </li>
            ))}
          </ul>
        )}

        <div className="mt-4">
          {installedAny ? (
            <Button variant="ghost" size="sm" onClick={onInstall}>
              Install another copy
            </Button>
          ) : (
            <Button onClick={onInstall}>Install</Button>
          )}
        </div>
      </Card>
    </article>
  );
}

function InstallDialog({
  state,
  onChange,
  onInstall,
  onClose,
}: {
  state: InstallState;
  onChange: (patch: Partial<InstallState>) => void;
  onInstall: () => void;
  onClose: () => void;
}) {
  const nameId = useId();
  const { app, phase, label, acknowledged, error, openId } = state;
  const preview = isPreview(app);
  const canInstall = label.trim().length > 0 && acknowledged;
  return (
    <Modal open onClose={onClose} title={`Install ${app.label}`}>
      {phase === "installing" && (
        <div role="status" className="flex flex-col items-center gap-3 py-6 text-center">
          <Spinner className="h-6 w-6 text-brand-600" />
          <p className="text-sm font-medium text-slate-800">Preparing {app.label}…</p>
          <p className="text-xs text-slate-500">
            Setting up its data on your computer. This takes a few seconds; please keep this window open.
          </p>
        </div>
      )}

      {phase === "done" && openId && (
        <div className="space-y-4">
          <p role="status" className="text-sm text-slate-700">
            <span className="font-medium text-slate-900">{app.label} is ready.</span> Everything is set up on your
            computer and you can start using it now.
          </p>
          <div className="flex justify-end gap-2">
            <Button variant="secondary" onClick={onClose}>
              Close
            </Button>
            <LinkButton href={openHref(app.key, openId)} variant="primary">
              Open application
            </LinkButton>
          </div>
        </div>
      )}

      {(phase === "review" || phase === "failed") && (
        <form
          className="space-y-4"
          onSubmit={(e) => {
            e.preventDefault();
            if (canInstall) onInstall();
          }}
        >
          {phase === "failed" && error && <ErrorBanner message={error} />}
          {phase === "failed" && (
            <p className="text-xs text-slate-500">
              {state.incompleteId
                ? "Your application was created but not finished. Trying again finishes it; nothing is duplicated."
                : "Nothing was installed."}
            </p>
          )}
          {phase === "review" && (
            <>
              <p className="text-sm text-slate-600">{app.summary}</p>
              <p className="text-xs text-slate-500">
                This sets up {app.label} on your own computer, ready to use. It includes: {app.highlights.join(", ")}.
              </p>
              <div>
                <Label htmlFor={nameId}>Application name</Label>
                <Input
                  id={nameId}
                  value={label}
                  maxLength={200}
                  onChange={(e) => onChange({ label: e.target.value })}
                />
              </div>
              {preview && (
                <label className="flex items-start gap-2 rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-900">
                  <Checkbox
                    checked={acknowledged}
                    onChange={(e) => onChange({ acknowledged: e.target.checked })}
                    aria-label="I understand this is a preview"
                  />
                  <span>
                    I understand this is a <strong>{app.status_label.toLowerCase()}</strong> that has not completed
                    production qualification, and I will keep my existing records alongside it.
                  </span>
                </label>
              )}
            </>
          )}
          <div className="flex justify-end gap-2">
            <Button type="button" variant="secondary" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit" disabled={!canInstall}>
              {phase === "failed" ? "Try again" : "Install"}
            </Button>
          </div>
        </form>
      )}
    </Modal>
  );
}
