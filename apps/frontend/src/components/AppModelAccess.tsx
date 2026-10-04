"use client";

import { useEffect, useState, type FormEvent } from "react";
import { api, ApiError, type Membership, type OrganizationalUnit, type Paginated } from "@/lib/api";
import { Button, ErrorBanner, Input, Label, Select } from "@/components/ui";
import { ShareSection } from "@/components/ShareSection";

type UnitGrant = {
  id: string; user: string; unit: string; level: "read" | "write"; expires_at: string | null;
};

export function AppModelAccess({ organizationId, modelId, hasUnitField }: {
  organizationId: string; modelId: string; hasUnitField: boolean;
}) {
  const [open, setOpen] = useState(false);
  return (
    <details className="my-6 rounded-lg border border-slate-200 p-4" onToggle={(event) => setOpen(event.currentTarget.open)}>
      <summary className="cursor-pointer text-sm font-semibold">Record access</summary>
      {open && <div className="mt-4 space-y-6">
        <p className="text-sm text-slate-600">
          Share all records in this model, or limit a member to one organizational unit.
          Organization roles and other grants can give broader access; a unit grant does not remove them.
          Attached files also require access to their storage bucket.
        </p>
        <ShareSection organizationId={organizationId} resourceType="app_model" resourceId={modelId} />
        {hasUnitField ? <UnitAccess organizationId={organizationId} modelId={modelId} /> :
          <p className="text-sm text-slate-500">Unit access requires an organizational-unit field on this model.</p>}
      </div>}
    </details>
  );
}

function UnitAccess({ organizationId, modelId }: { organizationId: string; modelId: string }) {
  const [grants, setGrants] = useState<UnitGrant[]>([]);
  const [members, setMembers] = useState<Membership[]>([]);
  const [units, setUnits] = useState<OrganizationalUnit[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [ready, setReady] = useState(false);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");

  useEffect(() => {
    let active = true;
    Promise.all([
      api.get<Paginated<UnitGrant>>(`/app-models/${modelId}/unit-grants/?limit=100`),
      api.get<Membership[]>(`/organizations/${organizationId}/members/`),
      api.get<OrganizationalUnit[]>(`/organizations/${organizationId}/units/`),
    ]).then(([page, people, departments]) => {
      if (!active) return;
      setGrants(page.results); setMembers(people.filter((member) => member.status === "active"));
      setUnits(departments); setReady(true);
      if (page.next) setNotice("Showing the first 100 unit grants. Additional grants remain active.");
    }).catch((err) => {
      if (active) setError(err instanceof ApiError && err.status === 403 ?
        "You don't have permission to manage unit access." : "Could not load unit access. Reopen this section to retry.");
    });
    return () => { active = false; };
  }, [modelId, organizationId]);

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    setBusy(true); setError(null); setNotice("");
    try {
      const expires = String(data.get("expires_at") ?? "");
      const grant = await api.post<UnitGrant>(`/app-models/${modelId}/unit-grants/`, {
        user_id: data.get("user"), unit_id: data.get("unit"), level: data.get("level"),
        expires_at: expires ? new Date(expires).toISOString() : null,
      });
      setGrants((previous) => [...previous.filter((entry) => entry.id !== grant.id), grant]);
      setNotice("Unit access saved."); form.reset();
    } catch (err) { setError(err instanceof ApiError ? err.message : "Could not save access."); }
    finally { setBusy(false); }
  }

  async function revoke(id: string) {
    setBusy(true); setError(null); setNotice("");
    try {
      await api.del(`/app-unit-grants/${id}/`);
      setGrants((previous) => previous.filter((entry) => entry.id !== id));
      setNotice("Unit grant revoked. Broader roles or shares, if present, still apply.");
    } catch (err) { setError(err instanceof ApiError ? err.message : "Could not revoke access."); }
    finally { setBusy(false); }
  }

  return <section aria-label="Unit access">
    <h3 className="mb-3 text-sm font-semibold">Access by organizational unit</h3>
    {error && <ErrorBanner message={error} />}
    {notice && <p role="status" className="my-2 text-sm text-slate-600">{notice}</p>}
    {ready && <>
      <ul className="mb-4 space-y-2">
        {grants.map((grant) => <li key={grant.id} className="flex flex-wrap items-center justify-between gap-2 text-sm">
          <span>{members.find((member) => member.user.id === grant.user)?.user.email ?? "Unavailable member"}
            {" · "}{units.find((unit) => unit.id === grant.unit)?.name ?? "Unavailable unit"}
            {" · "}{grant.level === "read" ? "View" : "View and edit"}
            {grant.expires_at && ` · until ${new Date(grant.expires_at).toLocaleString()}`}</span>
          <Button size="sm" variant="secondary" disabled={busy} onClick={() => revoke(grant.id)}>Revoke unit grant</Button>
        </li>)}
      </ul>
      {!grants.length && <p className="mb-3 text-sm text-slate-500">No unit grants yet.</p>}
      <form onSubmit={save} className="grid gap-3 sm:grid-cols-2">
        <div><Label htmlFor="unit-access-member">Member</Label><Select id="unit-access-member" name="user" required defaultValue="">
          <option value="" disabled>Choose a member</option>
          {members.map((member) => <option key={member.id} value={member.user.id}>{member.user.email}</option>)}
        </Select></div>
        <div><Label htmlFor="unit-access-unit">Organizational unit</Label><Select id="unit-access-unit" name="unit" required defaultValue="">
          <option value="" disabled>Choose a unit</option>
          {units.map((unit) => <option key={unit.id} value={unit.id}>{unit.name}</option>)}
        </Select></div>
        <div><Label htmlFor="unit-access-level">Access level</Label><Select id="unit-access-level" name="level" defaultValue="read">
          <option value="read">View records</option><option value="write">View and edit records</option>
        </Select></div>
        <div><Label htmlFor="unit-access-expiry">Expires at (optional, local time)</Label><Input id="unit-access-expiry" name="expires_at" type="datetime-local" /></div>
        <Button type="submit" disabled={busy || !members.length || !units.length}>{busy ? "Saving…" : "Grant unit access"}</Button>
      </form>
    </>}
  </section>;
}
