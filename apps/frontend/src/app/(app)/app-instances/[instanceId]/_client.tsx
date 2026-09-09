"use client";

import { useEffect, useState } from "react";
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
} from "@/lib/api";
import { Badge, Card, EmptyState, ErrorBanner, PageHeader, PageLoading } from "@/components/ui";

export default function AppInstanceClient({ instanceId }: { instanceId: string }) {
  const [instance, setInstance] = useState<AppInstance | null>(null);
  const [project, setProject] = useState<Project | null>(null);
  const [models, setModels] = useState<AppModelDefinition[] | null>(null);
  const [relationships, setRelationships] = useState<AppRelationshipDefinition[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [errorDetail, setErrorDetail] = useState<unknown>(null);

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
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load this app.");
      setErrorDetail(err);
    }
  }

  useEffect(() => {
    // One-shot fetch-on-mount/param-change, not a state-sync loop.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [instanceId]);

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
    </div>
  );
}
