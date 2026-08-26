"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Bot,
  Check,
  CheckCircle2,
  Database,
  Folder,
  Globe,
  Monitor,
  Package,
  Server,
  Smartphone,
  Workflow,
  XCircle,
  type LucideIcon,
} from "lucide-react";
import {
  api,
  ApiError,
  type Application,
  type ApplicationCredential,
  type Organization,
} from "@/lib/api";
import { listOrgResources, type OrgResource } from "@/lib/org-resources";
import {
  Button,
  Card,
  CopyButton,
  ErrorBanner,
  Input,
  Label,
  PageHeader,
  PageLoading,
  SecretReveal,
  Spinner,
  Textarea,
} from "@/components/ui";
import { DeveloperNav } from "@/components/DeveloperNav";

type AppType = {
  key: string;
  label: string;
  icon: LucideIcon;
  description: string;
  language: "javascript" | "python";
};

const APP_TYPES: AppType[] = [
  { key: "website", label: "Website", icon: Globe, description: "A server-rendered or static site with backend access.", language: "javascript" },
  { key: "backend", label: "Backend Service", icon: Server, description: "An API, worker, or other server-side process.", language: "python" },
  { key: "mobile", label: "Mobile App", icon: Smartphone, description: "iOS/Android app calling through your own backend.", language: "javascript" },
  { key: "desktop", label: "Desktop App", icon: Monitor, description: "A native or Electron-style desktop application.", language: "javascript" },
  { key: "ai", label: "AI Application", icon: Bot, description: "An assistant or agent that reads organization data.", language: "python" },
  { key: "automation", label: "Automation", icon: Workflow, description: "A scheduled job, script, or internal tool.", language: "python" },
  { key: "other", label: "Other", icon: Package, description: "Something else entirely.", language: "javascript" },
];

const STEPS = ["Type", "Identity", "Data access", "Credential", "Connect"] as const;

