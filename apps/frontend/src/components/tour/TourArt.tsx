/* The welcome tour's five drawings (design: design-references/installer-mockups/tour.js). Decorative only: every fact
   they show is also said in the slide's text, so they are hidden from screen readers. */
import type { CSSProperties, ReactNode } from "react";
import {
  Calendar,
  Check,
  Database,
  File,
  Folder,
  Globe,
  History,
  KeyRound,
  Link2,
  Lock,
  Pill,
  ScrollText,
  Shield,
  ShieldCheck,
  Smartphone,
  Table2,
  Trash2,
  Upload,
  Users,
  Wrench,
  type LucideIcon,
} from "lucide-react";

const card = "absolute rounded-xl bg-white shadow-[0_0_0_1px_rgba(15,23,42,.06),0_14px_34px_rgba(30,58,138,.16)]";
const row = "flex items-center gap-2 border-t border-slate-200 py-2 text-xs text-slate-900";

type Tone = "blue" | "teal" | "green" | "amber" | "slate" | "red";
const tones: Record<Tone, string> = {
  blue: "bg-brand-50 text-brand-700",
  teal: "bg-teal-50 text-teal-700",
  green: "bg-green-50 text-green-700",
  amber: "bg-amber-50 text-amber-700",
  slate: "bg-slate-100 text-slate-600",
  red: "bg-red-50 text-red-700",
};

function Chip({ icon: Icon, tone, children, style }: { icon: LucideIcon; tone: Tone; children: ReactNode; style: CSSProperties }) {
  return (
    <div
      className="absolute flex items-center gap-2 whitespace-nowrap rounded-full bg-white py-1.5 pr-3 pl-1.5 text-[12.5px] font-semibold text-slate-900 shadow-[0_0_0_1px_rgba(15,23,42,.06),0_8px_20px_rgba(30,58,138,.14)]"
      style={style}
    >
      <span className={`grid h-[26px] w-[26px] place-items-center rounded-full ${tones[tone]}`}>
        <Icon className="h-3.5 w-3.5" />
      </span>
      {children}
    </div>
  );
}

