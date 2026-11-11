"use client";

import { useEffect, useRef, useState } from "react";
import { Building2, LayoutDashboard, LayoutGrid, Lock, Pause, Play } from "lucide-react";
import { SCENES, SCENE_MS, type CursorPoint } from "./DemoScenes";
import { usePrefersReducedMotion } from "@/lib/use-reduced-motion";
import s from "./home.module.css";

const STAGE_W = 640;
const STAGE_H = 420;
// The real sidebar (components/AppShell.tsx): files and people live inside an organization; apps open from Apps.
const NAV = [
  { icon: LayoutDashboard, label: "Dashboard" },
  { icon: LayoutGrid, label: "Apps" },
  { icon: Building2, label: "Organizations" },
];

function cursorAt(points: CursorPoint[], t: number) {
  let current = points[0];
  for (const p of points) if (p.at <= t) current = p;
  const click = points.some((p) => p.click && t >= p.at && t < p.at + 260);
  return { x: current.x, y: current.y, click };
}

/**
 * A running IntraForge, played as a short loop on the home page: the dashboard filling in, a file being uploaded, an app
 * installed in one click and a person invited with a role. Sample data only; nothing is fetched. It pauses while the
 * pointer is over it, while it is off screen or the tab is hidden, and with reduced motion it shows each scene's finished
 * state and changes scene only when asked.
 */
