"use client";

import { Suspense, useState, type FormEvent } from "react";
import Link from "next/link";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter, useSearchParams } from "next/navigation";
import { api, ApiError, type Organization } from "@/lib/api";
import { keys, organizationsQuery } from "@/lib/queries";
import { isSafeNextPath } from "@/lib/safe-next";
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
  return (
    <Suspense fallback={<PageLoading />}>
      <OrgsPageInner />
    </Suspense>
  );
}

function OrgsPageInner() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const next = searchParams.get("next");
  // The same cached list the dashboard reads (lib/queries.ts): usually on screen at once.
  const queryClient = useQueryClient();
  const query = useQuery(organizationsQuery);
  const orgs = query.data ?? null;
  const errorDetail = query.error;
  const error = errorDetail
    ? errorDetail instanceof ApiError
      ? errorDetail.message
      : "Failed to load organizations."
    : null;
  const [modalOpen, setModalOpen] = useState(false);

  if (orgs === null && !error) return <PageLoading />;

  const skipHref = isSafeNextPath(next) ? next : "/dashboard";

  function onOrgCreated(org: Organization) {
    void queryClient.invalidateQueries({ queryKey: keys.organizations });
    // Arriving here mid-external-auth-flow (welcome's "Create" button
    // forwards `next`) means creating an organization completes that
    // flow too -- return to `next` instead of the new org's own page,
    // exactly like "Continue without an organization" would have.
    if (isSafeNextPath(next)) {
      window.location.assign(next);
    } else {
      router.push(`/orgs/${org.id}`);
    }
  }

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
          description="Organizations are optional — your personal account already works without one. Create one when you need shared workspaces, storage, or databases."
          action={
            <div className="flex flex-col items-center gap-2">
              <Button onClick={() => setModalOpen(true)}>New organization</Button>
              <Link href={skipHref} className="text-xs text-slate-500 underline underline-offset-2 hover:text-slate-700">
                Skip — take me to my dashboard
              </Link>
            </div>
          }
        />
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {orgs?.map((org) => (
            <Link key={org.id} href={`/orgs/${org.id}`} className="block text-left">
              <Card className="h-full transition-colors hover:border-brand-400/40 hover:bg-slate-50">
                <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-brand-50 text-sm font-semibold text-brand-600">
                  {org.name.slice(0, 1).toUpperCase()}
                </div>
                <p className="mt-3 font-medium text-slate-900">{org.name}</p>
                <p className="mt-0.5 text-xs text-slate-500">/{org.slug}</p>
              </Card>
            </Link>
          ))}
        </div>
      )}

      <CreateOrgModal open={modalOpen} onClose={() => setModalOpen(false)} onCreated={onOrgCreated} />
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
