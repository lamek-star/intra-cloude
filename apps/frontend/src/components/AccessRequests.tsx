"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";
import { ApiError } from "@/lib/api";
import { decideAccessRequest, listAccessRequests, type AccessRequest, type Decision } from "@/lib/access";
import {
  Badge,
  Button,
  ErrorBanner,
  Label,
  Modal,
  SecretReveal,
  Select,
  Table,
  Td,
  Textarea,
  Th,
  THead,
  TRow,
} from "@/components/ui";

type RoleOption = { slug: string; name: string; summary: string; administrative: boolean };

const TONE = { pending: "warning", approved: "success", rejected: "default" } as const;

/** Organization > Members > Requests (ADR-0026): people who asked for access from an app. Only shown to someone who
 * may give roles (the server answers 403 to anyone else, and this then renders nothing). */
export function AccessRequests({
  orgId,
  roles,
  onApproved,
}: {
  orgId: string;
  roles: RoleOption[];
  onApproved?: () => void;
}) {
  const [items, setItems] = useState<AccessRequest[] | null>(null);
  const [emailEnabled, setEmailEnabled] = useState(false);
  const [showDecided, setShowDecided] = useState(false);
  const [deciding, setDeciding] = useState<{ request: AccessRequest; mode: "approve" | "reject" } | null>(null);
  const [handOver, setHandOver] = useState<{ who: string; decision: Decision } | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    listAccessRequests(orgId)
      .then((r) => {
        setItems(r.results);
        setEmailEnabled(r.email_enabled);
      })
      .catch(() => setItems(null));
  }, [orgId]);

  useEffect(load, [load]);

  if (items === null) return null;
  const pending = items.filter((r) => r.status === "pending");
  const shown = showDecided ? items : pending;

  async function newLink(request: AccessRequest) {
    setError(null);
    try {
      setHandOver({ who: request.email, decision: await decideAccessRequest(orgId, request.id, "link") });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not make a new link.");
    }
  }

  return (
    <div>
      <div className="mb-3 flex items-center justify-between">
        <h2 className="flex items-center gap-2 text-sm font-semibold text-slate-600">
          Requests {pending.length > 0 && <Badge tone="warning">{pending.length} waiting</Badge>}
        </h2>
        <label className="flex items-center gap-2 text-xs text-text-muted">
          <input type="checkbox" checked={showDecided} onChange={(e) => setShowDecided(e.target.checked)} />
          Show decided
        </label>
      </div>
      {error && <ErrorBanner message={error} />}
      {shown.length === 0 ? (
        <p className="text-sm text-slate-500">
          No requests waiting. New staff ask from an app&apos;s sign-in page (Request access).
        </p>
      ) : (
        <Table>
          <THead>
            <Th>Person</Th>
            <Th>App</Th>
            <Th>Asked for</Th>
            <Th>Status</Th>
            <Th>
              <span className="sr-only">Actions</span>
            </Th>
          </THead>
          <tbody>
            {shown.map((r) => (
              <TRow key={r.id}>
                <Td>
                  <span className="block font-medium text-text-primary">{r.name || r.email}</span>
                  <span className="block text-xs text-text-muted">
                    {r.email}
                    {r.phone && ` · ${r.phone}`}
                  </span>
                  {r.message && <span className="mt-1 block text-xs text-slate-500">“{r.message}”</span>}
                </Td>
                <Td className="text-text-muted">{r.app?.name ?? "—"}</Td>
                <Td className="text-text-muted">{r.requested_role_name || "Administrator's choice"}</Td>
                <Td>
                  <Badge tone={TONE[r.status]}>{r.status}</Badge>
                  {r.status === "approved" && r.new_account && (
                    <span className="mt-1 block text-xs text-text-muted">
                      {r.activated ? "activated" : "waiting for the link"}
                    </span>
                  )}
                </Td>
                <Td>
                  {r.status === "pending" ? (
                    <div className="flex flex-wrap gap-1">
                      <Button size="sm" onClick={() => setDeciding({ request: r, mode: "approve" })}>
                        Approve
                      </Button>
                      <Button
                        size="sm"
                        variant="secondary"
                        onClick={() => setDeciding({ request: r, mode: "reject" })}
                      >
                        Reject
                      </Button>
                    </div>
                  ) : r.status === "approved" && r.new_account && !r.activated ? (
                    <Button size="sm" variant="secondary" onClick={() => void newLink(r)}>
                      New link
                    </Button>
                  ) : null}
                </Td>
              </TRow>
            ))}
          </tbody>
        </Table>
      )}

      {deciding && (
        <DecideModal
          orgId={orgId}
          roles={roles}
          request={deciding.request}
          mode={deciding.mode}
          onClose={() => setDeciding(null)}
          onDone={(decision) => {
            const { request, mode } = deciding;
            setDeciding(null);
            load();
            if (mode === "approve") {
              onApproved?.();
              if (decision.link) setHandOver({ who: request.email, decision });
            }
          }}
        />
      )}

      <Modal open={handOver !== null} onClose={() => setHandOver(null)} title="Hand over the activation link">
        {handOver && (
          <div className="space-y-3">
            <p className="text-sm text-text-muted">
              {handOver.decision.emailed
                ? `The link was e-mailed to ${handOver.who}. You can also give it in person:`
                : `Give this link to ${handOver.who} in person, or by a message only they read. It works once, for 72 hours.`}
            </p>
            {handOver.decision.link && <SecretReveal label="Shown only now" secret={handOver.decision.link} />}
            {!emailEnabled && (
              <p className="text-xs text-text-muted">E-mail is not set up on this installation, so nothing was sent.</p>
            )}
            <div className="flex justify-end">
              <Button onClick={() => setHandOver(null)}>Done</Button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}

function DecideModal({
  orgId,
  roles,
  request,
  mode,
  onClose,
  onDone,
}: {
  orgId: string;
  roles: RoleOption[];
  request: AccessRequest;
  mode: "approve" | "reject";
  onClose: () => void;
  onDone: (d: Decision) => void;
}) {
  const [role, setRole] = useState(request.requested_role);
  const [note, setNote] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const body = mode === "approve" ? { role_slug: role, note } : { note };
      onDone(await decideAccessRequest(orgId, request.id, mode, body));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong.");
      setBusy(false);
    }
  }

  return (
    <Modal open onClose={onClose} title={mode === "approve" ? `Approve ${request.email}` : `Reject ${request.email}`}>
      <form onSubmit={submit} className="space-y-4">
        {error && <ErrorBanner message={error} />}
        {mode === "approve" && (
          <div>
            <Label htmlFor="grant-role">Role to give</Label>
            <Select id="grant-role" required value={role} onChange={(e) => setRole(e.target.value)}>
              <option value="">Choose…</option>
              {roles.map((r) => (
                <option key={r.slug} value={r.slug}>
                  {r.name}
                  {r.slug === request.requested_role ? " (asked for)" : ""}
                </option>
              ))}
            </Select>
            <p className="mt-1 text-xs text-text-muted">You decide: what they asked for is only a suggestion.</p>
          </div>
        )}
        <div>
          <Label htmlFor="decision-note">{mode === "approve" ? "Note (optional)" : "Reason (optional)"}</Label>
          <Textarea id="decision-note" maxLength={500} value={note} onChange={(e) => setNote(e.target.value)} />
        </div>
        <div className="flex justify-end gap-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" disabled={busy || (mode === "approve" && !role)}>
            {busy ? "..." : mode === "approve" ? "Approve" : "Reject"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
