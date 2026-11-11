"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";
import { Download, Fingerprint, KeyRound, Laptop, Monitor, MonitorDown, Smartphone, UserRoundPlus, Users } from "lucide-react";
import { usePrefersReducedMotion } from "@/lib/use-reduced-motion";
import s from "./home.module.css";

type Step = { icon: typeof Download; title: string; time: string; text: string; visual: ReactNode };

function Shot({ src, alt }: { src: string; alt: string }) {
  return (
    // eslint-disable-next-line @next/next/no-img-element -- a fixed screenshot of the real Setup window, served as-is
    <img src={src} alt={alt} width={1100} height={700} className="h-auto w-full rounded-xl shadow-[0_0_0_1px_rgba(15,23,42,.08),0_24px_50px_-18px_rgba(15,23,42,.45)]" />
  );
}

function OwnerCard() {
  return (
    <div className="mx-auto w-full max-w-sm rounded-2xl bg-white p-6 shadow-[0_0_0_1px_rgba(15,23,42,.08),0_24px_50px_-18px_rgba(15,23,42,.35)]">
      <div className="flex items-center gap-2">
        {/* eslint-disable-next-line @next/next/no-img-element -- fixed-size static brand asset */}
        <img src="/brand/icon-48.png" alt="" width={24} height={24} />
        <span className="text-sm font-semibold text-slate-900">Create the owner account</span>
      </div>
      {[["Name", "Selam Tesfaye"], ["Email", "selam@shop.local"], ["Password", "••••••••••••"]].map(([label, value], i) => (
        <div key={label} className={`mt-3 ${s.pop}`} style={{ animationDelay: `${150 + i * 120}ms` }}>
          <p className="text-[11px] font-medium text-slate-500">{label}</p>
          <p className="mt-1 rounded-md border border-slate-200 px-2.5 py-1.5 text-sm text-slate-900">{value}</p>
        </div>
      ))}
      <div className={`mt-4 flex items-center gap-2 rounded-lg bg-brand-50 p-2.5 text-xs text-brand-700 ${s.pop}`} style={{ animationDelay: "560ms" }}>
        <Fingerprint className="h-4 w-4 shrink-0" />
        Then add your phone as a passkey: the owner signs in with it.
      </div>
    </div>
  );
}

function TeamPicture() {
  const devices: [typeof Monitor, string, string][] = [
    [Monitor, "Counter PC", "left-[6%] top-[12%]"],
    [Laptop, "Office laptop", "right-[4%] top-[8%]"],
    [Smartphone, "Owner's phone", "left-[10%] bottom-[8%]"],
    [Monitor, "Store room PC", "right-[8%] bottom-[10%]"],
  ];
  return (
    <div className="relative mx-auto aspect-[4/3] w-full max-w-md">
      <svg className="absolute inset-0 h-full w-full" viewBox="0 0 400 300" fill="none" aria-hidden="true">
        <g stroke="#93c5fd" strokeWidth="2" className={s.meshLine}>
          <path d="M200 150 L70 60" />
          <path d="M200 150 L330 52" />
          <path d="M200 150 L80 245" />
          <path d="M200 150 L320 240" />
        </g>
      </svg>
      <div className={`absolute top-1/2 left-1/2 grid h-24 w-24 -translate-x-1/2 -translate-y-1/2 place-items-center rounded-3xl bg-white shadow-[0_0_0_10px_rgba(255,255,255,.6),0_20px_40px_-12px_rgba(30,58,138,.35)] ${s.float}`}>
        {/* eslint-disable-next-line @next/next/no-img-element -- fixed-size static brand asset */}
        <img src="/brand/icon-96.png" alt="" width={64} height={64} />
      </div>
      {devices.map(([Icon, label, pos], i) => (
        <div key={label} className={`absolute ${pos} flex items-center gap-2 rounded-full bg-white py-1.5 pr-3 pl-1.5 text-xs font-semibold text-slate-900 shadow-[0_0_0_1px_rgba(15,23,42,.06),0_8px_20px_rgba(30,58,138,.14)] ${s.pop}`} style={{ animationDelay: `${120 + i * 140}ms` }}>
          <span className="grid h-7 w-7 place-items-center rounded-full bg-brand-50 text-brand-700"><Icon className="h-3.5 w-3.5" /></span>
          {label}
        </div>
      ))}
    </div>
  );
}

