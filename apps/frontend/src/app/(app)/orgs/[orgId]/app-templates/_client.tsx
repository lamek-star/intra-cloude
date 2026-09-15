"use client";

import { useEffect, useState, type FormEvent } from "react";
import Link from "next/link";
import { Layers } from "lucide-react";
import { api, ApiError, type AppTemplate, type Organization, type Paginated } from "@/lib/api";
import {
  Badge,
  Button,
  Card,
  EmptyState,
  ErrorBanner,
  Input,
  Label,
  Modal,
  PageHeader,
  PageLoading,
  Textarea,
} from "@/components/ui";

export default function AppTemplatesClient({ orgId }: { orgId: string }) {
  const [org, setOrg] = useState<Organization | null>(null);
  const [templates, setTemplates] = useState<AppTemplate[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [errorDetail, setErrorDetail] = useState<unknown>(null);
  const [modalOpen, setModalOpen] = useState(false);

  async function load() {
    try {
      const [o, page] = await Promise.all([
        api.get<Organization>(`/organizations/${orgId}/`),
        api.get<Paginated<AppTemplate>>(`/organizations/${orgId}/app-templates/?limit=100`),
      ]);
      setOrg(o);
      setTemplates(page.results);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load app templates.");
      setErrorDetail(err);
    }
  }

  useEffect(() => {
    // One-shot fetch-on-mount/param-change, not a state-sync loop.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [orgId]);

  if (!templates && !error) return <PageLoading />;
  if (error && !templates) return <ErrorBanner message={error} error={errorDetail} />;

  return (
    <div>
      <PageHeader
        title="App templates"
        breadcrumbs={[
          { label: "Organizations", href: "/orgs" },
          ...(org ? [{ label: org.name, href: `/orgs/${orgId}` }] : []),
          { label: "App templates" },
        ]}
        description="A template is a draft app definition -- publish a version, then install it into a project to get a real, provisioned data model."
        actions={<Button onClick={() => setModalOpen(true)}>New template</Button>}
      />

      {error && (
        <div className="mb-4">
          <ErrorBanner message={error} error={errorDetail} />
        </div>
      )}

      {templates && templates.length === 0 ? (
        <EmptyState
          title="No app templates yet"
          description="Create a template, add models and fields, then publish a version to install."
          action={<Button onClick={() => setModalOpen(true)}>New template</Button>}
        />
      ) : (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {templates?.map((t) => (
            <Link key={t.id} href={`/app-templates/${t.id}`} className="block text-left">
              <Card className="transition-colors hover:border-brand-400/40 hover:bg-slate-50">
                <div className="flex items-center gap-2">
                  <Layers className="h-4 w-4 text-brand-600" />
                  <p className="font-medium text-slate-900">{t.label}</p>
                </div>
                <p className="mt-1 text-xs text-slate-500">
                  {t.draft.models.length} model{t.draft.models.length === 1 ? "" : "s"}
                </p>
                {t.archived && (
                  <div className="mt-1.5">
                    <Badge tone="warning">Archived</Badge>
                  </div>
                )}
              </Card>
            </Link>
          ))}
        </div>
      )}

      <CreateTemplateModal
        open={modalOpen}
        orgId={orgId}
        onClose={() => setModalOpen(false)}
        onCreated={(t) => {
          setTemplates((prev) => [...(prev ?? []), t]);
          setModalOpen(false);
        }}
      />
    </div>
  );
}

function CreateTemplateModal({
  open,
  orgId,
  onClose,
  onCreated,
}: {
  open: boolean;
  orgId: string;
  onClose: () => void;
  onCreated: (t: AppTemplate) => void;
}) {
  const [label, setLabel] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!open) return;
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setLabel("");
    setDescription("");
    setError(null);
  }, [open]);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const t = await api.post<AppTemplate>(`/organizations/${orgId}/app-templates/`, {
        label,
        description,
      });
      onCreated(t);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to create template.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Modal open={open} onClose={onClose} title="New app template">
      <form onSubmit={handleSubmit} className="space-y-4">
        {error && <ErrorBanner message={error} />}
        <div>
          <Label htmlFor="template-label">Name</Label>
          <Input
            id="template-label"
            autoFocus
            required
            value={label}
            onChange={(e) => setLabel(e.target.value)}
            placeholder="Inventory tracker"
          />
        </div>
        <div>
          <Label htmlFor="template-description">Description</Label>
          <Textarea
            id="template-description"
            rows={3}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
        </div>
        <div className="flex justify-end gap-2">
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" disabled={submitting}>
            {submitting ? "..." : "Create"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