export default function ConnectApplicationClient({ orgId }: { orgId: string }) {
  const router = useRouter();
  const [org, setOrg] = useState<Organization | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [step, setStep] = useState(0);

  const [appType, setAppType] = useState<string>("website");
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [application, setApplication] = useState<Application | null>(null);

  const [resources, setResources] = useState<OrgResource[] | null>(null);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [accessLevel, setAccessLevel] = useState<"read" | "write">("read");
  const [grantError, setGrantError] = useState<string | null>(null);
  const [grantingAccess, setGrantingAccess] = useState(false);

  const [credential, setCredential] = useState<ApplicationCredential | null>(null);
  const [issuingCredential, setIssuingCredential] = useState(false);
  const [credentialError, setCredentialError] = useState<string | null>(null);

  const [testResult, setTestResult] = useState<"idle" | "running" | "ok" | "failed">("idle");
  const [testDetail, setTestDetail] = useState<string | null>(null);

  useEffect(() => {
    api
      .get<Organization>(`/organizations/${orgId}/`)
      .then(setOrg)
      .catch((err) => setLoadError(err instanceof ApiError ? err.message : "Failed to load organization."));
  }, [orgId]);

  useEffect(() => {
    if (step !== 2 || resources !== null) return;
    (async () => {
      try {
        setResources(await listOrgResources(orgId));
      } catch {
        setResources([]);
      }
    })();
  }, [step, orgId, resources]);

  if (!org && !loadError) return <PageLoading />;
  if (loadError && !org) return <ErrorBanner message={loadError} />;
  if (!org) return null;

  const selectedType = APP_TYPES.find((t) => t.key === appType)!;

  async function handleCreateApplication() {
    setLoadError(null);
    try {
      const app = await api.post<Application>(`/organizations/${orgId}/applications/`, {
        name,
        description: description || `${selectedType.label} — connected via the wizard`,
      });
      setApplication(app);
      setStep(2);
    } catch (err) {
      setLoadError(err instanceof ApiError ? err.message : "Failed to create application.");
    }
  }

  async function handleGrantAccess() {
    if (!application) return;
    setGrantError(null);
    setGrantingAccess(true);
    try {
      const chosen = resources?.filter((r) => selected.has(`${r.kind}:${r.id}`)) ?? [];
      await Promise.all(
        chosen.flatMap((r) => {
          const resourceType = r.kind === "bucket" ? "storage.bucket" : "databases.tenant_database";
          const codes =
            accessLevel === "write"
              ? r.kind === "bucket"
                ? ["storage.read", "storage.write"]
                : ["database.read", "database.write"]
              : r.kind === "bucket"
                ? ["storage.read"]
                : ["database.read"];
          return codes.map((permission_code) =>
            api.post(`/applications/${application.id}/resource-grants/`, {
              permission_code,
              resource_type: resourceType,
              resource_id: r.id,
            }),
          );
        }),
      );
      setStep(3);
    } catch (err) {
      setGrantError(err instanceof ApiError ? err.message : "Failed to grant access.");
    } finally {
      setGrantingAccess(false);
    }
  }

  async function handleIssueCredential() {
    if (!application) return;
    setCredentialError(null);
    setIssuingCredential(true);
    try {
      const cred = await api.post<ApplicationCredential>(`/applications/${application.id}/credentials/`);
      setCredential(cred);
      // Stays on this step -- the secret is shown exactly once and the
      // backend never returns it again, so the user must see and copy
      // it here before advancing (the step-3 JSX below renders
      // SecretReveal once `credential` is set, with its own "Next").
    } catch (err) {
      setCredentialError(err instanceof ApiError ? err.message : "Failed to issue credential.");
    } finally {
      setIssuingCredential(false);
    }
  }

  async function handleTestConnection() {
    const chosen = resources?.filter((r) => selected.has(`${r.kind}:${r.id}`)) ?? [];
    const target = chosen[0];
    if (!credential?.secret || !target) return;
    setTestResult("running");
    setTestDetail(null);

    // Bucket file listing is genuinely gated by the storage.read grant
    // (storage/views.py's FileListCreateView), so it's a real proof.
    // A tenant database's own detail/table-list endpoints are visible to
    // any org member regardless of grants (Unit 4b's finding) -- the
    // grant only actually gates row data on a specific table, so that's
    // what has to be tested for the result to mean anything.
    let path = target.kind === "bucket" ? `/api/v1/buckets/${target.id}/files/` : null;
    if (target.kind === "database") {
      try {
        const tables = await api.get<{ id: string }[]>(`/tenant-databases/${target.id}/tables/`);
        if (tables.length === 0) {
          setTestResult("failed");
          setTestDetail(`"${target.name}" has no tables yet -- create one to test row-level access.`);
          return;
        }
        path = `/api/v1/tables/${tables[0].id}/rows/`;
      } catch {
        setTestResult("failed");
        setTestDetail("Could not look up this database's tables.");
        return;
      }
    }
    if (!path) return;

    try {
      const res = await fetch(path, { headers: { Authorization: `Bearer ${credential.secret}` } });
      if (res.ok) {
        setTestResult("ok");
        setTestDetail(`${res.status} from ${path} -- the credential can reach "${target.name}".`);
      } else {
        setTestResult("failed");
        setTestDetail(`${res.status} from ${path}.`);
      }
    } catch {
      setTestResult("failed");
      setTestDetail("Network error calling the API.");
    }
  }

  return (
    <div>
      <PageHeader
        title="Connect application"
        breadcrumbs={[
          { label: "Organizations", href: "/orgs" },
          { label: org.name, href: `/orgs/${orgId}` },
          { label: "Developer", href: `/orgs/${orgId}/developer` },
          { label: "Applications", href: `/orgs/${orgId}/developer/applications` },
          { label: "Connect" },
        ]}
      />
      <DeveloperNav orgId={orgId} active="applications" />

      <Stepper current={step} />

      {loadError && (
        <div className="mb-4">
          <ErrorBanner message={loadError} />
        </div>
      )}

      <div className="mt-6">
        {step === 0 && (
          <StepCard title="What are you connecting?" description="This only tailors the example code at the end — it isn't stored.">
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {APP_TYPES.map((t) => (
                <button key={t.key} onClick={() => setAppType(t.key)} className="text-left">
                  <Card
                    className={`h-full transition-colors ${
                      appType === t.key ? "border-indigo-400 bg-indigo-50/40" : "hover:border-indigo-400/40 hover:bg-slate-50"
                    }`}
                  >
                    <t.icon className={`h-5 w-5 ${appType === t.key ? "text-indigo-600" : "text-slate-400"}`} />
                    <p className="mt-2 text-sm font-medium text-slate-900">{t.label}</p>
                    <p className="mt-1 text-xs text-slate-500">{t.description}</p>
                  </Card>
                </button>
              ))}
            </div>
            <div className="mt-5 flex justify-end">
              <Button onClick={() => setStep(1)}>Next</Button>
            </div>
          </StepCard>
        )}

        {step === 1 && (
          <StepCard title="Name this application" description="You can change these later from the application's page.">
            <div className="space-y-4">
              <div>
                <Label htmlFor="connect-name">Name</Label>
                <Input
                  id="connect-name"
                  autoFocus
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder={`${org.name} ${selectedType.label}`}
                />
              </div>
              <div>
                <Label htmlFor="connect-description">Description (optional)</Label>
                <Textarea
                  id="connect-description"
                  rows={2}
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="What this application does and who owns it."
                />
              </div>
            </div>
            <div className="mt-5 flex justify-between">
              <Button variant="ghost" onClick={() => setStep(0)}>
                Back
              </Button>
              <Button onClick={handleCreateApplication} disabled={!name.trim()}>
                Create application
              </Button>
            </div>
          </StepCard>
        )}

        {step === 2 && (
          <StepCard
            title="Choose what it can access"
            description="Grants a scoped ResourceGrant per selection — this application can reach nothing else."
          >
            {grantError && (
              <div className="mb-3">
                <ErrorBanner message={grantError} />
              </div>
            )}
            {resources === null ? (
              <div className="flex items-center gap-2 text-sm text-slate-400">
                <Spinner className="h-4 w-4" /> Loading storage and databases…
              </div>
            ) : resources.length === 0 ? (
              <p className="text-sm text-slate-500">
                No buckets or databases exist in this organization yet. You can grant access later from the
                application&apos;s page once you&apos;ve created some.
              </p>
            ) : (
              <>
                <fieldset className="m-0 mb-4 flex items-center gap-4 border-0 p-0 text-sm">
                  <legend className="p-0 text-slate-600">Access level:</legend>
                  <label className="flex items-center gap-1.5">
                    <input
                      type="radio"
                      name="access-level"
                      checked={accessLevel === "read"}
                      onChange={() => setAccessLevel("read")}
                    />
                    Read only
                  </label>
                  <label className="flex items-center gap-1.5">
                    <input
                      type="radio"
                      name="access-level"
                      checked={accessLevel === "write"}
                      onChange={() => setAccessLevel("write")}
                    />
                    Read &amp; write
                  </label>
                </fieldset>
                <div className="max-h-80 space-y-1.5 overflow-y-auto">
                  {resources.map((r) => {
                    const id = `${r.kind}:${r.id}`;
                    const isSelected = selected.has(id);
                    return (
                      <label
                        key={id}
                        className={`flex cursor-pointer items-center gap-3 rounded-lg border px-3 py-2.5 ${
                          isSelected ? "border-indigo-300 bg-indigo-50/40" : "border-slate-200 hover:bg-slate-50"
                        }`}
                      >
                        <input
                          type="checkbox"
                          checked={isSelected}
                          onChange={(e) => {
                            const next = new Set(selected);
                            if (e.target.checked) next.add(id);
                            else next.delete(id);
                            setSelected(next);
                          }}
                        />
                        {r.kind === "bucket" ? (
                          <Folder className="h-4 w-4 text-indigo-600" />
                        ) : (
                          <Database className="h-4 w-4 text-indigo-600" />
                        )}
                        <span className="min-w-0 flex-1">
                          <span className="block text-sm font-medium text-slate-800">{r.name}</span>
                          <span className="block text-xs text-slate-400">{r.projectName}</span>
                        </span>
                      </label>
                    );
                  })}
                </div>
              </>
            )}
            <div className="mt-5 flex justify-between">
              <Button variant="ghost" onClick={() => setStep(1)}>
                Back
              </Button>
              <div className="flex gap-2">
                {resources && resources.length > 0 && selected.size === 0 && (
                  <Button variant="secondary" onClick={() => setStep(3)}>
                    Skip for now
                  </Button>
                )}
                <Button
                  onClick={handleGrantAccess}
                  disabled={grantingAccess || (resources !== null && resources.length > 0 && selected.size === 0)}
                >
                  {grantingAccess ? "Granting…" : `Grant access${selected.size ? ` (${selected.size})` : ""}`}
                </Button>
              </div>
            </div>
          </StepCard>
        )}

        {step === 3 && (
          <StepCard title="Create a credential" description="The secret is shown exactly once — copy it before continuing.">
            {credentialError && (
              <div className="mb-3">
                <ErrorBanner message={credentialError} />
              </div>
            )}
            {!credential ? (
              <Button onClick={handleIssueCredential} disabled={issuingCredential}>
                {issuingCredential ? "Generating…" : "Generate credential"}
              </Button>
            ) : (
              <div className="space-y-4">
                <SecretReveal secret={credential.secret ?? ""} />
                <Button onClick={() => setStep(4)}>Next</Button>
              </div>
            )}
            <div className="mt-5">
              <Button variant="ghost" onClick={() => setStep(2)}>
                Back
              </Button>
            </div>
          </StepCard>
        )}

        {step === 4 && application && (
          <StepCard title="Connect it" description="Use this credential from your server — never from browser JavaScript.">
            <ConnectSnippet language={selectedType.language} secret={credential?.secret} />

            {resources !== null && selected.size > 0 && (
              <div className="mt-5">
                <Button variant="secondary" onClick={handleTestConnection} disabled={testResult === "running"}>
                  {testResult === "running" ? "Testing…" : "Test connection"}
                </Button>
                {testResult === "ok" && (
                  <p className="mt-2 flex items-center gap-1.5 text-sm text-emerald-700">
                    <CheckCircle2 className="h-4 w-4" /> {testDetail}
                  </p>
                )}
                {testResult === "failed" && (
                  <p className="mt-2 flex items-center gap-1.5 text-sm text-red-700">
                    <XCircle className="h-4 w-4" /> {testDetail}
                  </p>
                )}
              </div>
            )}

            <div className="mt-6 flex justify-between border-t border-slate-100 pt-5">
              <Button variant="ghost" onClick={() => setStep(3)}>
                Back
              </Button>
              <Button onClick={() => router.push(`/applications/${application.id}`)}>
                <Check className="h-3.5 w-3.5" />
                Done — open application
              </Button>
            </div>
          </StepCard>
        )}
      </div>
    </div>
  );
}

