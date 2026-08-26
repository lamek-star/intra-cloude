"use client";

import { useEffect, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { api, ApiError, type Organization } from "@/lib/api";
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
} from "@/components/ui";

export default function OrgsPage() {
  const router = useRouter();
  const [orgs, setOrgs] = useState<Organization[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [errorDetail, setErrorDetail] = useState<unknown>(null);
  const [modalOpen, setModalOpen] = useState(false);

  async function load() {
    try {
      setOrgs(await api.get<Organization[]>("/organizations/"));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load organizations.");
      setErrorDetail(err);
    }
  }

  useEffect(() => {
    // One-shot fetch-on-mount, not a state-sync loop.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    load();
  }, []);

  if (orgs === null && !error) return <PageLoading />;

  return (
    <div>
      <PageHeader
        title="Organizations"
        description="Every organization you're an active member of."
        actions={<Button onClick={() => setModalOpen(true)}>New organization</Button>}
      />

      {error && (
        <div className="mb-4">
          <ErrorBanner message={error} error={errorDetail} />
        </div>
      )}

      {orgs && orgs.length === 0 ? (
        <EmptyState
          title="No organizations yet"
          description="Create your first organization to start adding workspaces, storage, and databases."
          action={<Button onClick={() => setModalOpen(true)}>New organization</Button>}
        />
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {orgs?.map((org) => (
            <button
              key={org.id}
              onClick={() => router.push(`/orgs/${org.id}`)}
              className="text-left"
            >
              <Card className="h-full transition-colors hover:border-indigo-400/40 hover:bg-slate-50">
                <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-indigo-50 text-sm font-semibold text-indigo-600">
                  {org.name.slice(0, 1).toUpperCase()}
                </div>
                <p className="mt-3 font-medium text-slate-900">{org.name}</p>
                <p className="mt-0.5 text-xs text-slate-500">/{org.slug}</p>
              </Card>
            </button>
          ))}
        </div>
      )}

      <CreateOrgModal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        onCreated={(org) => router.push(`/orgs/${org.id}`)}
      />
    </div>
  );
}

function CreateOrgModal({
  open,
  onClose,
  onCreated,
}: {
  open: boolean;
  onClose: () => void;
  onCreated: (org: Organization) => void;
}) {
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [errorDetail, setErrorDetail] = useState<unknown>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const org = await api.post<Organization>("/organizations/", { name });
      setName("");
      onCreated(org);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to create organization.");
      setErrorDetail(err);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Modal open={open} onClose={onClose} title="New organization">
      <form onSubmit={handleSubmit} className="space-y-4">
        {error && <ErrorBanner message={error} error={errorDetail} />}
        <div>
          <Label htmlFor="org-name">Name</Label>
          <Input
            id="org-name"
            autoFocus
            required
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Acme Corp"
          />
          <p className="mt-1.5 text-xs text-slate-500">
            You&apos;ll become its administrator immediately.
          </p>
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
