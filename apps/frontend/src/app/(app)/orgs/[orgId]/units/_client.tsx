"use client";

import { useEffect, useMemo, useState, type FormEvent } from "react";
import {
  api,
  ApiError,
  type Membership,
  type Organization,
  type OrganizationalUnit,
  type UnitMembership,
} from "@/lib/api";
import {
  Badge,
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
import { useConfirm } from "@/components/ConfirmProvider";

type TreeNode = OrganizationalUnit & { children: TreeNode[] };

function buildTree(units: OrganizationalUnit[]): TreeNode[] {
  const byId = new Map<string, TreeNode>(units.map((u) => [u.id, { ...u, children: [] }]));
  const roots: TreeNode[] = [];
  for (const unit of byId.values()) {
    if (unit.parent && byId.has(unit.parent)) {
      byId.get(unit.parent)!.children.push(unit);
    } else {
      roots.push(unit);
    }
  }
  return roots;
}

// Every id reachable from `unitId` via `children` -- used to keep the
// reparent dropdown from ever offering a choice the server would reject
// as a cycle anyway (the server remains the real enforcement point).
function descendantIds(units: OrganizationalUnit[], unitId: string): Set<string> {
  const childrenOf = new Map<string | null, string[]>();
  for (const u of units) {
    const list = childrenOf.get(u.parent) ?? [];
    list.push(u.id);
    childrenOf.set(u.parent, list);
  }
  const seen = new Set<string>();
  const stack = [...(childrenOf.get(unitId) ?? [])];
  while (stack.length > 0) {
    const id = stack.pop()!;
    if (seen.has(id)) continue;
    seen.add(id);
    stack.push(...(childrenOf.get(id) ?? []));
  }
  return seen;
}

export default function UnitsClient({ orgId }: { orgId: string }) {
  const [org, setOrg] = useState<Organization | null>(null);
  const [units, setUnits] = useState<OrganizationalUnit[] | null>(null);
  const [orgMembers, setOrgMembers] = useState<Membership[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [errorDetail, setErrorDetail] = useState<unknown>(null);
  const [createParent, setCreateParent] = useState<OrganizationalUnit | null | undefined>(undefined);
  const [editUnit, setEditUnit] = useState<OrganizationalUnit | null>(null);
  const [membersUnit, setMembersUnit] = useState<OrganizationalUnit | null>(null);
  const confirm = useConfirm();

  async function load() {
    try {
      const [o, u] = await Promise.all([
        api.get<Organization>(`/organizations/${orgId}/`),
        api.get<OrganizationalUnit[]>(`/organizations/${orgId}/units/`),
      ]);
      setOrg(o);
      setUnits(u);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load units.");
      setErrorDetail(err);
      return;
    }
    // Org membership list requires users.manage -- a plain member may not
    // have it; fail soft, matching the Teams page's own convention.
    try {
      setOrgMembers(await api.get<Membership[]>(`/organizations/${orgId}/members/`));
    } catch {
      setOrgMembers([]);
    }
  }

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [orgId]);

  const tree = useMemo(() => buildTree(units ?? []), [units]);
  const hasChildren = (unitId: string) => (units ?? []).some((u) => u.parent === unitId);

  async function deleteUnit(unit: OrganizationalUnit) {
    if (
      !(await confirm({
        title: `Delete "${unit.name}"?`,
        description: "This cannot be undone.",
        confirmLabel: "Delete",
        danger: true,
      }))
    )
      return;
    try {
      await api.del(`/units/${unit.id}/`);
      setUnits((prev) => (prev ? prev.filter((u) => u.id !== unit.id) : prev));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to delete unit.");
      setErrorDetail(err);
    }
  }

  if (!org && !error) return <PageLoading />;
  if (error && !org) return <ErrorBanner message={error} error={errorDetail} />;
  if (!org || !units) return null;

  function renderNode(node: TreeNode, depth: number) {
    return (
      <div key={node.id}>
        <div
          className="flex items-center justify-between gap-3 border-b border-slate-100 py-2.5 last:border-b-0"
          style={{ paddingLeft: `${depth * 1.5}rem` }}
        >
          <div className="flex min-w-0 items-center gap-2">
            <span className="truncate text-sm font-medium text-slate-900">{node.name}</span>
            <Badge>{node.unit_type}</Badge>
          </div>
          <div className="flex shrink-0 gap-3 text-xs">
            <button
              onClick={() => setCreateParent(node)}
              className="text-brand-600 hover:text-brand-500"
            >
              Add sub-unit
            </button>
            <button
              onClick={() => setMembersUnit(node)}
              className="text-brand-600 hover:text-brand-500"
            >
              Members
            </button>
            <button
              onClick={() => setEditUnit(node)}
              className="text-slate-500 hover:text-slate-700"
            >
              Edit
            </button>
            <button
              onClick={() => deleteUnit(node)}
              disabled={hasChildren(node.id)}
              title={hasChildren(node.id) ? "Delete or move its sub-units first." : undefined}
              className="text-slate-500 hover:text-red-600 disabled:cursor-not-allowed disabled:opacity-40"
            >
              Delete
            </button>
          </div>
        </div>
        {node.children.map((child) => renderNode(child, depth + 1))}
      </div>
    );
  }

  return (
    <div>
      <PageHeader
        title="Organizational units"
        breadcrumbs={[
          { label: "Organizations", href: "/orgs" },
          { label: org.name, href: `/orgs/${orgId}` },
          { label: "Units" },
        ]}
        description="Branches, campuses, departments, warehouses, or any other structure this organization uses."
        actions={
          <Button size="sm" onClick={() => setCreateParent(null)}>
            New unit
          </Button>
        }
      />

      {error && (
        <div className="mb-4">
          <ErrorBanner message={error} error={errorDetail} />
        </div>
      )}

      {tree.length === 0 ? (
        <EmptyState
          title="No units yet"
          description="Create your first unit -- a branch, department, warehouse, or anything else."
          action={
            <Button size="sm" onClick={() => setCreateParent(null)}>
              New unit
            </Button>
          }
        />
      ) : (
        <Card>{tree.map((node) => renderNode(node, 0))}</Card>
      )}

      <CreateUnitModal
        key={createParent === undefined ? "closed" : (createParent?.id ?? "root")}
        open={createParent !== undefined}
        orgId={orgId}
        parent={createParent ?? null}
        onClose={() => setCreateParent(undefined)}
        onCreated={(unit) => {
          setUnits((prev) => [...(prev ?? []), unit]);
          setCreateParent(undefined);
        }}
      />

      <EditUnitModal
        key={editUnit?.id ?? "none"}
        unit={editUnit}
        units={units}
        onClose={() => setEditUnit(null)}
        onSaved={(unit) => {
          setUnits((prev) => (prev ? prev.map((u) => (u.id === unit.id ? unit : u)) : prev));
          setEditUnit(null);
        }}
      />

      <UnitMembersModal
        key={membersUnit?.id ?? "none"}
        unit={membersUnit}
        orgMembers={orgMembers ?? []}
        onClose={() => setMembersUnit(null)}
      />
    </div>
  );
}

function CreateUnitModal({
  open,
  orgId,
  parent,
  onClose,
  onCreated,
}: {
  open: boolean;
  orgId: string;
  parent: OrganizationalUnit | null;
  onClose: () => void;
  onCreated: (unit: OrganizationalUnit) => void;
}) {
  const [name, setName] = useState("");
  const [unitType, setUnitType] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [errorDetail, setErrorDetail] = useState<unknown>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const unit = await api.post<OrganizationalUnit>(`/organizations/${orgId}/units/`, {
        name,
        unit_type: unitType,
        ...(parent ? { parent: parent.id } : {}),
      });
      setName("");
      setUnitType("");
      onCreated(unit);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to create unit.");
      setErrorDetail(err);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Modal open={open} onClose={onClose} title={parent ? `New sub-unit of ${parent.name}` : "New unit"}>
      <form onSubmit={handleSubmit} className="space-y-4">
        {error && <ErrorBanner message={error} error={errorDetail} />}
        <div>
          <Label htmlFor="unit-name">Name</Label>
          <Input
            id="unit-name"
            autoFocus
            required
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Downtown Branch"
          />
        </div>
        <div>
          <Label htmlFor="unit-type">Type</Label>
          <Input
            id="unit-type"
            required
            value={unitType}
            onChange={(e) => setUnitType(e.target.value)}
            placeholder="branch, department, warehouse, team..."
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

function EditUnitModal({
  unit,
  units,
  onClose,
  onSaved,
}: {
  unit: OrganizationalUnit | null;
  units: OrganizationalUnit[];
  onClose: () => void;
  onSaved: (unit: OrganizationalUnit) => void;
}) {
  const [name, setName] = useState(unit?.name ?? "");
  const [unitType, setUnitType] = useState(unit?.unit_type ?? "");
  const [parentId, setParentId] = useState(unit?.parent ?? "");
  const [error, setError] = useState<string | null>(null);
  const [errorDetail, setErrorDetail] = useState<unknown>(null);
  const [submitting, setSubmitting] = useState(false);

  const blocked = unit ? descendantIds(units, unit.id) : new Set<string>();
  const parentOptions = unit ? units.filter((u) => u.id !== unit.id && !blocked.has(u.id)) : [];

  async function handleSubmit(e: FormEvent) {
    if (!unit) return;
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const updated = await api.patch<OrganizationalUnit>(`/units/${unit.id}/`, {
        name,
        unit_type: unitType,
        parent: parentId || null,
      });
      onSaved(updated);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to update unit.");
      setErrorDetail(err);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Modal open={unit !== null} onClose={onClose} title={`Edit ${unit?.name ?? ""}`}>
      <form onSubmit={handleSubmit} className="space-y-4">
        {error && <ErrorBanner message={error} error={errorDetail} />}
        <div>
          <Label htmlFor="edit-unit-name">Name</Label>
          <Input id="edit-unit-name" required value={name} onChange={(e) => setName(e.target.value)} />
        </div>
        <div>
          <Label htmlFor="edit-unit-type">Type</Label>
          <Input id="edit-unit-type" required value={unitType} onChange={(e) => setUnitType(e.target.value)} />
        </div>
        <div>
          <Label htmlFor="edit-unit-parent">Parent</Label>
          <Select id="edit-unit-parent" value={parentId} onChange={(e) => setParentId(e.target.value)}>
            <option value="">None (root)</option>
            {parentOptions.map((u) => (
              <option key={u.id} value={u.id}>
                {u.name}
              </option>
            ))}
          </Select>
        </div>
        <div className="flex justify-end gap-2">
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" disabled={submitting}>
            {submitting ? "..." : "Save"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

function UnitMembersModal({
  unit,
  orgMembers,
  onClose,
}: {
  unit: OrganizationalUnit | null;
  orgMembers: Membership[];
  onClose: () => void;
}) {
  const [members, setMembers] = useState<UnitMembership[] | null>(null);
  const [addUserId, setAddUserId] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [errorDetail, setErrorDetail] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!unit) return;
    (async () => {
      try {
        setMembers(await api.get<UnitMembership[]>(`/units/${unit.id}/members/`));
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "Failed to load members.");
        setErrorDetail(err);
        setMembers([]);
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [unit?.id]);

  const candidates = orgMembers.filter((m) => !members?.some((um) => um.user.id === m.user.id));

  async function addMember(e: FormEvent) {
    e.preventDefault();
    if (!unit || !addUserId) return;
    setBusy(true);
    setError(null);
    try {
      const membership = await api.post<UnitMembership>(`/units/${unit.id}/members/`, {
        user_id: addUserId,
      });
      setMembers((prev) => [...(prev ?? []), membership]);
      setAddUserId("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to add member.");
      setErrorDetail(err);
    } finally {
      setBusy(false);
    }
  }

  async function removeMember(userId: string) {
    if (!unit) return;
    try {
      await api.del(`/units/${unit.id}/members/${userId}/`);
      setMembers((prev) => (prev ? prev.filter((m) => m.user.id !== userId) : prev));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to remove member.");
      setErrorDetail(err);
    }
  }

  return (
    <Modal open={unit !== null} onClose={onClose} title={`Members of ${unit?.name ?? ""}`}>
      <div className="space-y-4">
        {error && <ErrorBanner message={error} error={errorDetail} />}
        {members === null ? (
          <p className="text-sm text-slate-500">Loading...</p>
        ) : members.length === 0 ? (
          <p className="text-sm text-slate-500">No members yet.</p>
        ) : (
          <ul className="space-y-1.5">
            {members.map((m) => (
              <li key={m.id} className="flex items-center justify-between gap-2 text-sm text-slate-600">
                <span className="truncate">{m.user.email}</span>
                <button
                  onClick={() => removeMember(m.user.id)}
                  className="text-xs text-slate-500 hover:text-red-600"
                >
                  Remove
                </button>
              </li>
            ))}
          </ul>
        )}

        {candidates.length > 0 && (
          <form onSubmit={addMember} className="flex items-end gap-2 border-t border-slate-100 pt-4">
            <div className="flex-1">
              <Label htmlFor="unit-add-member">Add member</Label>
              <Select
                id="unit-add-member"
                value={addUserId}
                onChange={(e) => setAddUserId(e.target.value)}
              >
                <option value="">Select a member...</option>
                {candidates.map((m) => (
                  <option key={m.user.id} value={m.user.id}>
                    {m.user.email}
                  </option>
                ))}
              </Select>
            </div>
            <Button type="submit" size="sm" disabled={busy || !addUserId}>
              {busy ? "..." : "Add"}
            </Button>
          </form>
        )}
      </div>
    </Modal>
  );
}
