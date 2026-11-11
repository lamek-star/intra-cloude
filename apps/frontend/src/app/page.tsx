"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import {
  ArrowRight,
  Database,
  Folder,
  HardDrive,
  History,
  LayoutGrid,
  Link2,
  PlayCircle,
  ScrollText,
  ShieldCheck,
  WifiOff,
  type LucideIcon,
} from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import { COPYRIGHT } from "@/lib/brand";
import { LinkButton, PageLoading } from "@/components/ui";
import { ProductDemo } from "@/components/home/ProductDemo";
import { Reveal } from "@/components/home/Reveal";
import { SetupWalkthrough } from "@/components/home/SetupWalkthrough";
import s from "@/components/home/home.module.css";

const PROMISES: [LucideIcon, string][] = [
  [WifiOff, "No internet needed"],
  [HardDrive, "Runs on one Windows PC"],
  [History, "Tested daily backups"],
  [ScrollText, "Every action audited"],
];

const FEATURES: { icon: LucideIcon; tone: string; title: string; text: string }[] = [
  { icon: Folder, tone: "bg-brand-50 text-brand-700", title: "Files, like a cloud drive", text: "Buckets and folders for the whole team. Every change keeps the earlier version; deleted files wait in Trash." },
  { icon: Database, tone: "bg-teal-50 text-teal-700", title: "Databases without code", text: "Design tables, import spreadsheets and CSV files, then explore, filter and chart your own data." },
  { icon: LayoutGrid, tone: "bg-violet-50 text-violet-700", title: "Ready-made business apps", text: "Spare Parts, Pharmacy and IntraForge Pay install in one click, with stock, sales, labels and receipts." },
  { icon: Link2, tone: "bg-amber-50 text-amber-700", title: "Connect your other apps", text: "Each app gets its own key and environment: Development, Staging and Production stay apart." },
  { icon: ShieldCheck, tone: "bg-green-50 text-green-700", title: "You decide who sees what", text: "Roles and sharing per folder, database and app. Passkeys and two-step sign-in for the people who matter." },
  { icon: History, tone: "bg-slate-100 text-slate-700", title: "Backups that are proven", text: "A backup every day, and every week a test restore into a throw-away copy proves it can really come back." },
];

