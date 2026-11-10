"use client";

import { useId, useState, type FormEvent } from "react";
import { Clapperboard, Gift } from "lucide-react";
import { portalApi, rulesInWords, type PortalHome } from "@/lib/portal";
import { portalMessage, portalStyle as ui } from "./Portal";
import { AdCarousel } from "./AdCarousel";

/** Sign in, or create an account with the shop (the shop approves it at the counter). */
export function AuthScreen({ shop, onSignedIn }: { shop: PortalHome["shop"]; onSignedIn: () => void }) {
  const [mode, setMode] = useState<"in" | "up">("up");
  const [form, setForm] = useState({ name: "", phone: "", password: "", birthday: "", referral_code: "" });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const ids = { name: useId(), phone: useId(), password: useId(), birthday: useId(), code: useId() };
  const perks = rulesInWords(shop.rules);
  const set = (key: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) => setForm({ ...form, [key]: e.target.value });

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      if (mode === "in") await portalApi.signIn(shop.id, form.phone, form.password);
      else
        await portalApi.signUp(shop.id, {
          name: form.name.trim(),
          phone: form.phone,
          password: form.password,
          birthday: form.birthday || undefined,
          referral_code: form.referral_code.trim() || undefined,
        });
      onSignedIn();
    } catch (err) {
      setError(portalMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex min-h-screen flex-col bg-[#0a0d16] bg-[radial-gradient(700px_420px_at_80%_-10%,rgba(245,165,36,.18),transparent_60%),radial-gradient(600px_420px_at_0%_100%,rgba(45,212,191,.10),transparent_60%)] text-slate-100">
      <div className="mx-auto w-full max-w-md flex-1 px-5 pt-12 pb-10">
        <span className="grid h-14 w-14 place-items-center rounded-2xl bg-[radial-gradient(circle_at_30%_25%,#ffd27a,#f5a524_60%,#c97b05)] text-amber-950 shadow-[0_12px_30px_-10px_rgba(245,165,36,.7)]">
          <Clapperboard className="h-7 w-7" strokeWidth={2.2} />
        </span>
        <h1 className="mt-5 text-3xl font-semibold tracking-wide uppercase" style={{ fontFamily: "var(--font-display), sans-serif" }}>
          {shop.name}
        </h1>
        <p className="mt-1 text-sm text-slate-400">Films and series, copied to your USB at the counter.</p>

        <div className="mt-5">
          <AdCarousel shopId={shop.id} shopName={shop.name} />
        </div>

        {perks.length > 0 && (
          <ul className="mt-5 flex flex-col gap-2 rounded-2xl border border-[#252e47] bg-[#141a2b]/80 p-4">
            {perks.map((p) => (
              <li key={p} className="flex items-center gap-2.5 text-sm">
                <Gift className="h-4 w-4 shrink-0 text-amber-300" /> {p}
              </li>
            ))}
          </ul>
        )}

        <div className="mt-6 grid grid-cols-2 rounded-xl bg-[#141a2b] p-1" role="tablist">
          {(
            [
              ["up", "Create account"],
              ["in", "Sign in"],
            ] as const
          ).map(([value, label]) => (
            <button
              key={value}
              role="tab"
              aria-selected={mode === value}
              onClick={() => {
                setMode(value);
                setError(null);
              }}
              className={`h-10 rounded-lg text-sm font-semibold ${mode === value ? "bg-amber-400 text-amber-950" : "text-slate-300"}`}
            >
              {label}
            </button>
          ))}
        </div>

        <form className="mt-5 flex flex-col gap-4" onSubmit={(e) => void submit(e)}>
          {mode === "up" && (
            <div>
              <label htmlFor={ids.name} className={ui.label}>
                Your name
              </label>
              <input id={ids.name} className={ui.input} required maxLength={80} autoComplete="name" value={form.name} onChange={set("name")} />
            </div>
          )}
          <div>
            <label htmlFor={ids.phone} className={ui.label}>
              Phone number
            </label>
            <input id={ids.phone} className={ui.input} required type="tel" inputMode="tel" autoComplete="tel" value={form.phone} onChange={set("phone")} />
          </div>
          <div>
            <label htmlFor={ids.password} className={ui.label}>
              Password{mode === "up" ? " (at least 8 characters)" : ""}
            </label>
            <input
              id={ids.password}
              className={ui.input}
              required
              type="password"
              minLength={mode === "up" ? 8 : undefined}
              autoComplete={mode === "up" ? "new-password" : "current-password"}
              value={form.password}
              onChange={set("password")}
            />
          </div>
          {mode === "up" && (
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label htmlFor={ids.birthday} className={ui.label}>
                  Birthday <span className="font-normal text-slate-500">(optional)</span>
                </label>
                <input id={ids.birthday} className={ui.input} type="date" value={form.birthday} onChange={set("birthday")} />
              </div>
              <div>
                <label htmlFor={ids.code} className={ui.label}>
                  Friend&apos;s code <span className="font-normal text-slate-500">(optional)</span>
                </label>
                <input id={ids.code} className={`${ui.input} uppercase`} maxLength={8} autoCapitalize="characters" value={form.referral_code} onChange={set("referral_code")} />
              </div>
            </div>
          )}
          {error && (
            <p className="rounded-xl bg-red-400/10 px-4 py-3 text-sm text-red-200" role="alert">
              {error}
            </p>
          )}
          <button className={ui.primary} disabled={busy}>
            {busy ? "One moment..." : mode === "up" ? "Create my account" : "Sign in"}
          </button>
        </form>
        <p className="mt-6 text-center text-xs text-slate-500">This portal works only on the shop&apos;s Wi-Fi. Your account is with this shop only.</p>
      </div>
    </div>
  );
}