function Stepper({ current }: { current: number }) {
  return (
    <div className="flex items-center gap-2 overflow-x-auto pb-1" role="list" aria-label="Wizard progress">
      {STEPS.map((label, i) => (
        <div key={label} role="listitem" className="flex shrink-0 items-center gap-2">
          <div
            aria-hidden="true"
            className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs font-medium ${
              i < current
                ? "bg-indigo-600 text-white"
                : i === current
                  ? "bg-indigo-100 text-indigo-700 ring-2 ring-indigo-300"
                  : "bg-slate-100 text-slate-400"
            }`}
          >
            {i < current ? <Check className="h-3.5 w-3.5" /> : i + 1}
          </div>
          <span
            aria-current={i === current ? "step" : undefined}
            className={`shrink-0 text-xs font-medium ${i <= current ? "text-slate-700" : "text-slate-400"}`}
          >
            {label}
          </span>
          {i < STEPS.length - 1 && <div aria-hidden="true" className="mx-1 h-px w-6 shrink-0 bg-slate-200" />}
        </div>
      ))}
    </div>
  );
}

function StepCard({
  title,
  description,
  children,
}: {
  title: string;
  description?: string;
  children: React.ReactNode;
}) {
  return (
    <Card>
      <h2 className="text-base font-semibold text-slate-900">{title}</h2>
      {description && <p className="mt-1 text-sm text-slate-500">{description}</p>}
      <div className="mt-4">{children}</div>
    </Card>
  );
}

function ConnectSnippet({ language, secret }: { language: "javascript" | "python"; secret?: string }) {
  const token = secret ?? "<credential-secret>";
  const code =
    language === "javascript"
      ? `const res = await fetch(
  "https://<your-intracloud-host>/api/v1/...",
  { headers: { Authorization: "Bearer " + process.env.INTRACLOUD_CREDENTIAL } }
);`
      : `import os, requests

res = requests.get(
    "https://<your-intracloud-host>/api/v1/...",
    headers={"Authorization": f"Bearer {os.environ['INTRACLOUD_CREDENTIAL']}"},
)`;
  return (
    <div>
      <div className="mb-2 flex items-center justify-between">
        <span className="text-xs font-medium text-slate-500">
          {language === "javascript" ? "JavaScript / TypeScript" : "Python"} — server-side only
        </span>
        <CopyButton value={code.replace("process.env.INTRACLOUD_CREDENTIAL", `"${token}"`)} />
      </div>
      <pre className="overflow-x-auto rounded-2xl border border-slate-200 bg-slate-50 p-4 text-xs text-slate-700">
        {code}
      </pre>
    </div>
  );
}
