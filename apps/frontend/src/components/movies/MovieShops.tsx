"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useId, useState } from "react";
import { useQuery, useQueries, useQueryClient } from "@tanstack/react-query";
import { ChevronRight, Film, Play, Plus } from "lucide-react";
import { api, type Project, type Workspace } from "@/lib/api";
import { agentOnline, movies } from "@/lib/movies";
import { organizationsQuery } from "@/lib/queries";
import { PageLoading } from "@/components/ui";
import { dark, DarkDialog, message } from "./Dialogs";

/** Every movie shop the person may see, across their organizations, and a way to open a new one. */
export function MovieShops() {
  const orgs = useQuery(organizationsQuery);
  const shops = useQueries({
    queries: (orgs.data ?? []).map((o) => ({ queryKey: ["movies", "shops", o.id], queryFn: () => movies.shops(o.id) })),
  });
  const [creating, setCreating] = useState(false);

  if (!orgs.data) return <PageLoading />;
  const all = shops.flatMap((q, i) => (q.data ?? []).map((s) => ({ shop: s, org: orgs.data[i] })));
  const loading = shops.some((q) => q.isLoading);

  return (
    <div data-theme="light" className="-m-4 min-h-[calc(100vh)] bg-[#0a0d16] bg-[radial-gradient(900px_500px_at_85%_-10%,rgba(245,165,36,.10),transparent_60%)] p-4 text-slate-100 sm:-m-8 sm:p-8">
      <div className="mx-auto max-w-5xl">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="text-[11px] font-semibold tracking-[.1em] text-amber-300 uppercase">Movie Shop</p>
            <h1 className="mt-1 text-3xl font-semibold tracking-wide uppercase" style={{ fontFamily: "var(--font-display), sans-serif" }}>
              Your movie shops
            </h1>
            <p className="mt-1 text-sm text-slate-400">The films and series on your own drives, as a catalogue you sell from.</p>
          </div>
          <button className={dark.amber} onClick={() => setCreating(true)}>
            <Plus className="h-4 w-4" strokeWidth={2.6} /> New movie shop
          </button>
        </div>

        <div className="mt-8 grid gap-4 sm:grid-cols-2">
          {all.map(({ shop, org }) => (
            <Link
              key={shop.id}
              href={`/movies/${shop.id}`}
              className="group flex items-center gap-4 rounded-2xl border border-[#252e47] bg-[#141a2b] p-5 transition hover:-translate-y-0.5 hover:border-amber-400/50 hover:shadow-[0_18px_40px_-18px_rgba(0,0,0,.9)]"
            >
              <span className="grid h-12 w-12 place-items-center rounded-xl bg-[radial-gradient(circle_at_30%_25%,#ffd27a,#f5a524_60%,#c97b05)] text-amber-950">
                <Play className="h-5 w-5" strokeWidth={2.6} />
              </span>
              <span className="min-w-0 flex-1">
                <span className="block truncate text-base font-bold">{shop.name}</span>
                <span className="block text-xs text-slate-500">
                  {org.name} · {shop.titles.toLocaleString()} titles · {agentOnline(shop.agent_seen_at) ? "media agent running" : "media agent not running"}
                </span>
              </span>
              <ChevronRight className="h-5 w-5 text-slate-500 transition group-hover:translate-x-0.5 group-hover:text-amber-300" />
            </Link>
          ))}
        </div>
        {!loading && all.length === 0 && (
          <div className="mt-10 rounded-2xl border border-dashed border-[#323c5a] p-10 text-center">
            <Film className="mx-auto h-8 w-8 text-amber-300" />
            <p className="mt-3 font-semibold">No movie shop yet</p>
            <p className="mt-1 text-sm text-slate-400">Open one, connect the shop PC&apos;s drives, and your folders become the catalogue.</p>
          </div>
        )}
      </div>
      {creating && <CreateShopDialog organizations={orgs.data} onClose={() => setCreating(false)} />}
    </div>
  );
}

export function CreateShopDialog({ organizations, onClose }: { organizations: { id: string; name: string }[]; onClose: () => void }) {
  const qc = useQueryClient();
  const router = useRouter();
  const [org, setOrg] = useState(organizations[0]?.id ?? "");
  const [projects, setProjects] = useState<(Project & { workspaceName: string })[]>([]);
  const [project, setProject] = useState("");
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const ids = { org: useId(), project: useId(), name: useId() };

  useEffect(() => {
    if (!org) return;
    let alive = true;
    (async () => {
      try {
        const workspaces = await api.get<Workspace[]>(`/organizations/${org}/workspaces/`);
        const lists = await Promise.all(workspaces.map(async (w) => (await api.get<Project[]>(`/workspaces/${w.id}/projects/`)).map((p) => ({ ...p, workspaceName: w.name }))));
        if (!alive) return;
        const flat = lists.flat();
        setProjects(flat);
        setProject(flat[0]?.id ?? "");
      } catch (err) {
        if (alive) setError(message(err));
      }
    })();
    return () => {
      alive = false;
    };
  }, [org]);

  async function create() {
    setBusy(true);
    setError(null);
    try {
      const shop = await movies.createShop(org, name.trim(), project);
      await qc.invalidateQueries({ queryKey: ["movies", "shops", org] });
      router.push(`/movies/${shop.id}`);
    } catch (err) {
      setError(message(err));
      setBusy(false);
    }
  }

  return (
    <DarkDialog title="New movie shop" onClose={onClose}>
      <div className="flex flex-col gap-3">
        <div>
          <label htmlFor={ids.name} className={dark.label}>
            Shop name
          </label>
          <input id={ids.name} className={dark.input} maxLength={120} placeholder="e.g. Lamek Movie Shop" value={name} onChange={(e) => setName(e.target.value)} />
        </div>
        <div>
          <label htmlFor={ids.org} className={dark.label}>
            Organization
          </label>
          <select id={ids.org} className={dark.input} value={org} onChange={(e) => setOrg(e.target.value)}>
            {organizations.map((o) => (
              <option key={o.id} value={o.id}>
                {o.name}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor={ids.project} className={dark.label}>
            Project (keeps the covers)
          </label>
          <select id={ids.project} className={dark.input} value={project} onChange={(e) => setProject(e.target.value)}>
            {projects.map((p) => (
              <option key={p.id} value={p.id}>
                {p.workspaceName} › {p.name}
              </option>
            ))}
          </select>
          {projects.length === 0 && <p className="mt-1 text-xs text-slate-500">Create a workspace and a project in this organization first.</p>}
        </div>
      </div>
      {error && <p className="mt-3 text-sm text-red-300">{error}</p>}
      <div className="mt-5 flex justify-end gap-2">
        <button className={dark.btn} onClick={onClose}>
          Cancel
        </button>
        <button className={dark.amber} disabled={busy || !name.trim() || !project} onClick={() => void create()}>
          <Plus className="h-4 w-4" strokeWidth={2.6} /> {busy ? "Opening..." : "Open the shop"}
        </button>
      </div>
    </DarkDialog>
  );
}
