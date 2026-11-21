"use client";

import { useId, useState, type FormEvent } from "react";
import { UserPen } from "lucide-react";
import { api, ApiError, ensureCsrfCookie, type User } from "@/lib/api";
import { Button, ErrorBanner, Input, Label, Modal } from "@/components/ui";

/** The details a person (or their administrator) may change. The email is not one: it is how they sign in. */
export type UserDetails = {
  first_name: string;
  last_name: string;
  phone: string;
  job_title: string;
  address: string;
  emergency_contact: string;
};

const FIELDS: { key: keyof UserDetails; label: string; placeholder?: string; type?: string; wide?: boolean }[] = [
  { key: "first_name", label: "First name" },
  { key: "last_name", label: "Last name" },
  { key: "phone", label: "Phone", placeholder: "+971 50 123 4567", type: "tel" },
  { key: "job_title", label: "Job title", placeholder: "Cashier, store keeper, manager..." },
  { key: "address", label: "Address", wide: true },
  { key: "emergency_contact", label: "Emergency contact", placeholder: "Name and phone number", wide: true },
];

export function detailsOf(user: Partial<User>): UserDetails {
  return {
    first_name: user.first_name ?? "",
    last_name: user.last_name ?? "",
    phone: user.phone ?? "",
    job_title: user.job_title ?? "",
    address: user.address ?? "",
    emergency_contact: user.emergency_contact ?? "",
  };
}

/** The six fields with Save; `save` sends them and returns the updated person. */
export function UserDetailsForm({
  initial,
  save,
  onSaved,
  onCancel,
}: {
  initial: UserDetails;
  save: (details: UserDetails) => Promise<User>;
  onSaved: (user: User) => void;
  onCancel?: () => void;
}) {
  const [values, setValues] = useState<UserDetails>(initial);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const id = useId();

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    setSaved(false);
    try {
      await ensureCsrfCookie();
      onSaved(await save(values));
      setSaved(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "The details were not saved.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={(e) => void submit(e)} className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-2">
        {FIELDS.map((f) => (
          <div key={f.key} className={f.wide ? "sm:col-span-2" : ""}>
            <Label htmlFor={`${id}-${f.key}`}>{f.label}</Label>
            <Input
              id={`${id}-${f.key}`}
              type={f.type ?? "text"}
              placeholder={f.placeholder}
              value={values[f.key]}
              onChange={(e) => {
                setValues({ ...values, [f.key]: e.target.value });
                setSaved(false);
              }}
            />
          </div>
        ))}
      </div>
      {error && <ErrorBanner message={error} />}
      <div className="flex items-center justify-end gap-3">
        <span aria-live="polite" className="text-sm text-green-700">
          {saved ? "Saved." : ""}
        </span>
        {onCancel && (
          <Button type="button" variant="secondary" onClick={onCancel} disabled={busy}>
            Close
          </Button>
        )}
        <Button type="submit" disabled={busy}>
          {busy ? "Saving..." : "Save"}
        </Button>
      </div>
    </form>
  );
}

/** "Details" for one member of an organization (an administrator's view of the members list). */
export function EditMemberDetails({
  orgId,
  membershipId,
  user,
  onSaved,
}: {
  orgId: string;
  membershipId: string;
  user: User;
  onSaved: (user: User) => void;
}) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <Button size="sm" variant="ghost" onClick={() => setOpen(true)} aria-label={`Edit the details of ${user.email}`}>
        <UserPen aria-hidden="true" className="h-3.5 w-3.5" />
        Details
      </Button>
      {open && (
        <Modal open onClose={() => setOpen(false)} title={`Details of ${user.email}`}>
          <UserDetailsForm
            initial={detailsOf(user)}
            save={(d) => api.patch<User>(`/organizations/${orgId}/members/${membershipId}/profile/`, d)}
            onSaved={onSaved}
            onCancel={() => setOpen(false)}
          />
        </Modal>
      )}
    </>
  );
}