/** The public home page: what IntraForge is, a running demo with sample data, and how an installation goes. */
export default function LandingPage() {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && user) router.replace("/dashboard");
  }, [loading, user, router]);

  if (loading || user) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-surface-canvas">
        <PageLoading />
      </div>
    );
  }

  return (
    <div className="flex min-h-screen flex-col bg-surface-canvas">
      <header className="sticky top-0 z-40 border-b border-slate-200/70 bg-white/80 backdrop-blur-md">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3 sm:px-8">
          <Link href="/" className="flex items-center gap-2.5">
            {/* eslint-disable-next-line @next/next/no-img-element -- fixed-size static brand asset */}
            <img src="/brand/icon-64.png" alt="" width={32} height={32} className="h-8 w-8" />
            <span className="text-base font-semibold text-text-primary">IntraForge</span>
          </Link>
          <nav aria-label="Home page" className="hidden items-center gap-7 text-sm font-medium text-slate-600 md:flex">
            <a href="#demo" className="transition-colors hover:text-slate-900">Demo</a>
            <a href="#setup" className="transition-colors hover:text-slate-900">How setup works</a>
            <a href="#features" className="transition-colors hover:text-slate-900">Features</a>
          </nav>
          <div className="flex items-center gap-3">
            <Link href="/login" className="hidden text-sm font-medium text-slate-600 transition-colors hover:text-text-primary sm:inline">
              Sign in
            </Link>
            <LinkButton href="/register" variant="primary">
              Get Started
            </LinkButton>
          </div>
        </div>
      </header>

      <main id="main-content" className="flex-1">
        {/* ---- Hero ---- */}
        <section id="demo" className="relative scroll-mt-16 overflow-hidden">
          <div aria-hidden="true" className="pointer-events-none absolute inset-0">
            <div className={`${s.glow} -top-24 -left-24 h-96 w-96 bg-brand-100`} />
            <div className={`${s.glow} top-40 right-[-6rem] h-[28rem] w-[28rem] bg-teal-50`} style={{ animationDelay: "-6s" }} />
            <svg className="absolute inset-0 h-full w-full opacity-60" preserveAspectRatio="xMidYMid slice" viewBox="0 0 1200 700" fill="none">
              <g stroke="#c7d7f5" strokeWidth="1" className={s.meshLine}>
                <path d="M60 120 L240 60 L420 160 L610 90 L820 150 L1010 70 L1160 140" />
                <path d="M40 560 L230 610 L400 520 L590 600 L780 540 L980 620 L1170 560" />
              </g>
              {[[240, 60], [420, 160], [610, 90], [1010, 70], [230, 610], [590, 600], [980, 620]].map(([cx, cy], i) => (
                <circle key={i} cx={cx} cy={cy} r="4" fill="#93c5fd" className={s.pulse} style={{ animationDelay: `${i * 0.45}s` }} />
              ))}
            </svg>
          </div>

          <div className="relative mx-auto grid max-w-6xl items-center gap-12 px-4 pt-14 pb-16 sm:px-8 sm:pt-20 lg:grid-cols-[0.92fr_1.08fr] lg:gap-14 lg:pb-24">
            <div>
              <p className={`${s.rise} inline-flex items-center gap-2 rounded-full border border-brand-100 bg-white/80 px-3 py-1 text-xs font-semibold text-brand-700 shadow-sm`}>
                <span className="relative flex h-2 w-2">
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-green-400 opacity-60" />
                  <span className="relative inline-flex h-2 w-2 rounded-full bg-green-500" />
                </span>
                Local Edition · runs without the internet
              </p>
              <h1 className={`${s.rise} mt-5 text-4xl font-bold tracking-tight text-navy sm:text-5xl lg:text-[3.4rem] lg:leading-[1.08]`} style={{ animationDelay: "80ms" }}>
                Forge your <br className="hidden sm:block" />
                <span className="bg-gradient-to-r from-brand-600 via-teal-500 to-green-500 bg-clip-text whitespace-nowrap text-transparent">private cloud</span>
              </h1>
              <p className={`${s.rise} mt-5 max-w-xl text-lg leading-relaxed text-slate-600`} style={{ animationDelay: "160ms" }}>
                Files, databases and business apps for your whole organization, on hardware you own. Install it in
                minutes; your data never leaves the building.
              </p>
              <div className={`${s.rise} mt-8 flex flex-wrap items-center gap-3`} style={{ animationDelay: "240ms" }}>
                <LinkButton href="/register" variant="primary" className="group !px-6 !py-3 !text-base">
                  Get Started
                  <ArrowRight aria-hidden="true" className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
                </LinkButton>
                <a
                  href="#setup"
                  className="inline-flex items-center gap-2 rounded-xl border border-slate-300 bg-white px-6 py-3 text-base font-medium text-slate-800 shadow-sm transition-all hover:-translate-y-px hover:border-slate-400 hover:shadow"
                >
                  <PlayCircle aria-hidden="true" className="h-4 w-4 text-brand-600" />
                  See how setup works
                </a>
              </div>
              <ul className={`${s.rise} mt-8 grid max-w-md grid-cols-2 gap-x-4 gap-y-2.5`} style={{ animationDelay: "320ms" }}>
                {PROMISES.map(([Icon, text]) => (
                  <li key={text} className="flex items-center gap-2 text-sm text-slate-600">
                    <Icon aria-hidden="true" className="h-4 w-4 text-teal-600" />
                    {text}
                  </li>
                ))}
              </ul>
            </div>
            <ProductDemo />
          </div>
        </section>

        {/* ---- Setup walkthrough ---- */}
        <section id="setup" className="scroll-mt-16 border-y border-slate-200/70 bg-white py-20 sm:py-24">
          <div className="mx-auto max-w-6xl px-4 sm:px-8">
            <Reveal className="mx-auto max-w-2xl text-center">
              <p className="text-xs font-semibold tracking-[.12em] text-brand-700 uppercase">How setup works</p>
              <h2 className="mt-3 text-3xl font-semibold tracking-tight text-balance text-navy sm:text-4xl">From download to running in about 15 minutes</h2>
              <p className="mt-4 text-base text-balance text-slate-600">
                One file installs everything, checks the computer first, and keeps your data on it. No server room, no
                accounts in someone else&apos;s cloud.
              </p>
            </Reveal>
            <Reveal className="mt-14" delay={120}>
              <SetupWalkthrough />
            </Reveal>
          </div>
        </section>

        {/* ---- Features ---- */}
        <section id="features" className="mx-auto max-w-6xl scroll-mt-16 px-4 py-20 sm:px-8 sm:py-24">
          <Reveal className="mx-auto max-w-2xl text-center">
            <p className="text-xs font-semibold tracking-[.12em] text-brand-700 uppercase">Everything in one place</p>
            <h2 className="mt-3 text-3xl font-semibold tracking-tight text-balance text-navy sm:text-4xl">Build. Store. Connect. Privately.</h2>
          </Reveal>
          <div className="mt-12 grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {FEATURES.map((f, i) => (
              <Reveal key={f.title} delay={(i % 3) * 90}>
                <div className="group h-full rounded-2xl border border-slate-200/80 bg-white p-6 shadow-[0_1px_2px_rgba(15,23,42,.04)] transition-all duration-300 hover:-translate-y-1 hover:border-brand-100 hover:shadow-[0_18px_40px_-18px_rgba(30,58,138,.3)]">
                  <span className={`grid h-11 w-11 place-items-center rounded-xl transition-transform duration-300 group-hover:scale-110 ${f.tone}`}>
                    <f.icon aria-hidden="true" className="h-5 w-5" />
                  </span>
                  <h3 className="mt-4 text-base font-semibold text-text-primary">{f.title}</h3>
                  <p className="mt-1.5 text-sm leading-relaxed text-slate-600">{f.text}</p>
                </div>
              </Reveal>
            ))}
          </div>
        </section>

        {/* ---- Call to action ---- */}
        <section className="px-4 pb-20 sm:px-8">
          <Reveal>
            <div className="relative mx-auto max-w-6xl overflow-hidden rounded-3xl bg-navy px-6 py-14 text-center sm:px-12">
              <div aria-hidden="true" className={`${s.glow} -top-20 left-1/4 h-72 w-72 bg-brand-500/40`} />
              <div aria-hidden="true" className={`${s.glow} right-1/4 -bottom-24 h-72 w-72 bg-teal-500/30`} style={{ animationDelay: "-9s" }} />
              <h2 className="relative text-3xl font-semibold tracking-tight text-balance text-white sm:text-4xl">Ready to forge your private cloud?</h2>
              <p className="relative mx-auto mt-3 max-w-xl text-base text-slate-300">
                Create the owner account and invite your team. Everything stays on this computer.
              </p>
              <div className="relative mt-8 flex flex-wrap items-center justify-center gap-3">
                <LinkButton href="/register" variant="primary" className="!px-6 !py-3 !text-base">
                  Get Started
                </LinkButton>
                <Link href="/login" className="rounded-xl px-5 py-3 text-base font-medium text-white ring-1 ring-white/25 transition-colors hover:bg-white/10">
                  Sign in
                </Link>
              </div>
            </div>
          </Reveal>
        </section>
      </main>

      <footer className="border-t border-slate-200/70 bg-white py-8">
        <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-3 px-4 text-sm text-slate-500 sm:flex-row sm:px-8">
          <div className="flex items-center gap-2">
            {/* eslint-disable-next-line @next/next/no-img-element -- fixed-size static brand asset */}
            <img src="/brand/icon-48.png" alt="" width={20} height={20} className="h-5 w-5" />
            <span className="font-medium text-slate-700">IntraForge</span>
            <span aria-hidden="true">·</span>
            <span>Self-hosted, local-first business infrastructure</span>
          </div>
          <p>{COPYRIGHT}. All rights reserved.</p>
        </div>
      </footer>
    </div>
  );
}
