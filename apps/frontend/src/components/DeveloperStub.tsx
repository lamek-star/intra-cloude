"use client";

import { useEffect, useState } from "react";
import { api, ApiError, type Organization } from "@/lib/api";
import { ComingSoon, ErrorBanner, PageHeader, PageLoading } from "@/components/ui";
import { DeveloperNav } from "@/components/DeveloperNav";

/** Shared shell for a Developer nav tab whose backend surface doesn't
 * exist yet (Environments, API Keys, Storage, Database, Auth, Webhooks,
 * API Logs, Usage). One component instead of eight near-identical
 * client files -- each tab's `page.tsx` just supplies the copy. */
export function DeveloperStub({
  orgId,
  tabKey,
  title,
  comingSoonTitle,
  comingSoonDescription,
}: {
  orgId: string;
  tabKey: string;
  title: string;
  comingSoonTitle: string;
  comingSoonDescription: string;
}) {
  const [org, setOrg] = useState<Organization | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .get<Organization>(`/organizations/${orgId}/`)
      .then(setOrg)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load organization."));
  }, [orgId]);

  if (!org && !error) return <PageLoading />;
  if (error && !org) return <ErrorBanner message={error} />;
  if (!org) return null;

  return (
    <div>
      <PageHeader
        title={title}
        breadcrumbs={[
          { label: "Organizations", href: "/orgs" },
          { label: org.name, href: `/orgs/${orgId}` },
          { label: "Developer", href: `/orgs/${orgId}/developer` },
          { label: title },
        ]}
      />
      <DeveloperNav orgId={orgId} active={tabKey} />
      <ComingSoon title={comingSoonTitle} description={comingSoonDescription} />
    </div>
  );
}
