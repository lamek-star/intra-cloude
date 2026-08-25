"use client";

import { useEffect, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { AppWindow } from "lucide-react";
import { api, ApiError, type Application, type Organization } from "@/lib/api";
import {
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
import { DeveloperNav } from "@/components/DeveloperNav";

export default function ApplicationsClient({ orgId }: { orgId: string }) {
  const router = useRouter();
  const [org, setOrg] = useState<Organization | null>(null);
  const [applications, setApplications] = useState<Application[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [createOpen, setCreateOpen] = useState(false);

  async function load() {
    try {
      const [o, apps] = await Promise.all([
        api.get<Organization>(`/organizations/${orgId}/`),
        api.get<Application[]>(`/organizations/${orgId}/applications/`),
      ]);
      setOrg(o);
      setApplications(apps);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load applications.");
    }
  }

  useEffect(() => {
    // One-shot fetch-on-mount/param-change, not a state-sync loop.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [orgId]);

  if (!org && !error) return <PageLoading />;
  if (error && !org) return <ErrorBanner message={error} />;
  if (!org || !applications) return null;

  return (
    <div>
      <PageHeader
        title="Applications"
        breadcrumbs={[
          { label: "Organizations", href: "/orgs" },
          { label: org.name, href: `/orgs/${orgId}` },
          { label: "Developer", href: `/orgs/${orgId}/developer` },
          { label: "Applications" },
        ]}
        description="Register external software that connects to this organization's data with its own scoped credentials."
        actions={
          <Button size="sm" onClick={() => setCreateOpen(true)}>
            New application
          </Button>
        }
      />

      <DeveloperNav orgId={orgId} active="applications" />

      {error && (
        <div className="mb-4">
          <ErrorBanner message={error} />
        </div>
      )}

      {applications.length === 0 ? (
        <EmptyState
          title="No applications yet"
          description="Register a website, backend service, or AI application to issue it a scoped API credential."
          action={
            <Button size="sm" onClick={() => setCreateOpen(true)}>
              New application
            </Button>
          }
        />
      ) : (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {applications.map((app) => (
            <button
              key={app.id}
              onClick={() => router.push(`/applications/${app.id}`)}
              className="text-left"
            >
              <Card className="transition-colors hover:border-indigo-400/40 hover:bg-slate-50">
                <div className="flex items-center gap-2">
                  <AppWindow className="h-4 w-4 text-indigo-600" />
                  <p className="font-medium text-slate-900">{app.name}</p>
                </div>
                {app.description && (
                  <p className="mt-1.5 line-clamp-2 text-xs text-slate-500">{app.description}</p>
                )}
              </Card>
            </button>
          ))}
        </div>
      )}

      <CreateApplicationModal
        open={createOpen}
        orgId={orgId}
        onClose={() => setCreateOpen(false)}
        onCreated={(app) => {
          setApplications((prev) => [...(prev ?? []), app]);
          setCreateOpen(false);
        }}
      />
    </div>
  );
}

function CreateApplicationModal({
  open,
  orgId,
  onClose,
  onCreated,
}: {
  open: boolean;
  orgId: string;
  onClose: () => void;
  onCreated: (app: Application) => void;
}) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const app = await api.post<Application>(`/organizations/${orgId}/applications/`, {
        name,
        description,
      });
      setName("");
      setDescription("");
      onCreated(app);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to create application.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Modal open={open} onClose={onClose} title="New application">
      <form onSubmit={handleSubmit} className="space-y-4">
        {error && <ErrorBanner message={error} />}
        <div>
          <Label htmlFor="app-name">Name</Label>
          <Input
            id="app-name"
            autoFocus
            required
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Harmony Website"
          />
        </div>
        <div>
          <Label htmlFor="app-description">Description (optional)</Label>
          <Textarea
            id="app-description"
            rows={2}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="What this application does and who owns it."
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
