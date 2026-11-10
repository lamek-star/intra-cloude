"use client";

import { useEffect, useId, useState } from "react";
import { Ban, Check, Copy, Gift, KeyRound, ShieldCheck, Undo2, Users, Wallet, X } from "lucide-react";
import { movies, type ApprovedWallet, type PortalSettings, type ShopCustomer } from "@/lib/movies";
import { dark, DarkDialog, message } from "./Dialogs";

const STATUS_LABEL: Record<ShopCustomer["status"], string> = {
  pending: "Waiting",
  approved: "Approved",
  rejected: "Rejected",
  blocked: "Blocked",
};
const STATUS_TONE: Record<ShopCustomer["status"], string> = {
  pending: "border-amber-400/30 bg-amber-400/10 text-amber-200",
  approved: "border-emerald-400/30 bg-emerald-400/10 text-emerald-200",
  rejected: "border-[#323c5a] text-slate-400",
  blocked: "border-red-400/30 bg-red-400/10 text-red-200",
};

/** The customer portal, the owner's side: open it, set the rewards, approve customers (adds them to IF Pay). */
export function CustomersDialog({ shopId, onClose, onChanged }: { shopId: string; onClose: () => void; onChanged: () => void }) {
  const [settings, setSettings] = useState<PortalSettings | null>(null);
  const [customers, setCustomers] = useState<ShopCustomer[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [approved, setApproved] = useState<{ customer: ShopCustomer; wallet: ApprovedWallet } | null>(null);

  const [version, setVersion] = useState(0);

  useEffect(() => {
    let live = true;
    Promise.all([movies.portal(shopId), movies.customers(shopId)])
      .then(([s, c]) => {
        if (!live) return;
        setSettings(s);
        setCustomers(c.results);
      })
      .catch((err) => live && setError(message(err)));
    return () => {
      live = false;
    };
  }, [shopId, version]);

  async function act(id: string, run: () => Promise<unknown>) {
    setBusy(id);
    setError(null);
    try {
      await run();
      setVersion((v) => v + 1);
      onChanged();
    } catch (err) {
      setError(message(err));
    } finally {
      setBusy(null);
    }
  }

  const waiting = customers?.filter((c) => c.status === "pending") ?? [];
  const others = customers?.filter((c) => c.status !== "pending") ?? [];

  return (
    <DarkDialog title="Customers" onClose={onClose} wide>
      {error && <p className="mb-3 rounded-lg bg-red-400/10 px-3 py-2 text-sm text-red-200">{error}</p>}
      {approved && <FirstPassword data={approved} onDone={() => setApproved(null)} />}
      {settings && (
        <PortalSettingsCard
          settings={settings}
          onSave={(body) =>
            act("settings", async () => {
              setSettings(await movies.setPortal(shopId, body));
            })
          }
          busy={busy === "settings"}
        />
      )}

      <section className="mt-5">
        <h3 className="flex items-center gap-2 text-sm font-bold">
          <Users className="h-4 w-4 text-amber-300" /> Waiting for you {waiting.length > 0 && <span className="rounded-full bg-amber-400 px-2 text-xs text-amber-950">{waiting.length}</span>}
        </h3>
        {customers && waiting.length === 0 && <p className="mt-2 text-sm text-slate-500">Nobody is waiting. New sign-ups from the portal appear here.</p>}
        <ul className="mt-2 flex flex-col gap-2">
          {waiting.map((c) => (
            <li key={c.id} className="flex flex-wrap items-center gap-3 rounded-xl border border-[#252e47] bg-[#0f1422] p-3">
              <CustomerLine customer={c} />
              <div className="ml-auto flex gap-2">
                <button
                  className={dark.amber}
                  disabled={busy !== null}
                  onClick={() =>
                    act(c.id, async () => {
                      setApproved(await movies.approve(c.id));
                    })
                  }
                >
                  <Wallet className="h-4 w-4" /> {busy === c.id ? "Adding..." : "Add to IF Pay"}
                </button>
                <button className={dark.btn} disabled={busy !== null} onClick={() => act(c.id, () => movies.customerAction(c.id, "reject"))}>
                  <X className="h-4 w-4" /> Reject
                </button>
              </div>
            </li>
          ))}
        </ul>
      </section>

      <section className="mt-5">
        <h3 className="text-sm font-bold">All customers</h3>
        {customers && others.length === 0 && <p className="mt-2 text-sm text-slate-500">No approved customers yet.</p>}
        <ul className="mt-2 flex max-h-[38vh] flex-col overflow-y-auto">
          {others.map((c) => (
            <li key={c.id} className="flex flex-wrap items-center gap-3 border-b border-[#252e47] py-2.5">
              <CustomerLine customer={c} />
              <span className="ml-auto text-sm font-bold text-amber-200" title="Movie Shop points">
                {c.points} pts
              </span>
              {c.status === "approved" && (
                <button className="text-xs text-slate-400 hover:text-red-300" disabled={busy !== null} onClick={() => act(c.id, () => movies.customerAction(c.id, "block"))}>
                  <Ban className="mr-1 inline h-3.5 w-3.5" /> Block
                </button>
              )}
              {c.status === "blocked" && (
                <button className="text-xs text-slate-400 hover:text-white" disabled={busy !== null} onClick={() => act(c.id, () => movies.customerAction(c.id, "unblock"))}>
                  <Undo2 className="mr-1 inline h-3.5 w-3.5" /> Unblock
                </button>
              )}
            </li>
          ))}
        </ul>
      </section>
      <div className="mt-4 flex justify-end">
        <button className={dark.btn} onClick={onClose}>
          Close
        </button>
      </div>
    </DarkDialog>
  );
}

function CustomerLine({ customer: c }: { customer: ShopCustomer }) {
  return (
    <span className="min-w-0">
      <span className="flex items-center gap-2 text-sm font-semibold">
        {c.name}
        <span className={`rounded-full border px-2 py-px text-[10.5px] font-semibold ${STATUS_TONE[c.status]}`}>{STATUS_LABEL[c.status]}</span>
      </span>
      <span className="block text-[11px] text-slate-500">
        {c.phone}
        {c.pay_username && ` · IF Pay ${c.pay_username}`}
        {c.referred_by && ` · invited by ${c.referred_by}`}
        {` · signed up ${new Date(c.created_at).toLocaleDateString()}`}
      </span>
    </span>
  );
}

function PortalSettingsCard({ settings, onSave, busy }: { settings: PortalSettings; onSave: (body: Partial<PortalSettings>) => void; busy: boolean }) {
  const [rules, setRules] = useState({
    welcome_points: settings.welcome_points,
    referral_points: settings.referral_points,
    birthday_points: settings.birthday_points,
    every_nth_free: settings.every_nth_free,
  });
  const ids = { welcome: useId(), referral: useId(), birthday: useId(), nth: useId() };
  const address = typeof window === "undefined" ? settings.path : `${window.location.origin}${settings.path}`;
  const local = typeof window !== "undefined" && /^(localhost|127\.0\.0\.1)$/.test(window.location.hostname);
  const [copied, setCopied] = useState(false);
  const field = (key: keyof typeof rules, id: string, label: string, hint: string) => (
    <div>
      <label htmlFor={id} className={dark.label}>
        {label}
      </label>
      <input
        id={id}
        type="number"
        min={0}
        className={dark.input}
        value={rules[key]}
        onChange={(e) => setRules({ ...rules, [key]: Math.max(0, Math.floor(Number(e.target.value) || 0)) })}
      />
      <p className="mt-1 text-[11px] text-slate-500">{hint}</p>
    </div>
  );
  return (
    <section className="rounded-2xl border border-[#252e47] bg-[#141a2b] p-4">
      <div className="flex flex-wrap items-center gap-3">
        <span className={`grid h-9 w-9 place-items-center rounded-xl ${settings.portal_open ? "bg-emerald-400/15 text-emerald-300" : "bg-[#1b2236] text-slate-400"}`}>
          <ShieldCheck className="h-4 w-4" />
        </span>
        <div className="min-w-0 flex-1">
          <p className="text-sm font-bold">Customer portal {settings.portal_open ? "is open" : "is closed"}</p>
          <p className="text-[11px] text-slate-500">On the shop network only. Customers sign up, browse and order; you approve them here.</p>
        </div>
        <button className={settings.portal_open ? dark.btn : dark.amber} disabled={busy} onClick={() => onSave({ portal_open: !settings.portal_open })}>
          {settings.portal_open ? "Close the portal" : "Open the portal"}
        </button>
      </div>
      {settings.portal_open && (
        <div className="mt-3 rounded-lg bg-[#0f1422] p-3">
          <p className="text-[11px] font-semibold text-slate-400">Customers open this address on the shop Wi-Fi</p>
          <div className="mt-1 flex items-center gap-2">
            <code className="min-w-0 flex-1 truncate font-mono text-sm text-amber-200">{address}</code>
            <button
              className="rounded-md p-1.5 text-slate-400 hover:bg-white/5 hover:text-white"
              aria-label="Copy the portal address"
              onClick={() => {
                void navigator.clipboard?.writeText(address).then(() => setCopied(true));
              }}
            >
              {copied ? <Check className="h-4 w-4 text-emerald-300" /> : <Copy className="h-4 w-4" />}
            </button>
          </div>
          {local && <p className="mt-1 text-[11px] text-amber-200/80">This is this PC&apos;s own address. On a phone, use the shop PC&apos;s network name or IP address instead of localhost.</p>}
        </div>
      )}
      <p className="mt-4 flex items-center gap-2 text-xs font-bold text-slate-300">
        <Gift className="h-4 w-4 text-amber-300" /> Rewards (Movie Shop points: 1 point = 1 credit off a purchase; 0 = off)
      </p>
      <div className="mt-2 grid gap-3 sm:grid-cols-4">
        {field("welcome_points", ids.welcome, "Welcome points", "When you approve a customer")}
        {field("every_nth_free", ids.nth, "Every Nth title free", "e.g. 10: every 10th title")}
        {field("referral_points", ids.referral, "Invite points", "To the customer who invited")}
        {field("birthday_points", ids.birthday, "Birthday points", "Once a year")}
      </div>
      <div className="mt-3 flex justify-end">
        <button className={dark.btn} disabled={busy} onClick={() => onSave(rules)}>
          Save rewards
        </button>
      </div>
    </section>
  );
}

/** Shown once after "Add to IF Pay": the wallet's username and one-time first password, to hand to the customer. */
function FirstPassword({ data, onDone }: { data: { customer: ShopCustomer; wallet: ApprovedWallet }; onDone: () => void }) {
  const { customer, wallet } = data;
  return (
    <div className="mb-4 rounded-2xl border border-teal-400/40 bg-teal-400/10 p-4" role="status">
      <p className="flex items-center gap-2 text-sm font-bold text-teal-100">
        <KeyRound className="h-4 w-4" /> {customer.name} is approved and has an IF Pay wallet
      </p>
      {wallet.first_password ? (
        <>
          <p className="mt-1 text-xs text-teal-100/80">Give these to the customer now. The password is shown only once; they choose their own at the first sign-in.</p>
          <dl className="mt-3 grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-sm">
            <dt className="text-slate-400">Wallet username</dt>
            <dd className="font-mono font-bold">{wallet.username}</dd>
            <dt className="text-slate-400">First password</dt>
            <dd className="font-mono text-lg font-bold tracking-wider text-amber-200">{wallet.first_password}</dd>
          </dl>
        </>
      ) : (
        <p className="mt-1 text-xs text-teal-100/80">Their wallet already existed ({wallet.username}); they keep their own password.</p>
      )}
      <button className={`${dark.btn} mt-3`} onClick={onDone}>
        Done, I gave it to them
      </button>
    </div>
  );
}
