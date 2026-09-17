"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ExternalLink } from "lucide-react";
import {
  api,
  ApiError,
  type Application,
  type Environment,
  type EnvironmentWebhook,
  type Organization,
} from "@/lib/api";
import {
  Badge,
  CopyButton,
  EmptyState,
  ErrorBanner,
  PageHeader,
  PageLoading,
  Table,
  Td,
  Th,
  THead,
  TRow,
} from "@/components/ui";
import { DeveloperNav } from "@/components/DeveloperNav";

type EnvironmentRow = Environment & { applicationName: string; webhookCount: number };

const EVENT_TYPES = [
  { type: "app_instance.record.create", description: "A record is created" },
  { type: "app_instance.record.update", description: "A record is updated" },
  { type: "app_instance.record.delete", description: "A record is deleted" },
  { type: "app_instance.workflow.transition", description: "A workflow transition is applied" },
];

const PAYLOAD_EXAMPLE = `{
  "event_id": "...",
  "event_type": "app_instance.record.create",
  "instance_id": "...",
  "model": { "id": "...", "key": "..." },
  "record_id": "..."
}`;

const VERIFY_EXAMPLE = `import hmac, hashlib

expected = "sha256=" + hmac.new(
    signing_secret.encode(), raw_body, hashlib.sha256
).hexdigest()

if not hmac.compare_digest(expected, request.headers["X-IntraForge-Signature"]):
    reject()`;

export default function WebhooksClient({ orgId }: { orgId: string }) {
  const [org, setOrg] = useState<Organization | null>(null);
  const [environments, setEnvironments] = useState<EnvironmentRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [errorDetail, setErrorDetail] = useState<unknown>(null);

  useEffect(() => {
    async function load() {
      try {
        const [o, apps] = await Promise.all([
          api.get<Organization>(`/organizations/${orgId}/`),
          api.get<Application[]>(`/organizations/${orgId}/applications/`),
        ]);
        setOrg(o);

        const perApp = await Promise.all(
          apps.map((app) =>
            api
              .get<Environment[]>(`/applications/${app.id}/environments/`)
              .then((envs) =>
                Promise.all(
                  envs.map(async (e): Promise<EnvironmentRow> => {
                    const webhooks = await api
                      .get<EnvironmentWebhook[]>(`/environments/${e.id}/webhooks/`)
                      .catch(() => [] as EnvironmentWebhook[]);
                    return { ...e, applicationName: app.name, webhookCount: webhooks.length };
                  }),
                ),
              )
              .catch(() => [] as EnvironmentRow[]),
          ),
        );
        setEnvironments(perApp.flat());
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "Failed to load webhooks.");
        setErrorDetail(err);
      }
    }
    load();
  }, [orgId]);

  if (!org && !error) return <PageLoading />;
  if (error && !org) return <ErrorBanner message={error} error={errorDetail} />;
  if (!org || !environments) return null;

  return (
    <div>
      <PageHeader
        title="Webhooks"
        breadcrumbs={[
          { label: "Organizations", href: "/orgs" },
          { label: org.name, href: `/orgs/${orgId}` },
          { label: "Developer", href: `/orgs/${orgId}/developer` },
          { label: "Webhooks" },
        ]}
        description="Webhooks are configured per-environment -- create and manage them from an environment's own Webhooks tab. This page is an overview of what's configured and how to verify a delivery."
      />
      <DeveloperNav orgId={orgId} active="webhooks" />

      <div className="space-y-8">
        <div>
          <h2 className="mb-3 text-sm font-semibold text-slate-600">Configured webhooks by environment</h2>
          {environments.length === 0 ? (
            <EmptyState
              title="No environments yet"
              description="Create an application and an environment first, then add a webhook from that environment's own page."
            />
          ) : (
            <Table>
              <THead>
                <Th>Environment</Th>
                <Th>Application</Th>
                <Th>Database bound</Th>
                <Th>Webhooks</Th>
                <Th>
                  <span className="sr-only">Manage</span>
                </Th>
              </THead>
              <tbody>
                {environments.map((env) => (
                  <TRow key={env.id}>
                    <Td className="font-medium text-slate-900">{env.name}</Td>
                    <Td className="text-slate-500">{env.applicationName}</Td>
                    <Td>
                      <Badge tone={env.database_status === "connected" ? "success" : "default"}>
                        {env.database_status === "connected" ? "Bound" : "Not bound"}
                      </Badge>
                    </Td>
                    <Td>{env.webhookCount}</Td>
                    <Td>
                      <Link
                        href={`/environments/${env.id}`}
                        className="inline-flex items-center gap-1 text-xs font-medium text-brand-600 hover:text-brand-500"
                      >
                        Manage <ExternalLink className="h-3 w-3" />
                      </Link>
                    </Td>
                  </TRow>
                ))}
              </tbody>
            </Table>
          )}
        </div>

        <div>
          <h2 className="mb-3 text-sm font-semibold text-slate-600">App Platform event types</h2>
          <p className="mb-3 text-xs text-slate-500">
            An App Platform instance only pushes events to webhooks on the environment its own runtime
            database is bound to (that environment&apos;s Database tab) -- an environment with no database
            binding has no possible subscribers, regardless of what webhooks exist there.
          </p>
          <Table>
            <THead>
              <Th>Event type</Th>
              <Th>Fires when</Th>
            </THead>
            <tbody>
              {EVENT_TYPES.map((e) => (
                <TRow key={e.type}>
                  <Td className="font-mono text-xs text-slate-700">{e.type}</Td>
                  <Td className="text-slate-500">{e.description}</Td>
                </TRow>
              ))}
            </tbody>
          </Table>
          <p className="mt-2 text-xs text-slate-400">
            An empty event-type list on a webhook subscribes it to every event type above.
          </p>
        </div>

        <CodeBlock title="Delivery payload" code={PAYLOAD_EXAMPLE} />
        <CodeBlock title="Verifying a delivery (Python)" code={VERIFY_EXAMPLE} />

        <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 text-xs text-slate-600">
          Every delivery is a <span className="font-mono">POST</span> with{" "}
          <span className="font-mono">Content-Type: application/json</span>, an{" "}
          <span className="font-mono">X-IntraForge-Event</span> header (the event type), and an{" "}
          <span className="font-mono">X-IntraForge-Signature</span> header --{" "}
          <span className="font-mono">sha256=&lt;hex&gt;</span>, an HMAC-SHA256 of the exact raw request
          body, keyed by the webhook&apos;s own signing secret (shown once, at creation time). Delivery is
          at-most-once and retried on failure by a background worker.
        </div>
      </div>
    </div>
  );
}

function CodeBlock({ title, code }: { title: string; code: string }) {
  return (
    <div>
      <div className="mb-2 flex items-center justify-between">
        <h2 className="text-sm font-semibold text-slate-700">{title}</h2>
        <CopyButton value={code} />
      </div>
      <pre className="overflow-x-auto rounded-2xl border border-slate-200 bg-slate-50 p-4 text-xs text-slate-700">
        {code}
      </pre>
    </div>
  );
}
