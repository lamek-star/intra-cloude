"use client";

import { useId, useRef, useState, type ReactNode } from "react";
import {
  ArrowRight,
  Calendar,
  Database,
  Fingerprint,
  Folder,
  History,
  KeyRound,
  LayoutGrid,
  Link2,
  Lock,
  Package,
  Trash2,
  Upload,
  Users,
  X,
  type LucideIcon,
} from "lucide-react";
import { useDialogA11y } from "@/lib/use-dialog-a11y";
import { versionLine } from "@/lib/brand";
import { BuildArt, ConnectArt, ProtectArt, StoreArt, WelcomeArt } from "@/components/tour/TourArt";

type Slide = { eyebrow: string; title: string; body: string; points: [LucideIcon, string][]; art: ReactNode; next?: string };

export const TOUR_SLIDES: Slide[] = [
  {
    eyebrow: "Welcome",
    title: "Welcome to IntraForge",
    body: "Your organization's private cloud. Files, databases and business apps for your whole team, running on your own computer, with or without the internet.",
    points: [[Folder, "Store your files and documents"], [Database, "Build databases and business apps"], [Link2, "Connect your other apps safely"]],
    art: <WelcomeArt />,
    next: "Take the tour",
  },
  {
    eyebrow: "Store",
    title: "Files, like a cloud drive",
    body: "Create buckets and folders, upload anything, and share each one with exactly the people who need it.",
    points: [[History, "Every change keeps the earlier version"], [Trash2, "Deleted files wait in Trash first"], [Users, "Share a folder, not a password"]],
    art: <StoreArt />,
  },
  {
    eyebrow: "Build",
    title: "Databases and business apps",
    body: "Design tables without code, import your spreadsheets, or install a ready-made app and start working today.",
    points: [[Package, "Spare Parts and Pharmacy, ready to install"], [Upload, "Import CSV files in a few clicks"], [LayoutGrid, "Statistics and dashboards on your data"]],
    art: <BuildArt />,
  },
  {
    eyebrow: "Connect",
    title: "Connect apps, safely",
    body: "Give every app its own key and its own environment. Try changes in Development, then move them to Production.",
    points: [[LayoutGrid, "Development, Staging and Production kept apart"], [KeyRound, "API keys and signed webhooks"], [Lock, "Internet stays off until you turn it on"]],
    art: <ConnectArt />,
  },
  {
    eyebrow: "Protect",
    title: "You decide who sees what",
    body: "Give people roles, not passwords. Every action is recorded, and your data is backed up every day.",
    points: [[Users, "Roles and sharing for every folder and app"], [Fingerprint, "Passkeys and two-step sign-in"], [Calendar, "Audit log and tested daily backups"]],
    art: <ProtectArt />,
    next: "Start using IntraForge",
  },
];

/** Five slides on what IntraForge does, shown once after the first sign-in (lib/tour.ts) and from "Take the tour". */
export function WelcomeTour({ open, onClose, version }: { open: boolean; onClose: () => void; version?: string | null }) {
  const [index, setIndex] = useState(0);
  const panelRef = useRef<HTMLDivElement>(null);
  const titleId = useId();
  const bodyId = useId();
  // Closing returns to the first slide, so "Take the tour" always starts at the beginning.
  const close = () => {
    setIndex(0);
    onClose();
  };
  useDialogA11y(open, close, panelRef);

  if (!open) return null;
  const slide = TOUR_SLIDES[index];
  const last = index === TOUR_SLIDES.length - 1;
  const next = () => (last ? close() : setIndex(index + 1));

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center p-4">
      <div className="dialog-backdrop absolute inset-0 bg-slate-900/55 backdrop-blur-[2px]" onClick={close} />
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={bodyId}
        tabIndex={-1}
        onKeyDown={(e) => {
          if (e.key === "ArrowRight" && !last) setIndex(index + 1);
          if (e.key === "ArrowLeft" && index > 0) setIndex(index - 1);
        }}
        className="dialog-panel relative grid w-full max-w-[880px] overflow-hidden rounded-2xl bg-white shadow-[0_0_0_1px_rgba(15,23,42,.08),0_30px_80px_rgba(15,23,42,.35)] outline-none md:h-[520px] md:grid-cols-[410px_1fr]"
      >
        <div
          aria-hidden="true"
          className="relative hidden overflow-hidden md:block"
          style={{
            background:
              "radial-gradient(320px 260px at 0% 0%, #dbeafe, transparent 70%), radial-gradient(300px 260px at 100% 100%, #ccfbf1, transparent 70%), linear-gradient(160deg, #f5f8ff, #f2fbf9)",
          }}
        >
          <div key={index} className="tour-art absolute inset-0">
            {slide.art}
          </div>
        </div>

        <div className="flex flex-col p-6 sm:px-[38px] sm:pt-[34px] sm:pb-[26px]">
          <button
            onClick={close}
            aria-label="Close the tour"
            className="absolute top-3.5 right-3.5 grid h-8 w-8 place-items-center rounded-lg text-slate-500 hover:bg-slate-100 hover:text-slate-900"
          >
            <X className="h-[18px] w-[18px]" />
          </button>
          <p className="text-xs font-semibold tracking-[.06em] text-brand-700 uppercase" aria-live="polite">
            {slide.eyebrow} · {index + 1} of {TOUR_SLIDES.length}
          </p>
          <h2 id={titleId} className="mt-2.5 text-[28px] leading-tight font-semibold tracking-[-0.025em] text-slate-900">
            {slide.title}
          </h2>
          <p id={bodyId} className="mt-3 text-[15px] leading-relaxed text-slate-600">
            {slide.body}
          </p>
          <ul className="mt-5 flex flex-col gap-3">
            {slide.points.map(([Icon, text]) => (
              <li key={text} className="flex items-center gap-3 text-sm text-slate-900">
                <span className="grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-brand-50 text-brand-700">
                  <Icon aria-hidden="true" className="h-[17px] w-[17px]" />
                </span>
                {text}
              </li>
            ))}
          </ul>
          {last && <p className="mt-5 text-xs text-slate-500">{versionLine(version)}</p>}

          <div className="mt-8 flex flex-wrap items-center gap-2.5 md:mt-auto">
            <div className="mr-auto flex items-center gap-1.5" role="tablist" aria-label="Tour slides">
              {TOUR_SLIDES.map((s, i) => (
                <button
                  key={s.eyebrow}
                  role="tab"
                  aria-selected={i === index}
                  aria-label={`Slide ${i + 1}: ${s.title}`}
                  onClick={() => setIndex(i)}
                  className={`h-[7px] rounded-full transition-all ${i === index ? "w-[22px] bg-brand-600" : "w-[7px] bg-slate-300 hover:bg-slate-400"}`}
                />
              ))}
            </div>
            {!last && (
              <button onClick={close} className="h-[38px] rounded-lg px-2 text-sm font-semibold text-slate-500 hover:text-slate-900">
                Skip tour
              </button>
            )}
            {index > 0 && (
              <button
                onClick={() => setIndex(index - 1)}
                className="h-[38px] rounded-lg border border-slate-300 bg-white px-4 text-sm font-semibold text-slate-900 hover:bg-slate-50"
              >
                Back
              </button>
            )}
            <button
              onClick={next}
              className="inline-flex h-[38px] items-center gap-2 rounded-lg bg-brand-600 px-4 text-sm font-semibold text-white hover:bg-accent-hover"
            >
              {slide.next ?? "Next"}
              <ArrowRight aria-hidden="true" className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
