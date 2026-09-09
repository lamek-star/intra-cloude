"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import Link from "next/link";
import { Boxes } from "lucide-react";
import {
  api,
  ApiError,
  type AppInstance,
  type AppModelDefinition,
  type AppRelationshipDefinition,
  type Paginated,
  type Project,
  type RuntimePlan,
  type RuntimeStatus,
} from "@/lib/api";
import {
  Badge,
  Button,
  Card,
  Checkbox,
  EmptyState,
  ErrorBanner,
  Input,
  Label,
  Modal,
  PageHeader,
  PageLoading,
  Spinner,
} from "@/components/ui";

export default function AppInstanceClient({ instanceId }: { instanceId: string }) {
  const [instance, setInstance] = useState<AppInstance | null>(null);
  const [project, setProject] = useState<Project | null>(null);
  const [models, setModels] = useState<AppModelDefinition[] | null>(null);
  const [relationships, setRelationships] = useState<AppRelationshipDefinition[] | null>(null);
  const [runtime, setRuntime] = useState<RuntimeStatus | null>(null);
  const [runtimeVisible, setRuntimeVisible] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [errorDetail, setErrorDetail] = useState<unknown>(null);
  const [provisionError, setProvisionError] = useState<string | null>(null);
  const [provisioning, setProvisioning] = useState(false);
  const [editModalOpen, setEditModalOpen] = useState(false);
  const pollRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  async function loadRuntime() {
    try {
      setRuntime(await api.get<RuntimeStatus>(`/app-instances/${instanceId}/runtime/`));
      setRuntimeVisible(true);
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) {
        setRuntime(null);
        setRuntimeVisible(true);
      }
      // A 403 (no app_instance.schema.manage) leaves runtimeVisible false --
      // this actor can browse installed models but not manage provisioning.
    }
  }

  async function load() {
    try {
      const inst = await api.get<AppInstance>(`/app-instances/${instanceId}/`);
      setInstance(inst);
      const [m, r] = await Promise.all([
        api.get<Paginated<AppModelDefinition>>(`/app-instances/${instanceId}/models/?limit=100`),
        api.get<Paginated<AppRelationshipDefinition>>(
          `/app-instances/${instanceId}/relationships/?limit=500`,
        ),
      ]);
      setModels(m.results);
      setRelationships(r.results);
      api.get<Project>(`/projects/${inst.project}/`).then(setProject).catch(() => {});
      loadRuntime();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load this app.");
      setErrorDetail(err);
    }
  }

  useEffect(() => {
    // One-shot fetch-on-mount/param-change, not a state-sync loop.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    load();
    return () => {
      if (pollRef.current) clearTimeout(pollRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [instanceId]);

  function pollRuntime() {
    pollRef.current = setTimeout(async () => {
      try {
        const status = await api.get<RuntimeStatus>(`/app-instances/${instanceId}/runtime/`);
        setRuntime(status);
        if (status.status === "pending") pollRuntime();
        else setProvisioning(false);
      } catch {
        setProvisioning(false);
      }
    }, 2000);
  }

  async function handleProvision() {
    setProvisionError(null);
    setProvisioning(true);
    try {
      const plan = await api.get<RuntimePlan>(`/app-instances/${instanceId}/runtime-plan/`);
      const status = await api.post<RuntimeStatus>(`/app-instances/${instanceId}/runtime/`, {
        fingerprint: plan.fingerprint,
      });
      setRuntime(status);
      if (status.status === "pending") pollRuntime();
      else setProvisioning(false);
    } catch (err) {
      setProvisionError(err instanceof ApiError ? err.message : "Failed to start provisioning.");
      setProvisioning(false);
    }
  }

  if (!instance && !error) return <PageLoading />;
  if (error && !instance) return <ErrorBanner message={error} error={errorDetail} />;
  if (!instance) return null;

  const modelLabel = (id: string) => models?.find((m) => m.id === id)?.label ?? id.slice(0, 8);

  return (
    <div>
      <PageHeader
        title={instance.label}
        breadcrumbs={[
          { label: "Organizations", href: "/orgs" },
          ...(project ? [{ label: project.name, href: `/projects/${project.id}` }] : []),
          { label: instance.label },
        ]}
        description="A generic app instance — each model below has its own data explorer once its runtime is provisioned."
        actions={
          <Button variant="secondary" onClick={() => setEditModalOpen(true)}>
            Edit
          </Button>
        }
      />

      {error && (
        <div className="mb-4">
          <ErrorBanner message={error} error={errorDetail} />
        </div>
      )}

      {instance.archived && (
        <div className="mb-4">
          <Badge tone="warning">Archived</Badge>
        </div>
      )}

      {runtimeVisible && (
        <Card className="mb-6">
          {provisionError && (
            <div className="mb-3">
              <ErrorBanner message={provisionError} />
            </div>
          )}
          {!runtime ? (
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-slate-900">Runtime not provisioned</p>
                <p className="text-xs text-slate-500">
                  Provisioning creates a real database table for each model above.
                </p>
              </div>
              <Button onClick={handleProvision} disabled={provisioning || models?.length === 0}>
                {provisioning ? "Starting…" : "Provision runtime"}
              </Button>
            </div>
          ) : runtime.status === "ready" ? (
            <div className="flex items-center gap-2 text-sm text-green-700">
              <Badge tone="success">Ready</Badge>
              Runtime is provisioned — models above link to their real record screens.
            </div>
          ) : runtime.status === "failed" ? (
            <div>
              <div className="flex items-center justify-between">
                <Badge tone="danger">Failed</Badge>
                <Button size="sm" onClick={handleProvision} disabled={provisioning}>
                  {provisioning ? "Retrying…" : "Retry"}
                </Button>
              </div>
              {runtime.error && <p className="mt-2 text-xs text-red-600">{runtime.error}</p>}
            </div>
          ) : (
            <div className="flex items-center gap-2 text-sm text-slate-600">
              <Spinner className="h-4 w-4" /> Provisioning…
            </div>
          )}
        </Card>
      )}

      <h2 className="mb-3 text-sm font-semibold text-slate-600">Models</h2>
      {models && models.length === 0 ? (
        <EmptyState
          title="No models yet"
          description="This app's template defines no models, or none have been installed."
        />
      ) : (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {models?.map((m) => (
            <Link key={m.id} href={`/app-models/${m.id}`} className="block text-left">
              <Card className="transition-colors hover:border-brand-400/40 hover:bg-slate-50">
                <div className="flex items-center gap-2">
                  <Boxes className="h-4 w-4 text-brand-600" />
                  <p className="font-medium text-slate-900">{m.label}</p>
                </div>
                <p className="mt-1 text-xs text-slate-500">{m.key}</p>
              </Card>
            </Link>
          ))}
        </div>
      )}

      {relationships && relationships.length > 0 && (
        <div className="mt-8">
          <h2 className="mb-3 text-sm font-semibold text-slate-600">Relationships</h2>
          <div className="flex flex-wrap gap-2">
            {relationships.map((r) => (
              <Badge key={r.id}>
                {modelLabel(r.source_model)} → {modelLabel(r.target_model)} ({r.label})
              </Badge>
            ))}
          </div>
        </div>
      )}

      <EditInstanceModal
        open={editModalOpen}
        instance={instance}
        onClose={() => setEditModalOpen(false)}
        onSaved={(inst) => {
          setInstance(inst);
          setEditModalOpen(false);
        }}
      />
    </div>
  );
}

function EditInstanceModal({
  open,
  instance,
  onClose,
  onSaved,
}: {
  open: boolean;
  instance: AppInstance;
  onClose: () => void;
  onSaved: (inst: AppInstance) => void;
}) {
  const [label, setLabel] = useState(instance.label);
  const [archived, setArchived] = useState(instance.archived);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!open) return;
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setLabel(instance.label);
    setArchived(instance.archived);
    setError(null);
  }, [open, instance]);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const inst = await api.patch<AppInstance>(`/app-instances/${instance.id}/`, { label, archived });
      onSaved(inst);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to save.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Modal open={open} onClose={onClose} title="Edit app">
      <form onSubmit={handleSubmit} className="space-y-4">
        {error && <ErrorBanner message={error} />}
        <div>
          <Label htmlFor="edit-instance-label">Name</Label>
          <Input id="edit-instance-label" required value={label} onChange={(e) => setLabel(e.target.value)} />
        </div>
        <label className="flex items-center gap-2 text-sm text-slate-600">
          <Checkbox checked={archived} onChange={(e) => setArchived(e.target.checked)} />
          Archived
        </label>
        <div className="flex justify-end gap-2">
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" disabled={submitting}>
            {submitting ? "..." : "Save"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
