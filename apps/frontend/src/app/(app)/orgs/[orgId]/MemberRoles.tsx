"use client";

import { useState } from "react";
import { X } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { Badge, Button, Select } from "@/components/ui";

/** A role this organization can give its members (GET /organizations/{id}/roles/). */
export type RoleOption = { slug: string; name: string; summary: string; administrative: boolean };
export type OrganizationRoles = {
  roles: RoleOption[];
  assignments: { membership_id: string; role_slug: string }[];
};

/** The roles one member holds, with "give" and "take away" — shown only to people who may manage
 * roles (the roles endpoint answers 403 to everyone else, and the page then shows no controls). */
export function MemberRoles({
  orgId,
  membershipId,
  who,
  roles,
  held,
  onChange,
}: {
  orgId: string;
  membershipId: string;
  who: string;
  roles: RoleOption[];
  held: string[];
  onChange: (held: string[]) => void;
}) {
  const [choice, setChoice] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const byslug = new Map(roles.map((r) => [r.slug, r]));
  const available = roles.filter((r) => !held.includes(r.slug));
  const chosen = choice ? byslug.get(choice) : undefined;

  async function give() {
    if (!choice) return;
    setBusy(true);
    setError(null);
    try {
      await api.post(`/organizations/${orgId}/members/${membershipId}/role/`, { role_slug: choice });
      onChange([...held, choice]);
      setChoice("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "The role could not be given.");
    } finally {
      setBusy(false);
    }
  }

  async function takeAway(slug: string) {
    const name = byslug.get(slug)?.name ?? slug;
    if (!window.confirm(`Take the role "${name}" away from ${who}?`)) return;
    setBusy(true);
    setError(null);
    try {
      await api.del(`/organizations/${orgId}/members/${membershipId}/roles/${slug}/`);
      onChange(held.filter((s) => s !== slug));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "The role could not be taken away.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-1.5">
      <div className="flex flex-wrap gap-1.5">
        {held.length === 0 && <span className="text-xs text-amber-700">No role — can open nothing yet</span>}
        {held.map((slug) => (
          <span key={slug} className="inline-flex items-center gap-0.5">
            <Badge tone={byslug.get(slug)?.administrative ? "warning" : "info"}>{byslug.get(slug)?.name ?? slug}</Badge>
            <button
              type="button"
              disabled={busy}
              onClick={() => void takeAway(slug)}
              aria-label={`Take away ${byslug.get(slug)?.name ?? slug} from ${who}`}
              className="rounded p-0.5 text-text-muted hover:bg-slate-100 hover:text-red-600 disabled:opacity-50"
            >
              <X size={12} aria-hidden="true" />
            </button>
          </span>
        ))}
      </div>
      {available.length > 0 && (
        <div className="flex items-center gap-1.5">
          <Select
            aria-label={`Give ${who} a role`}
            value={choice}
            disabled={busy}
            onChange={(e) => setChoice(e.target.value)}
            className="max-w-56 py-1 text-xs"
          >
            <option value="">Give a role…</option>
            {available.map((r) => (
              <option key={r.slug} value={r.slug}>
                {r.name}
              </option>
            ))}
          </Select>
          <Button size="sm" variant="secondary" disabled={!choice || busy} onClick={() => void give()}>
            Give
          </Button>
        </div>
      )}
      {chosen && <p className="max-w-72 text-xs text-slate-500">{chosen.summary}</p>}
      {error && <p className="text-xs text-red-600">{error}</p>}
    </div>
  );
}
