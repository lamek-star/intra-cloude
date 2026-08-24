"use client";

import { useEffect, useState, type FormEvent } from "react";
import {
  api,
  ApiError,
  type Membership,
  type Organization,
  type Team,
} from "@/lib/api";
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
  Select,
} from "@/components/ui";

export default function TeamsClient({ orgId }: { orgId: string }) {
  const [org, setOrg] = useState<Organization | null>(null);
  const [teams, setTeams] = useState<Team[] | null>(null);
  const [members, setMembers] = useState<Membership[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [createOpen, setCreateOpen] = useState(false);
  const [addMemberTeam, setAddMemberTeam] = useState<Team | null>(null);

  async function load() {
    try {
      const [o, t] = await Promise.all([
        api.get<Organization>(`/organizations/${orgId}/`),
        api.get<Team[]>(`/organizations/${orgId}/teams/`),
      ]);
      setOrg(o);
      setTeams(t);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load teams.");
      return;
    }
    // Members require users.manage -- a plain member may not have it; fail soft,
    // same as the org detail page's own members list.
    try {
      setMembers(await api.get<Membership[]>(`/organizations/${orgId}/members/`));
    } catch {
      setMembers([]);
    }
  }

  useEffect(() => {
    // One-shot fetch-on-mount/param-change, not a state-sync loop.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [orgId]);

  async function removeFromTeam(team: Team, userId: string) {
    try {
      await api.del(`/teams/${team.id}/members/${userId}/`);
      setMembers((prev) =>
        prev ? prev.map((m) => (m.user.id === userId ? { ...m, team: null } : m)) : prev,
      );
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to remove team member.");
    }
  }

  if (!org && !error) return <PageLoading />;
  if (error && !org) return <ErrorBanner message={error} />;
  if (!org || !teams) return null;

  return (
    <div>
      <PageHeader
        title="Teams"
        breadcrumbs={[
          { label: "Organizations", href: "/orgs" },
          { label: org.name, href: `/orgs/${orgId}` },
          { label: "Teams" },
        ]}
        description="Group members within this organization."
        actions={
          <Button size="sm" onClick={() => setCreateOpen(true)}>
            New team
          </Button>
        }
      />

      {error && (
        <div className="mb-4">
          <ErrorBanner message={error} />
        </div>
      )}

      {teams.length === 0 ? (
        <EmptyState
          title="No teams yet"
          description="Create a team to group members within this organization."
          action={
            <Button size="sm" onClick={() => setCreateOpen(true)}>
              New team
            </Button>
          }
        />
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {teams.map((team) => {
            const teamMembers = members?.filter((m) => m.team === team.id) ?? [];
            return (
              <Card key={team.id}>
                <div className="mb-3 flex items-center justify-between">
                  <p className="font-medium text-white">{team.name}</p>
                  {members && (
                    <button
                      onClick={() => setAddMemberTeam(team)}
                      className="text-xs text-indigo-400 hover:text-indigo-300"
                    >
                      Add member
                    </button>
                  )}
                </div>
                {teamMembers.length === 0 ? (
                  <p className="text-xs text-slate-500">No members yet.</p>
                ) : (
                  <ul className="space-y-1.5">
                    {teamMembers.map((m) => (
                      <li
                        key={m.id}
                        className="flex items-center justify-between gap-2 text-sm text-slate-300"
                      >
                        <span className="truncate">{m.user.email}</span>
                        <button
                          onClick={() => removeFromTeam(team, m.user.id)}
                          className="text-xs text-slate-500 hover:text-red-400"
                        >
                          Remove
                        </button>
                      </li>
                    ))}
                  </ul>
                )}
              </Card>
            );
          })}
        </div>
      )}

      <CreateTeamModal
        open={createOpen}
        orgId={orgId}
        onClose={() => setCreateOpen(false)}
        onCreated={(team) => {
          setTeams((prev) => [...(prev ?? []), team]);
          setCreateOpen(false);
        }}
      />

      <AddTeamMemberModal
        key={addMemberTeam?.id ?? "none"}
        team={addMemberTeam}
        members={members ?? []}
        onClose={() => setAddMemberTeam(null)}
        onAdded={(membership) => {
          setMembers((prev) =>
            prev ? prev.map((m) => (m.id === membership.id ? membership : m)) : prev,
          );
          setAddMemberTeam(null);
        }}
      />
    </div>
  );
}

function CreateTeamModal({
  open,
  orgId,
  onClose,
  onCreated,
}: {
  open: boolean;
  orgId: string;
  onClose: () => void;
  onCreated: (team: Team) => void;
}) {
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const team = await api.post<Team>(`/organizations/${orgId}/teams/`, { name });
      setName("");
      onCreated(team);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to create team.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Modal open={open} onClose={onClose} title="New team">
      <form onSubmit={handleSubmit} className="space-y-4">
        {error && <ErrorBanner message={error} />}
        <div>
          <Label htmlFor="team-name">Name</Label>
          <Input
            id="team-name"
            autoFocus
            required
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Platform"
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

function AddTeamMemberModal({
  team,
  members,
  onClose,
  onAdded,
}: {
  team: Team | null;
  members: Membership[];
  onClose: () => void;
  onAdded: (m: Membership) => void;
}) {
  const candidates = team ? members.filter((m) => m.team !== team.id) : [];
  const [userId, setUserId] = useState(() => candidates[0]?.user.id ?? "");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!team || !userId) return;
    setError(null);
    setSubmitting(true);
    try {
      const membership = await api.post<Membership>(`/teams/${team.id}/members/`, {
        user_id: userId,
      });
      onAdded(membership);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to add team member.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Modal open={team !== null} onClose={onClose} title={`Add member to ${team?.name ?? ""}`}>
      <form onSubmit={handleSubmit} className="space-y-4">
        {error && <ErrorBanner message={error} />}
        {candidates.length === 0 ? (
          <p className="text-sm text-slate-500">
            Every organization member is already in this team, or there are no other members yet.
          </p>
        ) : (
          <div>
            <Label htmlFor="team-member">Member</Label>
            <Select id="team-member" value={userId} onChange={(e) => setUserId(e.target.value)}>
              {candidates.map((m) => (
                <option key={m.user.id} value={m.user.id}>
                  {m.user.email}
                </option>
              ))}
            </Select>
          </div>
        )}
        <div className="flex justify-end gap-2">
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" disabled={submitting || candidates.length === 0}>
            {submitting ? "..." : "Add"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
