"use client";

import { useEffect, useId, useMemo, useState } from "react";
import { ArrowDown, ArrowUp, Eye, ImagePlus, Megaphone, MousePointerClick, Pencil, Plus, Trash2 } from "lucide-react";
import { movies, type AdInput, type MovieTitle, type ShopAd } from "@/lib/movies";
import { useConfirm } from "@/components/ConfirmProvider";
import { AdBanner } from "./AdBanner";
import { dark, DarkDialog, message } from "./Dialogs";

type Draft = { title: string; text: string; advertiser: string; target: "none" | "film" | "link"; film: string; link: string; starts_on: string; ends_on: string };

const EMPTY: Draft = { title: "", text: "", advertiser: "", target: "none", film: "", link: "", starts_on: "", ends_on: "" };

function state(ad: ShopAd): [string, string] {
  if (ad.showing) return ["Showing", "border-emerald-400/30 bg-emerald-400/10 text-emerald-200"];
  if (!ad.active) return ["Off", "border-[#323c5a] text-slate-400"];
  const today = new Date().toISOString().slice(0, 10);
  if (ad.starts_on && ad.starts_on > today) return [`From ${ad.starts_on}`, "border-sky-400/30 bg-sky-400/10 text-sky-200"];
  return ["Ended", "border-[#323c5a] text-slate-400"];
}

/** The shop's ads on its customer portal: write one, give it a picture and dates, switch it on or off, see its views. */
export function AdsDialog({ shopId, shopName, onClose }: { shopId: string; shopName: string; onClose: () => void }) {
  const confirm = useConfirm();
  const [list, setList] = useState<ShopAd[] | null>(null);
  const [films, setFilms] = useState<MovieTitle[]>([]);
  const [editing, setEditing] = useState<ShopAd | "new" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [version, setVersion] = useState(0);

  useEffect(() => {
    let live = true;
    movies
      .ads(shopId)
      .then((r) => live && setList(r))
      .catch((err) => live && setError(message(err)));
    return () => {
      live = false;
    };
  }, [shopId, version]);

  useEffect(() => {
    let live = true;
    movies
      .titles(shopId, { limit: 300, sort: "title" })
      .then((r) => live && setFilms(r.results))
      .catch(() => undefined);
    return () => {
      live = false;
    };
  }, [shopId]);

  const reload = () => setVersion((v) => v + 1);
  async function run(task: () => Promise<unknown>) {
    setError(null);
    try {
      await task();
      reload();
    } catch (err) {
      setError(message(err));
    }
  }
  async function move(index: number, by: number) {
    if (!list) return;
    const order = [...list];
    const [moved] = order.splice(index, 1);
    order.splice(index + by, 0, moved);
    await run(() => Promise.all(order.map((a, i) => (a.position === i ? null : movies.updateAd(a.id, { position: i })))));
  }

  if (editing) {
    return (
      <DarkDialog title={editing === "new" ? "New ad" : "Edit ad"} onClose={onClose} wide>
        <AdEditor
          shopId={shopId}
          shopName={shopName}
          ad={editing === "new" ? null : editing}
          films={films}
          position={list?.length ?? 0}
          onDone={() => {
            setEditing(null);
            reload();
          }}
        />
      </DarkDialog>
    );
  }

  return (
    <DarkDialog title="Ads on your portal" onClose={onClose} wide>
      <p className="text-sm text-slate-400">
        Customers see these at the top of the portal, marked &ldquo;Ad&rdquo;. Advertise your own films, or another shop or business you work
        with. They show only on this shop&apos;s portal.
      </p>
      {error && <p className="mt-3 rounded-lg bg-red-400/10 px-3 py-2 text-sm text-red-200">{error}</p>}
      <div className="mt-4 flex justify-end">
        <button className={dark.amber} onClick={() => setEditing("new")}>
          <Plus className="h-4 w-4" strokeWidth={2.6} /> New ad
        </button>
      </div>
      {list && list.length === 0 && (
        <div className="mt-6 rounded-2xl border border-dashed border-[#323c5a] p-8 text-center">
          <Megaphone className="mx-auto h-8 w-8 text-amber-300" />
          <p className="mt-2 font-semibold">No ads yet</p>
          <p className="text-sm text-slate-500">A new film, a weekend offer, a phone shop next door...</p>
        </div>
      )}
      <ul className="mt-4 flex max-h-[55vh] flex-col gap-2 overflow-y-auto">
        {list?.map((ad, i) => {
          const [label, tone] = state(ad);
          return (
            <li key={ad.id} className="flex items-center gap-3 rounded-xl border border-[#252e47] bg-[#0f1422] p-2.5">
              <div className="w-36 shrink-0">
                <AdBanner ad={ad} compact shopName={shopName} src={movies.adPictureUrl(ad.id, ad.picture_version)} />
              </div>
              <div className="min-w-0 flex-1">
                <p className="flex flex-wrap items-center gap-2 text-sm font-semibold">
                  <span className="truncate">{ad.title}</span>
                  <span className={`rounded-full border px-2 py-px text-[10.5px] font-semibold ${tone}`}>{label}</span>
                </p>
                <p className="truncate text-[11px] text-slate-500">
                  {ad.advertiser ? `For ${ad.advertiser}` : "For your shop"}
                  {ad.film_title ? ` · opens ${ad.film_title}` : ad.link ? ` · ${ad.link}` : ""}
                  {ad.ends_on ? ` · until ${ad.ends_on}` : ""}
                </p>
                <p className="mt-1 flex items-center gap-3 text-[11px] text-slate-400">
                  <span className="inline-flex items-center gap-1">
                    <Eye className="h-3.5 w-3.5" /> {ad.views.toLocaleString()} views
                  </span>
                  <span className="inline-flex items-center gap-1">
                    <MousePointerClick className="h-3.5 w-3.5" /> {ad.taps.toLocaleString()} taps
                  </span>
                </p>
              </div>
              <div className="flex shrink-0 items-center gap-1">
                <label className="mr-1 inline-flex cursor-pointer items-center gap-1.5 text-[11px] text-slate-300">
                  <input type="checkbox" className="h-4 w-4 accent-amber-400" checked={ad.active} onChange={(e) => void run(() => movies.updateAd(ad.id, { active: e.target.checked }))} />
                  On
                </label>
                <button className="rounded-md p-1.5 text-slate-400 hover:bg-white/5 hover:text-white disabled:opacity-30" disabled={i === 0} onClick={() => void move(i, -1)} aria-label={`Move ${ad.title} up`}>
                  <ArrowUp className="h-4 w-4" />
                </button>
                <button
                  className="rounded-md p-1.5 text-slate-400 hover:bg-white/5 hover:text-white disabled:opacity-30"
                  disabled={i === list.length - 1}
                  onClick={() => void move(i, 1)}
                  aria-label={`Move ${ad.title} down`}
                >
                  <ArrowDown className="h-4 w-4" />
                </button>
                <button className="rounded-md p-1.5 text-slate-400 hover:bg-white/5 hover:text-white" onClick={() => setEditing(ad)} aria-label={`Edit ${ad.title}`}>
                  <Pencil className="h-4 w-4" />
                </button>
                <button
                  className="rounded-md p-1.5 text-slate-400 hover:bg-white/5 hover:text-red-300"
                  aria-label={`Delete ${ad.title}`}
                  onClick={async () => {
                    if (await confirm({ title: `Delete "${ad.title}"?`, description: "It leaves the portal at once.", confirmLabel: "Delete", danger: true }))
                      void run(() => movies.deleteAd(ad.id));
                  }}
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            </li>
          );
        })}
      </ul>
      <div className="mt-4 flex justify-end">
        <button className={dark.btn} onClick={onClose}>
          Close
        </button>
      </div>
    </DarkDialog>
  );
}