export function ProductDemo() {
  const reduced = usePrefersReducedMotion();
  const [scene, setScene] = useState(0);
  const [t, setT] = useState(0);
  const [hovered, setHovered] = useState(false);
  const [stopped, setStopped] = useState(false);
  const [visible, setVisible] = useState(true);
  const [scale, setScale] = useState(1);
  const frameRef = useRef<HTMLDivElement>(null);
  const clock = useRef(0);

  const playing = !reduced && !hovered && !stopped && visible;

  // Fit the fixed stage into whatever width the page gives it.
  useEffect(() => {
    const el = frameRef.current;
    if (!el) return;
    const fit = () => setScale(el.clientWidth / STAGE_W);
    fit();
    const ro = new ResizeObserver(fit);
    ro.observe(el);
    const io = new IntersectionObserver(([entry]) => setVisible(entry.isIntersecting && !document.hidden), { threshold: 0.15 });
    io.observe(el);
    const onVisibility = () => setVisible(!document.hidden);
    document.addEventListener("visibilitychange", onVisibility);
    return () => {
      ro.disconnect();
      io.disconnect();
      document.removeEventListener("visibilitychange", onVisibility);
    };
  }, []);

  // The clock: time into the current scene, advancing to the next one at the end.
  useEffect(() => {
    if (!playing) return;
    let last = performance.now();
    let raf = 0;
    const tick = (now: number) => {
      clock.current += Math.min(100, now - last);
      last = now;
      if (clock.current >= SCENE_MS) {
        clock.current = 0;
        setScene((i) => (i + 1) % SCENES.length);
      }
      setT(clock.current);
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [playing]);

  const current = SCENES[scene];
  const shownT = reduced ? SCENE_MS : t;
  const cursor = cursorAt(current.cursor, shownT);
  const go = (i: number) => {
    clock.current = 0;
    setScene(i);
    setT(0);
  };

  return (
    <div role="region" aria-roledescription="demo" aria-label="IntraForge demo with sample data" className="w-full">
      <div
        ref={frameRef}
        onMouseEnter={() => setHovered(true)}
        onMouseLeave={() => setHovered(false)}
        className={`${s.window} relative w-full overflow-hidden rounded-2xl bg-white shadow-[0_0_0_1px_rgba(15,23,42,.08),0_30px_70px_-20px_rgba(15,23,42,.45),0_10px_24px_-12px_rgba(37,99,235,.35)] ${playing || reduced ? "" : s.paused}`}
        style={{ height: STAGE_H * scale }}
      >
        <div aria-hidden="true" className="absolute top-0 left-0 origin-top-left select-none" style={{ width: STAGE_W, height: STAGE_H, transform: `scale(${scale})` }}>
          {/* Browser bar: this PC's own address and the real page each scene shows. */}
          <div className="absolute inset-x-0 top-0 flex h-9 items-center gap-2 border-b border-slate-200 bg-slate-50 px-3">
            <span className="h-2.5 w-2.5 rounded-full bg-[#ff5f57]" />
            <span className="h-2.5 w-2.5 rounded-full bg-[#febc2e]" />
            <span className="h-2.5 w-2.5 rounded-full bg-[#28c840]" />
            <div className="mx-auto flex h-[22px] w-64 items-center justify-center gap-1.5 rounded-md bg-white text-[10px] text-slate-500 shadow-[inset_0_0_0_1px_rgba(15,23,42,.08)]">
              <Lock className="h-2.5 w-2.5 text-green-600" />
              https://shop-pc:8443/{current.path}
            </div>
          </div>
          {/* The app's navy rail */}
          <div className="absolute top-9 bottom-0 left-0 w-[128px] bg-navy px-2.5 pt-3">
            <div className="mb-4 flex items-center gap-1.5 px-1">
              {/* eslint-disable-next-line @next/next/no-img-element -- fixed-size static brand asset */}
              <img src="/brand/icon-48.png" alt="" width={18} height={18} />
              <span className="text-[11px] font-semibold text-white">IntraForge</span>
            </div>
            {NAV.map((n, i) => (
              <div
                key={n.label}
                className={`mb-1 flex h-[22px] items-center gap-1.5 rounded-md px-2 text-[10.5px] transition-colors duration-300 ${i === current.nav ? "bg-brand-600 text-white" : "text-slate-300"}`}
              >
                <n.icon className="h-3 w-3" />
                {n.label}
              </div>
            ))}
            <div className="absolute inset-x-2.5 bottom-3 rounded-md bg-white/5 px-2 py-1.5 text-[9px] text-slate-400">
              <span className="block font-medium text-white">Selam</span>
              Owner
            </div>
          </div>
          <div className="absolute top-9 right-0 bottom-0 left-[128px] bg-slate-50" />
          <div key={current.key} className="absolute inset-0">
            <current.View t={shownT} />
          </div>
          {!reduced && (
            <svg className={`${s.cursor} ${cursor.click ? s.press : ""}`} style={{ left: cursor.x - 3, top: cursor.y - 2 }} width="18" height="22" viewBox="0 0 18 22">
              <path d="M1.5 1.5v16.2l4.3-4.1 2.8 6.6 3-1.3-2.8-6.4h6z" fill="#fff" stroke="#0f172a" strokeWidth="1.4" strokeLinejoin="round" />
            </svg>
          )}
        </div>
      </div>

      {/* Scene stepper: progress, captions, and a way to stop the motion */}
      <div className="mt-4 grid grid-cols-4 gap-2">
        {SCENES.map((sc, i) => {
          const fill = i < scene ? 1 : i === scene ? shownT / SCENE_MS : 0;
          return (
            <button
              key={sc.key}
              type="button"
              onClick={() => go(i)}
              aria-pressed={i === scene}
              className={`group flex flex-col justify-start self-start rounded-lg px-1 pt-2 pb-1 text-left transition-opacity duration-300 ${i === scene ? "" : "opacity-70 hover:opacity-100"}`}
            >
              <span className="block h-1 overflow-hidden rounded-full bg-slate-200">
                <span className="block h-full rounded-full bg-brand-600" style={{ width: `${(reduced && i === scene ? 1 : fill) * 100}%` }} />
              </span>
              <span className={`mt-2 block text-xs font-semibold sm:text-sm ${i === scene ? "text-slate-900" : "text-slate-500"}`}>{sc.title}</span>
            </button>
          );
        })}
      </div>
      <div className="mt-1 flex items-start justify-between gap-3">
        <p className="text-sm text-slate-600" aria-live="polite">
          {current.caption}
        </p>
        {!reduced && (
          <button
            type="button"
            onClick={() => setStopped((v) => !v)}
            className="inline-flex shrink-0 items-center gap-1.5 rounded-md px-2 py-1 text-xs font-medium text-slate-500 hover:bg-slate-100 hover:text-slate-900"
          >
            {stopped ? <Play className="h-3.5 w-3.5" /> : <Pause className="h-3.5 w-3.5" />}
            {stopped ? "Play" : "Pause"}
          </button>
        )}
      </div>
    </div>
  );
}
