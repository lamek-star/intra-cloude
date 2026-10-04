"use client";

import { useEffect, useState } from "react";
import { api, ApiError, type AppTemplate, type AppTemplateVersion } from "@/lib/api";
import { Badge, Card, ErrorBanner, PageHeader, PageLoading } from "@/components/ui";

export default function AppTemplateVersionClient({ versionId }: { versionId: string }) {
  const [version, setVersion] = useState<AppTemplateVersion | null>(null);
  const [template, setTemplate] = useState<AppTemplate | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [errorDetail, setErrorDetail] = useState<unknown>(null);

  async function load() {
    try {
      const v = await api.get<AppTemplateVersion>(`/app-template-versions/${versionId}/`);
      setVersion(v);
      api.get<AppTemplate>(`/app-templates/${v.template}/`).then(setTemplate).catch(() => {});
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load this version.");
      setErrorDetail(err);
    }
  }

  useEffect(() => {
    // One-shot fetch-on-mount/param-change, not a state-sync loop.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [versionId]);

  if (!version && !error) return <PageLoading />;
  if (error && !version) return <ErrorBanner message={error} error={errorDetail} />;
  if (!version) return null;

  return (
    <div>
      <PageHeader
        title={`${template ? template.label : "App template"} — v${version.number}`}
        breadcrumbs={[
          { label: "Organizations", href: "/orgs" },
          ...(template ? [{ label: template.label, href: `/app-templates/${template.id}` }] : []),
          { label: `Version ${version.number}` },
        ]}
        description={`Published ${new Date(version.created_at).toLocaleString()} · checksum ${version.checksum_sha256.slice(0, 12)}`}
      />

      {error && (
        <div className="mb-4">
          <ErrorBanner message={error} error={errorDetail} />
        </div>
      )}

      <div className="space-y-4">
        {version.definition.models.map((model) => (
          <Card key={model.id}>
            <div className="flex items-center gap-2">
              <p className="font-medium text-slate-900">{model.label}</p>
              <Badge>{model.key}</Badge>
            </div>
            <div className="mt-2 flex flex-wrap gap-1.5">
              {model.fields.map((field) => (
                <Badge key={field.id}>
                  {field.label}: {field.data_type}
                  {field.required ? " · required" : ""}
                </Badge>
              ))}
            </div>
          </Card>
        ))}
      </div>

      {version.definition.relationships.length > 0 && (
        <div className="mt-8">
          <h2 className="mb-3 text-sm font-semibold text-slate-600">Relationships</h2>
          <div className="flex flex-wrap gap-2">
            {version.definition.relationships.map((rel) => {
              const source = version.definition.models.find((m) => m.id === rel.source_model);
              const target = version.definition.models.find((m) => m.id === rel.target_model);
              return (
                <Badge key={rel.id}>
                  {source?.label ?? "?"} → {target?.label ?? "?"} ({rel.label})
                </Badge>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