function Pill_({ tone, children }: { tone: Tone; children: ReactNode }) {
  return <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-semibold ${tones[tone]}`}>{children}</span>;
}

export function WelcomeArt() {
  return (
    <>
      <svg className="absolute inset-0 h-full w-full" viewBox="0 0 410 520" fill="none" aria-hidden="true">
        <g stroke="#93c5fd" strokeWidth="1.5" strokeDasharray="4 5">
          <path d="M205 250 L88 132" />
          <path d="M205 250 L326 136" />
          <path d="M205 250 L90 384" />
          <path d="M205 250 L322 388" />
        </g>
      </svg>
      <div
        className={`${card} grid place-items-center`}
        style={{ left: 130, top: 176, width: 150, height: 150, borderRadius: 34, boxShadow: "0 0 0 12px rgba(255,255,255,.55), 0 22px 50px rgba(30,58,138,.22)" }}
      >
        {/* eslint-disable-next-line @next/next/no-img-element -- fixed-size static brand asset */}
        <img src="/brand/icon-128.png" alt="" width={104} height={104} />
      </div>
      <Chip icon={Folder} tone="blue" style={{ left: 30, top: 112 }}>Store</Chip>
      <Chip icon={Database} tone="teal" style={{ left: 268, top: 116 }}>Build</Chip>
      <Chip icon={Link2} tone="green" style={{ left: 26, top: 366 }}>Connect</Chip>
      <Chip icon={Shield} tone="amber" style={{ left: 262, top: 370 }}>Protect</Chip>
      <p className="absolute inset-x-0 bottom-8 text-center text-xs font-semibold tracking-[.08em] text-navy-800/70">
        BUILD · STORE · CONNECT · PRIVATELY
      </p>
    </>
  );
}

export function StoreArt() {
  return (
    <>
      <div className={card} style={{ left: 34, top: 70, width: 300, padding: "14px 16px 6px" }}>
        <div className="flex items-center gap-1.5 text-xs text-slate-500">
          <Folder className="h-3.5 w-3.5" />
          <b className="text-slate-900">Shop documents</b>› Invoices
        </div>
        <div className={`${row} mt-2.5`}><Folder className="h-4 w-4 text-brand-600" />2026 receipts<span className="ml-auto text-[11px] text-slate-500">48 files</span></div>
        <div className={row}><Table2 className="h-4 w-4 text-teal-600" />Price list.xlsx<span className="ml-auto"><Pill_ tone="blue">v3</Pill_></span></div>
        <div className={row}><File className="h-4 w-4 text-slate-500" />Supplier contract.pdf<span className="ml-auto text-[11px] text-slate-500">1.2 MB</span></div>
      </div>
      <div className={card} style={{ left: 200, top: 236, width: 176, padding: "12px 14px" }}>
        <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-900"><History className="h-3.5 w-3.5" />Versions</div>
        <div className={`${row} mt-1.5`}><b className="text-brand-700">v3</b><span className="ml-auto text-[11px] text-slate-500">Today 10:42</span></div>
        <div className={row}>v2<span className="ml-auto text-[11px] text-slate-500">Yesterday</span></div>
        <div className={row}>v1<span className="ml-auto text-[11px] text-slate-500">3 Nov</span></div>
      </div>
      <Chip icon={Trash2} tone="slate" style={{ left: 40, top: 300 }}>Trash · 30 days</Chip>
      <div
        className="absolute flex items-center justify-center gap-2.5 rounded-xl border-2 border-dashed border-brand-400 bg-white/70 text-[13px] font-semibold text-brand-700"
        style={{ left: 34, top: 410, width: 342, height: 76 }}
      >
        <Upload className="h-[18px] w-[18px]" />
        Drop files to upload
      </div>
    </>
  );
}

const PARTS = [
  ["04465-0K290", "Brake pads", "12", "48.00"],
  ["90915-YZZE1", "Oil filter", "40", "6.50"],
  ["17801-0L040", "Air filter", "3", "14.90"],
  ["88568-0K010", "Cabin filter", "0", "9.80"],
];

function AppTile({ icon: Icon, tone, name, text, state, style }: { icon: LucideIcon; tone: Tone; name: string; text: string; state: ReactNode; style: CSSProperties }) {
  return (
    <div className={card} style={{ width: 164, padding: 14, ...style }}>
      <span className={`grid h-[38px] w-[38px] place-items-center rounded-[10px] ${tones[tone]}`}><Icon className="h-5 w-5" /></span>
      <b className="mt-2.5 block text-[13.5px] text-slate-900">{name}</b>
      <span className="text-[11.5px] text-slate-500">{text}</span>
      <div className="mt-2.5">{state}</div>
    </div>
  );
}

export function BuildArt() {
  return (
    <>
      <div className={card} style={{ left: 30, top: 64, width: 350, padding: "12px 14px 4px" }}>
        <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-900">
          <Table2 className="h-3.5 w-3.5" />Parts<span className="ml-auto"><Pill_ tone="slate">1,284 rows</Pill_></span>
        </div>
        <div className="mt-2 flex py-2 text-[10px] font-semibold tracking-[.05em] text-slate-500 uppercase">
          <span className="w-24">Part no.</span><span className="flex-1">Name</span><span className="w-12 text-right">Stock</span><span className="w-16 text-right">Price</span>
        </div>
        {PARTS.map(([n, name, stock, price]) => (
          <div key={n} className={row}>
            <span className="w-24 font-mono text-[11px] text-slate-600">{n}</span>
            <span className="flex-1">{name}</span>
            <span className={`w-12 text-right font-mono text-[11px] ${stock === "0" ? "font-semibold text-red-700" : ""}`}>{stock}</span>
            <span className="w-16 text-right font-mono text-[11px]">{price}</span>
          </div>
        ))}
      </div>
      <AppTile icon={Wrench} tone="blue" name="Spare Parts" text="Stock, sales, labels" style={{ left: 30, top: 300 }}
        state={<Pill_ tone="green"><Check className="h-3 w-3" strokeWidth={3} />Installed</Pill_>} />
      <AppTile icon={Pill} tone="teal" name="Pharmacy" text="Medicines, prices" style={{ left: 216, top: 300 }} state={<Pill_ tone="blue">Install</Pill_>} />
      <Chip icon={Upload} tone="teal" style={{ left: 30, top: 458 }}>medicines.csv</Chip>
    </>
  );
}

export function ConnectArt() {
  return (
    <>
      <svg className="absolute inset-0 h-full w-full" viewBox="0 0 410 520" fill="none" aria-hidden="true">
        <g stroke="#93c5fd" strokeWidth="1.5">
          <path d="M150 230 L205 230" />
          <path d="M265 230 C 290 230, 290 120, 312 120" />
          <path d="M265 230 L312 230" />
          <path d="M265 230 C 290 230, 290 340, 312 340" />
        </g>
      </svg>
      <div className="absolute flex flex-col gap-2.5" style={{ left: 26, top: 150 }}>
        <Pill_ tone="slate">Development</Pill_>
        <Pill_ tone="amber">Staging</Pill_>
        <Pill_ tone="green"><Shield className="h-3 w-3" />Production</Pill_>
      </div>
      <div className={`${card} grid place-items-center rounded-[20px]`} style={{ left: 150, top: 184, width: 116, height: 96 }}>
        {/* eslint-disable-next-line @next/next/no-img-element -- fixed-size static brand asset */}
        <img src="/brand/icon-96.png" alt="" width={76} height={76} />
      </div>
      <Chip icon={Globe} tone="blue" style={{ left: 300, top: 102 }}>Website</Chip>
      <Chip icon={Smartphone} tone="teal" style={{ left: 300, top: 212 }}>Phone</Chip>
      <Chip icon={KeyRound} tone="slate" style={{ left: 300, top: 322 }}>Your app</Chip>
      <div className={`${card} flex items-center gap-3`} style={{ left: 30, top: 408, width: 350, padding: "12px 14px" }}>
        <span className="grid h-[34px] w-[34px] place-items-center rounded-[9px] bg-slate-100 text-slate-600"><Lock className="h-[17px] w-[17px]" /></span>
        <div>
          <b className="block text-[13px] text-slate-900">Internet access</b>
          <span className="text-[11.5px] text-slate-500">Off · local network only</span>
        </div>
        <span className="relative ml-auto h-5 w-[34px] rounded-full bg-slate-300 after:absolute after:top-[3px] after:left-[3px] after:h-3.5 after:w-3.5 after:rounded-full after:bg-white" />
      </div>
    </>
  );
}

const PEOPLE: [string, string, string, string, Tone][] = [
  ["SA", "bg-brand-600", "Selam", "Owner", "blue"],
  ["DM", "bg-teal-600", "Daniel", "Manager", "teal"],
  ["LH", "bg-violet-600", "Lula", "Cashier", "slate"],
];

export function ProtectArt() {
  return (
    <>
      <div className={card} style={{ left: 30, top: 60, width: 350, padding: "14px 16px 6px" }}>
        <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-900"><Users className="h-3.5 w-3.5" />People</div>
        {PEOPLE.map(([initials, color, name, role, tone]) => (
          <div key={name} className={row}>
            <span className={`grid h-7 w-7 place-items-center rounded-full text-[11px] font-bold text-white ${color}`}>{initials}</span>
            {name}
            <span className="ml-auto"><Pill_ tone={tone}>{role}</Pill_></span>
          </div>
        ))}
      </div>
      <div className={card} style={{ left: 30, top: 236, width: 350, padding: "14px 16px 6px" }}>
        <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-900"><ScrollText className="h-3.5 w-3.5" />Audit log</div>
        <div className={row}><span className="font-mono text-[11px] text-slate-500">10:42</span>Lula sold 2 × Oil filter<Check className="ml-auto h-3.5 w-3.5 text-slate-500" /></div>
        <div className={row}><span className="font-mono text-[11px] text-slate-500">11:05</span>Daniel received 40 parts<Check className="ml-auto h-3.5 w-3.5 text-slate-500" /></div>
        <div className={row}><span className="font-mono text-[11px] text-slate-500">11:20</span>Lula tried to change a price<span className="ml-auto"><Pill_ tone="red">Denied</Pill_></span></div>
      </div>
      <Chip icon={Calendar} tone="green" style={{ left: 44, top: 420 }}>Backup 19:00 · restore tested</Chip>
      <div className={`${card} grid place-items-center rounded-[22px] text-brand-600`} style={{ left: 296, top: 398, width: 78, height: 78 }}>
        <ShieldCheck className="h-10 w-10" strokeWidth={1.8} />
      </div>
    </>
  );
}
