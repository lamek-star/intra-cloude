"use client";

import { useEffect, useState, type FormEvent } from "react";
import { Share2, ShieldOff } from "lucide-react";
import {
  api,
  ApiError,
  type Membership,
  type ShareGrant,
  type Team,
} from "@/lib/api";
import {
  Badge,
  Button,
  ErrorBanner,
  Label,
  Modal,
  Select,
  Table,
  Td,
  Th,
  THead,
  TRow,
} from "@/components/ui";

const LEVEL_TONE = { read: "default", write: "info", admin: "warning" } as const;

/** Drop into any resource's detail page to manage who it's shared with.
 * Enforcement is entirely the existing ResourceGrant/has_permission
 * mechanism (sharing/models.py's ShareGrant docstring) -- this is the
 * human-facing "who has access" record, not a second permission check.
 *
 * The list endpoint has no server-side resource filter (sharing/views.py
 * returns every ShareGrant for the organization), so this filters
 * client-side. Fine at the scale a single org's share grants reach
 * today; if that stops being true, add a resource_type/resource_id query
 * param to ShareGrantListCreateView.get rather than paginating around it
 * here (docs/implementation/DECISIONS.md). */
export function ShareSection({
  organizationId,
  resourceType,
  resourceId,
}: {
  organizationId: string;
  resourceType: string;
  resourceId: string;
}) {
  const [shares, setShares] = useState<ShareGrant[] | null>(null);
  const [members, setMembers] = useState<Membership[]>([]);
  const [teams, setTeams] = useState<Team[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [modalOpen, setModalOpen] = useState(false);

  async function load() {
    try {
      const all = await api.get<ShareGrant[]>(`/organizations/${organizationId}/shares/`);
      setShares(
        all.filter(
          (s) => s.resource_type === resourceType && s.resource_id === resourceId && !s.revoked_at,
        ),
      );
    } catch (err) {
      setShares([]);
      setError(
        err instanceof ApiError && err.status === 403
          ? "You don't have permission to manage sharing for this resource."
          : "Failed to load sharing.",
      );
    }
    api
      .get<Membership[]>(`/organizations/${organizationId}/members/`)
      .then(setMembers)
      .catch(() => {});
    api
      .get<Team[]>(`/organizations/${organizationId}/teams/`)
      .then(setTeams)
      .catch(() => {});
  }

  useEffect(() => {
    // One-shot fetch-on-mount/param-change, not a state-sync loop.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [organizationId, resourceType, resourceId]);

  async function revoke(share: ShareGrant) {
    setError(null);
    try {
      await api.del(`/shares/${share.id}/`);
      setShares((prev) => prev?.filter((s) => s.id !== share.id) ?? prev);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to revoke share.");
    }
  }

  function principalLabel(share: ShareGrant): string {
    if (share.principal_type === "organization") return "Everyone in this organization";
    if (share.principal_type === "team") {
      return teams.find((t) => t.id === share.team)?.name ?? "A team";
    }
    return members.find((m) => m.user.id === share.user)?.user.email ?? "A user";
  }

  return (
    <section>
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-sm font-semibold text-slate-300">Sharing</h2>
        {shares && (
          <Button size="sm" variant="secondary" onClick={() => setModalOpen(true)}>
            <Share2 className="h-3.5 w-3.5" />
            Share
          </Button>
        )}
      </div>
      {error && (
        <div className="mb-3">
          <ErrorBanner message={error} />
        </div>
      )}
      {shares && shares.length > 0 && (
        <Table>
          <THead>
            <Th>Shared with</Th>
            <Th>Level</Th>
            <Th>Expires</Th>
            <Th>
              <span className="sr-only">Actions</span>
            </Th>
          </THead>
          <tbody>
            {shares.map((s) => (
              <TRow key={s.id}>
                <Td className="font-medium text-white">{principalLabel(s)}</Td>
                <Td>
                  <Badge tone={LEVEL_TONE[s.level]}>{s.level}</Badge>
                </Td>
                <Td className="text-slate-500">
                  {s.expires_at ? new Date(s.expires_at).toLocaleString() : "Never"}
                </Td>
                <Td>
                  <button
                    onClick={() => revoke(s)}
                    className="inline-flex items-center gap-1 text-xs text-slate-500 hover:text-red-400"
                  >
                    <ShieldOff className="h-3.5 w-3.5" />
                    Revoke
                  </button>
                </Td>
              </TRow>
            ))}
          </tbody>
        </Table>
      )}
      {shares && shares.length === 0 && !error && (
        <p className="text-sm text-slate-500">Not shared with anyone yet.</p>
      )}

      <ShareModal
        open={modalOpen}
        organizationId={organizationId}
        resourceType={resourceType}
        resourceId={resourceId}
        members={members}
        teams={teams}
        onClose={() => setModalOpen(false)}
        onCreated={(share) => {
          setShares((prev) => [share, ...(prev ?? [])]);
          setModalOpen(false);
        }}
      />
    </section>
  );
}

function ShareModal({
  open,
  organizationId,
  resourceType,
  resourceId,
  members,
  teams,
  onClose,
  onCreated,
}: {
  open: boolean;
  organizationId: string;
  resourceType: string;
  resourceId: string;
  members: Membership[];
  teams: Team[];
  onClose: () => void;
  onCreated: (share: ShareGrant) => void;
}) {
  const [principalType, setPrincipalType] = useState<"user" | "team" | "organization">("user");
  const [userId, setUserId] = useState(() => members[0]?.user.id ?? "");
  const [teamId, setTeamId] = useState(() => teams[0]?.id ?? "");
  const [level, setLevel] = useState<"read" | "write" | "admin">("read");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const share = await api.post<ShareGrant>(`/organizations/${organizationId}/shares/`, {
        resource_type: resourceType,
        resource_id: resourceId,
        principal_type: principalType,
        level,
        user_id: principalType === "user" ? userId : null,
        team_id: principalType === "team" ? teamId : null,
      });
      onCreated(share);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to share.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Modal open={open} onClose={onClose} title="Share">
      <form onSubmit={handleSubmit} className="space-y-4">
        {error && <ErrorBanner message={error} />}
        <div>
          <Label htmlFor="share-principal-type">Share with</Label>
          <Select
            id="share-principal-type"
            value={principalType}
            onChange={(e) => setPrincipalType(e.target.value as typeof principalType)}
          >
            <option value="user">A specific member</option>
            <option value="team">A team</option>
            <option value="organization">Everyone in this organization</option>
          </Select>
        </div>
        {principalType === "user" && (
          <div>
            <Label htmlFor="share-user">Member</Label>
            {members.length === 0 ? (
              <p className="text-sm text-slate-500">No other members to share with.</p>
            ) : (
              <Select id="share-user" value={userId} onChange={(e) => setUserId(e.target.value)}>
                {members.map((m) => (
                  <option key={m.user.id} value={m.user.id}>
                    {m.user.email}
                  </option>
                ))}
              </Select>
            )}
          </div>
        )}
        {principalType === "team" && (
          <div>
            <Label htmlFor="share-team">Team</Label>
            {teams.length === 0 ? (
              <p className="text-sm text-slate-500">No teams in this organization yet.</p>
            ) : (
              <Select id="share-team" value={teamId} onChange={(e) => setTeamId(e.target.value)}>
                {teams.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.name}
                  </option>
                ))}
              </Select>
            )}
          </div>
        )}
        <div>
          <Label htmlFor="share-level">Access level</Label>
          <Select id="share-level" value={level} onChange={(e) => setLevel(e.target.value as typeof level)}>
            <option value="read">Read</option>
            <option value="write">Write</option>
            <option value="admin">Admin</option>
          </Select>
        </div>
        <div className="flex justify-end gap-2">
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button
            type="submit"
            disabled={
              submitting ||
              (principalType === "user" && members.length === 0) ||
              (principalType === "team" && teams.length === 0)
            }
          >
            {submitting ? "..." : "Share"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
