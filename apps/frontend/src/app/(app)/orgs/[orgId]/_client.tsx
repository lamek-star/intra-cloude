"use client";

import { useEffect, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { api, ApiError, type Membership, type Organization, type Team, type Workspace } from "@/lib/api";
import {
  Badge,
  Button,
  Card,
  EmptyState,
  ErrorBanner,
  Input,
  Label,
  LinkButton,
  Modal,
  PageHeader,
  PageLoading,
  Table,
  Td,
  Th,
  THead,
  TRow,
} from "@/components/ui";

export default function OrgDetailClient({ orgId }: { orgId: string }) {
  const router = useRouter();
  const [org, setOrg] = useState<Organization | null>(null);
  const [workspaces, setWorkspaces] = useState<Workspace[] | null>(null);
  const [members, setMembers] = useState<Membership[] | null>(null);
  const [teams, setTeams] = useState<Team[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [wsModalOpen, setWsModalOpen] = useState(false);
  const [memberModalOpen, setMemberModalOpen] = useState(false);

  async function load() {
    try {
      const [o, ws] = await Promise.all([
        api.get<Organization>(`/organizations/${orgId}/`),
        api.get<Workspace[]>(`/organizations/${orgId}/workspaces/`),
      ]);
      setOrg(o);
      setWorkspaces(ws);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load organization.");
      return;
    }
    // Members and teams require users.manage — a plain member may not have
    // it; fail soft.
    try {
      setMembers(await api.get<Membership[]>(`/organizations/${orgId}/members/`));
    } catch {
      setMembers([]);
    }
    try {
      setTeams(await api.get<Team[]>(`/organizations/${orgId}/teams/`));
    } catch {
      setTeams([]);
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
  if (!org) return null;

  return (
    <div>
      <PageHeader
        title={org.name}
        breadcrumbs={[{ label: "Organizations", href: "/orgs" }, { label: org.name }]}
        description={`/${org.slug}`}
        actions={
          <>
            <LinkButton href={`/orgs/${orgId}/teams`} variant="secondary" size="sm">
              Teams
            </LinkButton>
            <LinkButton href={`/orgs/${orgId}/audit`} variant="secondary" size="sm">
              Audit log
            </LinkButton>
          </>
        }
      />

      <div className="mb-8">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-slate-300">Workspaces</h2>
          <Button size="sm" onClick={() => setWsModalOpen(true)}>
            New workspace
          </Button>
        </div>
        {workspaces && workspaces.length === 0 ? (
          <EmptyState
            title="No workspaces yet"
            description="Workspaces group related projects — buckets and databases live inside a project."
            action={
              <Button size="sm" onClick={() => setWsModalOpen(true)}>
                New workspace
              </Button>
            }
          />
        ) : (
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {workspaces?.map((ws) => (
              <button
                key={ws.id}
                onClick={() => router.push(`/orgs/${orgId}/workspaces/${ws.id}`)}
                className="text-left"
              >
                <Card className="transition-colors hover:border-indigo-400/40 hover:bg-white/[0.05]">
                  <p className="font-medium text-white">{ws.name}</p>
                  <p className="mt-1 text-xs text-slate-500">
                    Created {new Date(ws.created_at).toLocaleDateString()}
                  </p>
                </Card>
              </button>
            ))}
          </div>
        )}
      </div>

      <div>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-slate-300">Members</h2>
          <Button size="sm" variant="secondary" onClick={() => setMemberModalOpen(true)}>
            Add member
          </Button>
        </div>
        {members && members.length > 0 ? (
          <Table>
            <THead>
              <Th>Email</Th>
              <Th>Name</Th>
              <Th>Status</Th>
              <Th>Team</Th>
            </THead>
            <tbody>
              {members.map((m) => (
                <TRow key={m.id}>
                  <Td>{m.user.email}</Td>
                  <Td className="text-slate-400">
                    {[m.user.first_name, m.user.last_name].filter(Boolean).join(" ") || "—"}
                  </Td>
                  <Td>
                    <Badge tone={m.status === "active" ? "success" : "warning"}>{m.status}</Badge>
                  </Td>
                  <Td className="text-slate-500">
                    {teams.find((t) => t.id === m.team)?.name ?? "—"}
                  </Td>
                </TRow>
              ))}
            </tbody>
          </Table>
        ) : (
          <p className="text-sm text-slate-500">
            No member list visible — you may not hold <code className="text-slate-400">users.manage</code> in
            this organization.
          </p>
        )}
      </div>

      <CreateWorkspaceModal
        open={wsModalOpen}
        orgId={orgId}
        onClose={() => setWsModalOpen(false)}
        onCreated={(ws) => {
          setWorkspaces((prev) => [...(prev ?? []), ws]);
          setWsModalOpen(false);
        }}
      />
      <AddMemberModal
        open={memberModalOpen}
        orgId={orgId}
        onClose={() => setMemberModalOpen(false)}
        onAdded={(m) => {
          setMembers((prev) => [...(prev ?? []), m]);
          setMemberModalOpen(false);
        }}
      />
    </div>
  );
}

function CreateWorkspaceModal({
  open,
  orgId,
  onClose,
  onCreated,
}: {
  open: boolean;
  orgId: string;
  onClose: () => void;
  onCreated: (ws: Workspace) => void;
}) {
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const ws = await api.post<Workspace>(`/organizations/${orgId}/workspaces/`, { name });
      setName("");
      onCreated(ws);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to create workspace.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Modal open={open} onClose={onClose} title="New workspace">
      <form onSubmit={handleSubmit} className="space-y-4">
        {error && <ErrorBanner message={error} />}
        <div>
          <Label htmlFor="ws-name">Name</Label>
          <Input
            id="ws-name"
            autoFocus
            required
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Engineering"
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

function AddMemberModal({
  open,
  orgId,
  onClose,
  onAdded,
}: {
  open: boolean;
  orgId: string;
  onClose: () => void;
  onAdded: (m: Membership) => void;
}) {
  const [email, setEmail] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const m = await api.post<Membership>(`/organizations/${orgId}/members/`, { email });
      setEmail("");
      onAdded(m);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to add member.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Modal open={open} onClose={onClose} title="Add member">
      <form onSubmit={handleSubmit} className="space-y-4">
        {error && <ErrorBanner message={error} />}
        <div>
          <Label htmlFor="member-email">Email of an existing user</Label>
          <Input
            id="member-email"
            type="email"
            autoFocus
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="teammate@example.com"
          />
          <p className="mt-1.5 text-xs text-slate-500">
            The user must already have an account — this doesn&apos;t send an invite email.
          </p>
        </div>
        <div className="flex justify-end gap-2">
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" disabled={submitting}>
            {submitting ? "..." : "Add"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
