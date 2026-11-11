"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Check, Coins, Copy, ExternalLink, Gift, Wallet } from "lucide-react";
import { POINT_REASONS, portalApi, rulesInWords, type PortalRules } from "@/lib/portal";

/** The customer's points (with their history), their IF Pay wallet, and their code to invite friends. */
export function MeScreen({ shopId, rules }: { shopId: string; rules: PortalRules }) {
  const me = useQuery({ queryKey: ["portal", shopId, "me"], queryFn: () => portalApi.me(shopId) });
  const [copied, setCopied] = useState(false);
  if (!me.data) return <p className="mt-8 text-center text-sm text-slate-500">Loading...</p>;
  const m = me.data;
  const perks = rulesInWords(rules);

  return (
    <div className="flex flex-col gap-4">
      <section className="rounded-3xl bg-[linear-gradient(135deg,#f5a524,#c97b05)] p-5 text-amber-950 shadow-[0_18px_40px_-20px_rgba(245,165,36,.9)]">
        <p className="text-sm font-semibold opacity-80">Movie Shop points</p>
        <p className="mt-1 flex items-center gap-2 text-4xl font-extrabold">
          <Coins className="h-8 w-8" /> {m.points}
        </p>
        <p className="mt-1 text-xs font-medium opacity-80">1 point takes 1 credit off a purchase here.</p>
      </section>

      <section className="rounded-2xl border border-[#252e47] bg-[#141a2b] p-4">
        <p className="flex items-center gap-2 text-sm font-bold">
          <Wallet className="h-4 w-4 text-teal-300" /> IF Pay wallet
        </p>
        {m.wallet ? (
          <>
            <p className="mt-2 text-sm text-slate-300">
              Username <span className="font-mono font-bold">{m.wallet.username}</span>
            </p>
            <p className="mt-1 text-2xl font-extrabold">
              {m.wallet.balance == null ? "—" : m.wallet.balance.toFixed(2)} <span className="text-xs font-semibold text-slate-400">IF Credits</span>
            </p>
            {m.wallet.must_change_password && (
              <p className="mt-2 rounded-lg bg-amber-400/10 px-3 py-2 text-xs text-amber-100">Open your wallet and choose your own password (the shop gave you a one-time one).</p>
            )}
            {m.wallet.path && (
              <a href={m.wallet.path} className="mt-3 inline-flex items-center gap-1.5 text-sm font-semibold text-teal-300">
                Open my wallet <ExternalLink className="h-4 w-4" />
              </a>
            )}
          </>
        ) : (
          <p className="mt-2 text-sm text-slate-400">{m.status === "approved" ? "The wallet is not answering right now." : "The shop adds you to IF Pay when it approves your account."}</p>
        )}
      </section>

      {m.referral_code && (
        <section className="rounded-2xl border border-[#252e47] bg-[#141a2b] p-4">
          <p className="flex items-center gap-2 text-sm font-bold">
            <Gift className="h-4 w-4 text-amber-300" /> Invite a friend
          </p>
          <p className="mt-1 text-xs text-slate-400">{rules.referral_points ? `They enter your code when they sign up; you get ${rules.referral_points} points when the shop approves them.` : "Friends can enter your code when they sign up."}</p>
          <div className="mt-3 flex items-center gap-3">
            <span className="flex-1 rounded-xl bg-[#0f1422] px-4 py-3 text-center font-mono text-2xl font-bold tracking-[.3em]">{m.referral_code}</span>
            <button
              className="rounded-xl border border-[#323c5a] p-3 text-slate-300 hover:text-white"
              aria-label="Copy my code"
              onClick={() => void navigator.clipboard?.writeText(m.referral_code ?? "").then(() => setCopied(true))}
            >
              {copied ? <Check className="h-5 w-5 text-emerald-300" /> : <Copy className="h-5 w-5" />}
            </button>
          </div>
        </section>
      )}

      {perks.length > 0 && (
        <section className="rounded-2xl border border-[#252e47] bg-[#141a2b] p-4">
          <p className="text-sm font-bold">This shop&apos;s rewards</p>
          <ul className="mt-2 flex flex-col gap-1.5 text-sm text-slate-300">
            {perks.map((p) => (
              <li key={p} className="flex items-center gap-2">
                <Gift className="h-4 w-4 shrink-0 text-amber-300" /> {p}
              </li>
            ))}
          </ul>
        </section>
      )}

      <section>
        <p className="px-1 text-sm font-bold">Points history</p>
        {(m.points_history?.length ?? 0) === 0 && <p className="mt-2 px-1 text-sm text-slate-500">No points yet.</p>}
        <ul className="mt-2 flex flex-col divide-y divide-[#252e47]">
          {m.points_history?.map((e, i) => (
            <li key={i} className="flex items-center gap-3 px-1 py-2.5 text-sm">
              <span className="min-w-0 flex-1">
                <span className="block">{POINT_REASONS[e.reason] ?? e.reason}</span>
                <span className="block text-xs text-slate-500">
                  {e.note ? `${e.note} · ` : ""}
                  {new Date(e.at).toLocaleDateString()}
                </span>
              </span>
              <span className={`font-bold ${e.delta > 0 ? "text-emerald-300" : "text-slate-300"}`}>{e.delta > 0 ? `+${e.delta}` : e.delta}</span>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