function AdEditor({
  shopId,
  shopName,
  ad,
  films,
  position,
  onDone,
}: {
  shopId: string;
  shopName: string;
  ad: ShopAd | null;
  films: MovieTitle[];
  position: number;
  onDone: () => void;
}) {
  const [draft, setDraft] = useState<Draft>(
    ad
      ? {
          title: ad.title,
          text: ad.text,
          advertiser: ad.advertiser,
          target: ad.film ? "film" : ad.link ? "link" : "none",
          film: ad.film ?? "",
          link: ad.link,
          starts_on: ad.starts_on ?? "",
          ends_on: ad.ends_on ?? "",
        }
      : EMPTY,
  );
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const ids = { title: useId(), text: useId(), advertiser: useId(), film: useId(), link: useId(), from: useId(), to: useId(), file: useId() };
  const set = (key: keyof Draft) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => setDraft({ ...draft, [key]: e.target.value });

  // The chosen picture, shown before it is uploaded; the temporary address is released when it changes.
  const preview = useMemo(() => (file ? URL.createObjectURL(file) : null), [file]);
  useEffect(() => () => void (preview && URL.revokeObjectURL(preview)), [preview]);

  async function save() {
    setBusy(true);
    setError(null);
    const body: AdInput = {
      title: draft.title.trim(),
      text: draft.text.trim(),
      advertiser: draft.advertiser.trim(),
      film: draft.target === "film" ? draft.film || null : null,
      link: draft.target === "link" ? draft.link.trim() : "",
      starts_on: draft.starts_on || null,
      ends_on: draft.ends_on || null,
    };
    try {
      const saved = ad ? await movies.updateAd(ad.id, body) : await movies.createAd(shopId, { ...body, position });
      if (file) await movies.uploadAdPicture(saved.id, file);
      onDone();
    } catch (err) {
      setError(message(err));
    } finally {
      setBusy(false);
    }
  }

  const bannerAd = {
    title: draft.title,
    text: draft.text,
    advertiser: draft.advertiser,
    film: draft.target === "film" && draft.film ? draft.film : null,
    link: draft.target === "link" ? draft.link : "",
    has_picture: Boolean(preview || ad?.has_picture),
  };

  return (
    <div className="grid gap-6 md:grid-cols-[1fr_320px]">
      <div className="flex flex-col gap-3">
        <div>
          <label htmlFor={ids.title} className={dark.label}>
            Title
          </label>
          <input id={ids.title} className={dark.input} maxLength={80} value={draft.title} onChange={set("title")} placeholder="New this week: Desert Wind" />
        </div>
        <div>
          <label htmlFor={ids.text} className={dark.label}>
            Text <span className="font-normal text-slate-500">(optional)</span>
          </label>
          <textarea id={ids.text} className={`${dark.input} h-20 py-2`} maxLength={300} value={draft.text} onChange={set("text")} />
        </div>
        <div>
          <label htmlFor={ids.advertiser} className={dark.label}>
            For <span className="font-normal text-slate-500">(another shop or business; empty = your shop)</span>
          </label>
          <input id={ids.advertiser} className={dark.input} maxLength={80} value={draft.advertiser} onChange={set("advertiser")} placeholder={shopName} />
        </div>
        <fieldset>
          <legend className={dark.label}>When a customer taps it</legend>
          <div className="grid grid-cols-3 gap-2">
            {(
              [
                ["none", "Nothing"],
                ["film", "Open a film"],
                ["link", "Open a web page"],
              ] as const
            ).map(([value, label]) => (
              <label key={value} className={`flex h-9 cursor-pointer items-center justify-center rounded-lg border text-xs font-semibold ${draft.target === value ? "border-amber-400 bg-amber-400/10 text-amber-200" : "border-[#323c5a] text-slate-300"}`}>
                <input type="radio" name="ad-target" className="sr-only" checked={draft.target === value} onChange={() => setDraft({ ...draft, target: value })} />
                {label}
              </label>
            ))}
          </div>
        </fieldset>
        {draft.target === "film" && (
          <div>
            <label htmlFor={ids.film} className={dark.label}>
              Film
            </label>
            <select id={ids.film} className={dark.input} value={draft.film} onChange={set("film")}>
              <option value="">Choose a film...</option>
              {films.map((f) => (
                <option key={f.id} value={f.id}>
                  {f.title} {f.year ? `(${f.year})` : ""} · {f.category}
                </option>
              ))}
            </select>
          </div>
        )}
        {draft.target === "link" && (
          <div>
            <label htmlFor={ids.link} className={dark.label}>
              Web address
            </label>
            <input id={ids.link} className={dark.input} type="url" maxLength={300} value={draft.link} onChange={set("link")} placeholder="https://..." />
            <p className="mt-1 text-[11px] text-slate-500">Opens in a new tab. A page on the internet works only when the customer&apos;s phone has internet.</p>
          </div>
        )}
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label htmlFor={ids.from} className={dark.label}>
              First day <span className="font-normal text-slate-500">(optional)</span>
            </label>
            <input id={ids.from} type="date" className={dark.input} value={draft.starts_on} onChange={set("starts_on")} />
          </div>
          <div>
            <label htmlFor={ids.to} className={dark.label}>
              Last day <span className="font-normal text-slate-500">(optional)</span>
            </label>
            <input id={ids.to} type="date" className={dark.input} value={draft.ends_on} onChange={set("ends_on")} />
          </div>
        </div>
        {error && <p className="rounded-lg bg-red-400/10 px-3 py-2 text-sm text-red-200">{error}</p>}
        <div className="mt-1 flex justify-end gap-2">
          <button className={dark.btn} onClick={onDone} disabled={busy}>
            Cancel
          </button>
          <button className={dark.amber} onClick={() => void save()} disabled={busy || !draft.title.trim()}>
            {busy ? "Saving..." : ad ? "Save" : "Add the ad"}
          </button>
        </div>
      </div>
      <div>
        <p className={dark.label}>How customers see it</p>
        <AdBanner ad={bannerAd} shopName={shopName} src={preview ?? (ad ? movies.adPictureUrl(ad.id, ad.picture_version) : undefined)} />
        <label htmlFor={ids.file} className={`${dark.btn} mt-3 w-full cursor-pointer`}>
          <ImagePlus className="h-4 w-4" /> {preview || ad?.has_picture ? "Change the picture" : "Add a picture"}
        </label>
        <input id={ids.file} type="file" accept="image/jpeg,image/png,image/webp" className="sr-only" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
        <p className="mt-1.5 text-[11px] text-slate-500">JPEG, PNG or WebP, up to 2 MB. A wide picture fits best (16:9 on phones, 16:7 on larger screens; keep the right side for the picture).</p>
      </div>
    </div>
  );
}