const STEPS: Step[] = [
  {
    icon: Download,
    title: "Run Setup",
    time: "1 minute",
    text: "Double-click IntraForge-Setup. It checks the computer first and asks only where to keep your data.",
    visual: <Shot src="/home/setup-choose.webp" alt="IntraForge Setup, first screen: choose the install and data folders" />,
  },
  {
    icon: MonitorDown,
    title: "It installs itself",
    time: "About 10 minutes",
    text: "Everything it needs is inside the file, so no internet is needed. It shows each step while it works.",
    visual: <Shot src="/home/setup-install.webp" alt="IntraForge Setup installing, with the list of steps and a progress bar" />,
  },
  {
    icon: UserRoundPlus,
    title: "Create the owner account",
    time: "2 minutes",
    text: "Setup opens IntraForge in your browser. The first account is the owner, who controls everything.",
    visual: <OwnerCard />,
  },
  {
    icon: Users,
    title: "Your team signs in",
    time: "Every day",
    text: "Invite people with a role. Every PC and phone in the shop reaches the same IntraForge on this computer.",
    visual: <TeamPicture />,
  },
];

const STEP_MS = 5000;

/** "From download to running": the four steps of an installation, using screenshots of the real Setup window. */
export function SetupWalkthrough() {
  const [active, setActive] = useState(0);
  const [hold, setHold] = useState(false);
  const [visible, setVisible] = useState(false);
  const reduced = usePrefersReducedMotion();
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const io = new IntersectionObserver(([e]) => setVisible(e.isIntersecting), { threshold: 0.3 });
    io.observe(el);
    return () => io.disconnect();
  }, []);

  const auto = visible && !hold && !reduced;
  useEffect(() => {
    if (!auto) return;
    const id = window.setTimeout(() => setActive((i) => (i + 1) % STEPS.length), STEP_MS);
    return () => window.clearTimeout(id);
  }, [auto, active]);

  return (
    <div ref={ref} onMouseEnter={() => setHold(true)} onMouseLeave={() => setHold(false)} className="grid items-center gap-10 lg:grid-cols-[0.9fr_1.1fr]">
      <ol className="relative flex flex-col gap-2">
        <span aria-hidden="true" className="absolute top-6 bottom-6 left-[27px] w-px bg-slate-200" />
        {STEPS.map((step, i) => {
          const on = i === active;
          return (
            <li key={step.title}>
              <button
                type="button"
                onClick={() => setActive(i)}
                aria-current={on ? "step" : undefined}
                className={`relative flex w-full gap-4 rounded-2xl p-3 text-left transition-all duration-300 ${on ? "bg-white shadow-[0_0_0_1px_rgba(15,23,42,.06),0_12px_30px_-12px_rgba(30,58,138,.25)]" : "hover:bg-white/60"}`}
              >
                <span className={`relative z-10 grid h-8 w-8 shrink-0 place-items-center rounded-full text-sm font-semibold transition-colors duration-300 ${on ? "bg-brand-600 text-white" : i < active ? "bg-green-50 text-green-700" : "bg-white text-slate-500 ring-1 ring-slate-200"}`}>
                  {i + 1}
                </span>
                <span className="min-w-0 flex-1">
                  <span className="flex items-center gap-2">
                    <step.icon aria-hidden="true" className={`h-4 w-4 ${on ? "text-brand-600" : "text-slate-400"}`} />
                    <span className="font-semibold text-slate-900">{step.title}</span>
                    <span className="ml-auto text-xs text-slate-500">{step.time}</span>
                  </span>
                  <span className={`grid transition-all duration-500 ${on ? "mt-1.5 grid-rows-[1fr] opacity-100" : "grid-rows-[0fr] opacity-0"}`}>
                    <span className="overflow-hidden text-sm leading-relaxed text-slate-600">{step.text}</span>
                  </span>
                  {on && auto && (
                    <span className="mt-3 block h-0.5 overflow-hidden rounded-full bg-slate-100">
                      <span key={active} className={`block h-full bg-brand-600 ${s.fill}`} style={{ animationDuration: `${STEP_MS}ms`, animationTimingFunction: "linear" }} />
                    </span>
                  )}
                </span>
              </button>
            </li>
          );
        })}
      </ol>
      <div className="relative">
        <div aria-hidden="true" className="absolute -inset-6 -z-10 rounded-[2rem] bg-gradient-to-br from-brand-100/70 via-white to-teal-50" />
        <div key={active} className={s.shot}>
          {STEPS[active].visual}
        </div>
        <p className="mt-4 flex items-center justify-center gap-1.5 text-xs text-slate-500">
          <KeyRound aria-hidden="true" className="h-3.5 w-3.5" />
          {active < 2 ? "Real screens from IntraForge Setup" : "Illustration with sample names"}
        </p>
      </div>
    </div>
  );
}
