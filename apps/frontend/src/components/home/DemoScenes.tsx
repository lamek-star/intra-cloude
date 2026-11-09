/* The four scenes of the home page's product demo (ProductDemo.tsx). Drawn on a fixed 640 x 420 stage that the demo
   scales to fit; `t` is the time into the scene in milliseconds, so the whole demo pauses and replays exactly. Every
   name and number is sample data. */
import type { CSSProperties, ReactNode } from "react";
import {
  Check,
  File,
  Folder,
  Globe,
  History,
  Package,
  Pill,
  ScrollText,
  Table2,
  Trash2,
  Upload,
  UserPlus,
  Wallet,
  Wrench,
  type LucideIcon,
} from "lucide-react";
import s from "./home.module.css";

export type CursorPoint = { at: number; x: number; y: number; click?: boolean };
export type Scene = { key: string; nav: number; title: string; caption: string; cursor: CursorPoint[]; View: (p: { t: number }) => ReactNode };

export const SCENE_MS = 5600;

function Box({ x, y, w, h, className = "", style, children }: { x: number; y: number; w?: number; h?: number; className?: string; style?: CSSProperties; children?: ReactNode }) {
  return (
    <div className={`absolute ${className}`} style={{ left: x, top: y, width: w, height: h, ...style }}>
      {children}
    </div>
  );
}

const panel = "rounded-lg border border-slate-200 bg-white shadow-[0_1px_2px_rgba(15,23,42,.04)]";
const ease = (p: number) => 1 - Math.pow(1 - Math.min(1, Math.max(0, p)), 3);
const countUp = (t: number, from: number, dur: number, target: number) => Math.round(target * ease((t - from) / dur));
const progress = (t: number, from: number, dur: number) => Math.min(1, Math.max(0, (t - from) / dur));

function Heading({ title, sub }: { title: string; sub: string }) {
  return (
    <Box x={146} y={50} className={s.sceneIn}>
      <p className="text-[15px] font-semibold tracking-tight text-slate-900">{title}</p>
      <p className="mt-0.5 text-[10.5px] text-slate-500">{sub}</p>
    </Box>
  );
}

function Row({ y, icon: Icon, tone, name, meta, className = "", style }: { y: number; icon: LucideIcon; tone: string; name: ReactNode; meta: ReactNode; className?: string; style?: CSSProperties }) {
  return (
    <Box x={146} y={y} w={476} h={28} className={`flex items-center gap-2 border-b border-slate-100 px-2 text-[11px] text-slate-800 ${className}`} style={{ transition: "top 500ms cubic-bezier(.16,1,.3,1)", ...style }}>
      <Icon className={`h-3.5 w-3.5 ${tone}`} />
      <span className="flex-1">{name}</span>
      <span className="text-[10px] text-slate-500">{meta}</span>
    </Box>
  );
}

// ---- 1. Overview -----------------------------------------------------------------------------------------------------
const HEALTH = ["API", "Database", "Tenant data", "Cache", "Files"];
const ACTIVITY: [number, string, string][] = [
  [1700, "Lula sold 2 × Oil filter", "10:42"],
  [2200, "Backup finished, restore tested", "19:03"],
  [2700, "Daniel received 40 parts", "11:05"],
];

function Overview({ t }: { t: number }) {
  const stats: [string, number, string][] = [
    ["Organizations", 1, ""],
    ["Files", 1284, ""],
    ["Apps", 3, ""],
    ["Health", 5, "/5"],
  ];
  return (
    <>
      <Heading title="Good morning, Selam" sub="Your shop at a glance · everything runs on this PC" />
      {stats.map(([label, n, suffix], i) => (
        <Box key={label} x={146 + i * 121} y={92} w={112} h={62} className={`${panel} ${s.pop} p-2.5`} style={{ animationDelay: `${120 + i * 90}ms` }}>
          <p className="text-[9.5px] font-medium text-slate-500">{label}</p>
          <p className="mt-1 text-[19px] font-semibold tabular-nums tracking-tight text-slate-900">
            {countUp(t, 300, 1300, n).toLocaleString("en-US")}
            {suffix}
          </p>
          <div className="absolute inset-x-0 bottom-0 h-[3px] rounded-b-lg" style={{ background: ["#3b82f6", "#f59e0b", "#14b8a6", "#22c55e"][i], transform: `scaleX(${ease((t - 300) / 1300)})`, transformOrigin: "left" }} />
        </Box>
      ))}
      <Box x={146} y={168} w={230} h={116} className={`${panel} p-2.5`}>
        <p className="text-[10.5px] font-semibold text-slate-900">System health</p>
        <div className="mt-2 flex flex-wrap gap-1.5">
          {HEALTH.map((h, i) => {
            const on = t > 900 + i * 220;
            return (
              <span key={h} className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[9.5px] font-semibold ${on ? `bg-green-50 text-green-700 ${s.healthOn}` : "bg-slate-100 text-slate-400"}`}>
                <span className={`h-1.5 w-1.5 rounded-full ${on ? "bg-green-500" : "bg-slate-300"}`} />
                {h}
              </span>
            );
          })}
        </div>
        <p className="mt-3 text-[9.5px] text-slate-500">{t > 2100 ? "All 5 checks passing" : "Checking..."}</p>
      </Box>
      <Box x={386} y={168} w={236} h={116} className={`${panel} p-2.5`}>
        <p className="text-[10.5px] font-semibold text-slate-900">Recent activity</p>
        <div className="mt-1.5">
          {ACTIVITY.filter(([at]) => t > at).map(([, text, time]) => (
            <div key={text} className={`flex items-center gap-1.5 border-b border-slate-100 py-1.5 text-[10px] text-slate-700 ${s.pop}`}>
              <span className="font-mono text-[9px] text-slate-400">{time}</span>
              <span className="flex-1 truncate">{text}</span>
              <Check className="h-3 w-3 text-green-600" />
            </div>
          ))}
        </div>
      </Box>
      <Box x={146} y={296} w={476} h={50} className={`${panel} flex items-center gap-3 px-3`}>
        <div className="grid h-7 w-7 place-items-center rounded-md bg-brand-50 text-brand-700"><History className="h-3.5 w-3.5" /></div>
        <div className="flex-1">
          <p className="text-[10.5px] font-semibold text-slate-900">Daily backup at 19:00</p>
          <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-slate-100">
            <div className="h-full rounded-full bg-gradient-to-r from-brand-600 to-teal-500" style={{ width: `${18 + 62 * ease((t - 600) / 2400)}%`, transition: "width 120ms linear" }} />
          </div>
        </div>
        <span className="text-[9.5px] text-slate-500">Storage {Math.round(18 + 62 * ease((t - 600) / 2400))}% used</span>
      </Box>
      <Box x={146} y={358} w={476} h={44} className={`${panel} flex items-center gap-2 px-3 text-[10px] text-slate-600`}>
        <Globe className="h-3.5 w-3.5 text-slate-400" />
        Internet access <b className="text-slate-900">off</b> · reachable from this shop&apos;s network only
        <span className="relative ml-auto h-4 w-7 rounded-full bg-slate-300 after:absolute after:top-0.5 after:left-0.5 after:h-3 after:w-3 after:rounded-full after:bg-white" />
      </Box>
    </>
  );
}

// ---- 2. Storage ------------------------------------------------------------------------------------------------------
function Storage({ t }: { t: number }) {
  const uploaded = t > 3100;
  const shift = uploaded ? 28 : 0;
  const upload = progress(t, 1500, 1500);
  return (
    <>
      <Heading title="Shop documents" sub="Bucket › Invoices · versioning on" />
      <Box x={548} y={50} w={74} h={26} className={`flex items-center justify-center gap-1 rounded-md bg-brand-600 text-[10.5px] font-semibold text-white ${t > 1150 && t < 1500 ? s.ring : ""}`}>
        <Upload className="h-3 w-3" />
        Upload
      </Box>
      <Box x={146} y={92} w={476} h={20} className="flex items-center px-2 text-[9px] font-semibold tracking-wider text-slate-400 uppercase">
        <span className="flex-1">Name</span>
        <span>Size / version</span>
      </Box>
      {uploaded && <Row y={112} icon={File} tone="text-rose-500" name={<>Invoice-0412.pdf <span className="ml-1 rounded-full bg-green-50 px-1.5 text-[9px] font-semibold text-green-700">New</span></>} meta="320 KB" className={`bg-green-50/40 ${s.pop}`} />}
      <Row y={112 + shift} icon={Folder} tone="text-brand-600" name="2026 receipts" meta="48 files" />
      <Row
        y={140 + shift}
        icon={Table2}
        tone="text-teal-600"
        name="Price list.xlsx"
        meta={<span key={t > 3700 ? "v3" : "v2"} className={`rounded-full bg-brand-50 px-1.5 py-0.5 text-[9px] font-semibold text-brand-700 ${t > 3700 ? s.ring : ""}`}>{t > 3700 ? "v3" : "v2"}</span>}
      />
      <Row y={168 + shift} icon={File} tone="text-slate-400" name="Supplier contract.pdf" meta="1.2 MB" />
      <Row y={196 + shift} icon={File} tone="text-slate-400" name="Delivery note 0398.pdf" meta="214 KB" />
      {t > 1400 && t < 3150 && (
        <Box x={300} y={262} w={230} h={70} className={`${panel} ${s.dropIn} p-3 shadow-xl`}>
          <div className="flex items-center gap-2 text-[10.5px] font-semibold text-slate-900">
            <File className="h-4 w-4 text-rose-500" /> Invoice-0412.pdf
            <span className="ml-auto text-[9.5px] font-normal text-slate-500">{Math.round(upload * 320)} / 320 KB</span>
          </div>
          <div className="mt-2.5 h-1.5 overflow-hidden rounded-full bg-slate-100">
            <div className="h-full rounded-full bg-brand-600" style={{ width: `${upload * 100}%`, transition: "width 100ms linear" }} />
          </div>
          <p className="mt-1.5 text-[9px] text-slate-500">{upload < 1 ? "Uploading..." : "Checked and stored"}</p>
        </Box>
      )}
      {t > 3900 && (
        <Box x={440} y={198} w={182} h={78} className={`${panel} ${s.pop} p-2 shadow-lg`}>
          <p className="flex items-center gap-1 text-[10px] font-semibold text-slate-900"><History className="h-3 w-3" />Earlier versions kept</p>
          {[["v3", "Today 10:42"], ["v2", "Yesterday"], ["v1", "3 Nov"]].map(([v, d], i) => (
            <p key={v} className="mt-0.5 flex justify-between text-[9.5px] text-slate-600">
              <b className={i === 0 ? "text-brand-700" : "font-normal"}>{v}</b>
              {d}
            </p>
          ))}
        </Box>
      )}
      <Box x={146} y={372} className="flex items-center gap-1.5 rounded-full bg-slate-100 px-2.5 py-1 text-[9.5px] font-semibold text-slate-600">
        <Trash2 className="h-3 w-3" />
        Deleted files wait 30 days in Trash
      </Box>
    </>
  );
}

// ---- 3. Apps ---------------------------------------------------------------------------------------------------------
function AppCard({ x, icon: Icon, tone, name, text, children, delay }: { x: number; icon: LucideIcon; tone: string; name: string; text: string; children: ReactNode; delay: number }) {
  return (
    <Box x={x} y={92} w={152} h={150} className={`${panel} ${s.pop} p-3`} style={{ animationDelay: `${delay}ms` }}>
      <span className={`grid h-9 w-9 place-items-center rounded-lg ${tone}`}><Icon className="h-[18px] w-[18px]" /></span>
      <p className="mt-2.5 text-[12px] font-semibold text-slate-900">{name}</p>
      <p className="mt-0.5 text-[9.5px] leading-snug text-slate-500">{text}</p>
      <div className="absolute inset-x-3 bottom-3">{children}</div>
    </Box>
  );
}
const Installed = () => (
  <span className="inline-flex items-center gap-1 rounded-full bg-green-50 px-2 py-0.5 text-[9.5px] font-semibold text-green-700"><Check className="h-3 w-3" strokeWidth={3} />Installed</span>
);

function Apps({ t }: { t: number }) {
  const installing = t > 1250 && t < 3000;
  return (
    <>
      <Heading title="Apps" sub="Ready-made business apps · one click, no internet" />
      <AppCard x={146} icon={Wrench} tone="bg-brand-50 text-brand-700" name="Spare Parts" text="Stock, sales, barcode labels" delay={60}><Installed /></AppCard>
      <AppCard x={308} icon={Wallet} tone="bg-violet-50 text-violet-700" name="IntraForge Pay" text="Wallets and QR payments" delay={140}><Installed /></AppCard>
      <AppCard x={470} icon={Pill} tone="bg-teal-50 text-teal-700" name="Pharmacy" text="Medicines, shelves, prices" delay={220}>
        {t <= 1250 && (
          <span className={`flex h-[26px] items-center justify-center rounded-md bg-brand-600 text-[10.5px] font-semibold text-white ${t > 1100 ? s.ring : ""}`}>Install</span>
        )}
        {installing && (
          <div>
            <p className="mb-1 text-[9px] font-semibold text-brand-700">Installing... {Math.round(progress(t, 1250, 1750) * 100)}%</p>
            <div className="h-1.5 overflow-hidden rounded-full bg-slate-100">
              <div className="h-full rounded-full bg-brand-600" style={{ width: `${progress(t, 1250, 1750) * 100}%`, transition: "width 100ms linear" }} />
            </div>
          </div>
        )}
        {t >= 3000 && <span className={s.pop}><Installed /></span>}
      </AppCard>
      <Box x={146} y={256} w={476} h={20} className="px-1 text-[9px] font-semibold tracking-wider text-slate-400 uppercase">Your own apps</Box>
      <Row y={276} icon={Globe} tone="text-brand-600" name="Shop website · shop.local" meta={<span className="font-semibold text-green-700">Running</span>} />
      <Row y={304} icon={Package} tone="text-amber-600" name="Price checker (uploaded zip)" meta={<span className="font-semibold text-green-700">Running</span>} />
      {t > 3100 && (
        <Box x={402} y={364} w={220} h={36} className={`flex items-center gap-2 rounded-lg bg-slate-900 px-3 text-[10.5px] font-medium text-white shadow-xl ${s.pop}`}>
          <span className="grid h-4 w-4 place-items-center rounded-full bg-green-500"><Check className="h-2.5 w-2.5" strokeWidth={3.5} /></span>
          Pharmacy is ready to use
        </Box>
      )}
    </>
  );
}

// ---- 4. People -------------------------------------------------------------------------------------------------------
const EMAIL = "lula@shop.local";
const ROLE: Record<string, string> = { Owner: "bg-brand-50 text-brand-700", Manager: "bg-teal-50 text-teal-700", Cashier: "bg-slate-100 text-slate-600" };

function Member({ y, initials, color, name, email, role, className = "" }: { y: number; initials: string; color: string; name: string; email: string; role: string; className?: string }) {
  return (
    <Box x={146} y={y} w={476} h={30} className={`flex items-center gap-2 border-b border-slate-100 px-2 text-[11px] ${className}`}>
      <span className={`grid h-5 w-5 place-items-center rounded-full text-[8px] font-bold text-white ${color}`}>{initials}</span>
      <span className="w-20 font-medium text-slate-900">{name}</span>
      <span className="flex-1 text-[10px] text-slate-500">{email}</span>
      <span className={`rounded-full px-2 py-0.5 text-[9.5px] font-semibold ${ROLE[role]}`}>{role}</span>
    </Box>
  );
}

function People({ t }: { t: number }) {
  const typed = EMAIL.slice(0, Math.round(EMAIL.length * progress(t, 900, 1200)));
  const audit: [number, string, ReactNode][] = [
    [3500, "Selam invited Lula as Cashier", <Check key="c" className="h-3 w-3 text-green-600" />],
    [4100, "Lula tried to change a price", <span key="d" className="rounded-full bg-red-50 px-1.5 text-[9px] font-semibold text-red-700">Denied</span>],
  ];
  return (
    <>
      <Heading title="People and roles" sub="Each person signs in with their own account · roles, not shared passwords" />
      <Box x={146} y={90} w={476} h={58} className={`${panel} flex items-center gap-2 px-3`}>
        <UserPlus className="h-4 w-4 text-slate-400" />
        <div className={`flex h-[26px] flex-1 items-center rounded-md border px-2 font-mono text-[10.5px] text-slate-900 ${t > 800 ? "border-brand-400" : "border-slate-200"}`}>
          {typed || <span className="font-sans text-slate-400">Email address</span>}
          {t > 800 && t < 2300 && <span className={`ml-px h-3 w-px bg-slate-900 ${s.blink}`} />}
        </div>
        <span className={`flex h-[26px] w-[84px] items-center justify-center rounded-md border text-[10.5px] font-semibold ${t > 2400 ? "border-slate-200 bg-slate-50 text-slate-700" : "border-slate-200 text-slate-400"}`}>
          {t > 2400 ? "Cashier" : "Role"}
        </span>
        <span className={`flex h-[26px] w-[76px] items-center justify-center rounded-md bg-brand-600 text-[10.5px] font-semibold text-white ${t > 2850 && t < 3200 ? s.ring : ""}`}>Invite</span>
      </Box>
      <Member y={160} initials="SA" color="bg-brand-600" name="Selam" email="selam@shop.local" role="Owner" />
      <Member y={190} initials="DM" color="bg-teal-600" name="Daniel" email="daniel@shop.local" role="Manager" />
      {t > 3100 && <Member y={220} initials="LH" color="bg-violet-600" name="Lula" email={EMAIL} role="Cashier" className={`bg-green-50/40 ${s.pop}`} />}
      <Box x={146} y={268} w={476} h={118} className={`${panel} p-2.5`}>
        <p className="flex items-center gap-1.5 text-[10.5px] font-semibold text-slate-900"><ScrollText className="h-3.5 w-3.5" />Audit log · every action is recorded</p>
        <div className="mt-1.5">
          <div className="flex items-center gap-2 border-b border-slate-100 py-1.5 text-[10px] text-slate-700">
            <span className="font-mono text-[9px] text-slate-400">09:58</span>Daniel signed in with a passkey<Check className="ml-auto h-3 w-3 text-green-600" />
          </div>
          {audit.filter(([at]) => t > at).map(([, text, mark]) => (
            <div key={text} className={`flex items-center gap-2 border-b border-slate-100 py-1.5 text-[10px] text-slate-700 ${s.pop}`}>
              <span className="font-mono text-[9px] text-slate-400">{text.startsWith("Selam") ? "10:12" : "10:15"}</span>
              {text}
              <span className="ml-auto">{mark}</span>
            </div>
          ))}
        </div>
      </Box>
    </>
  );
}

export const SCENES: Scene[] = [
  {
    key: "overview",
    nav: 0,
    title: "Your shop at a glance",
    caption: "Health, activity, backups and storage, live on one page.",
    View: Overview,
    cursor: [
      { at: 0, x: 560, y: 330 },
      { at: 1800, x: 196, y: 128 },
      { at: 3400, x: 470, y: 240 },
      { at: 4300, x: 54, y: 127 },
      { at: 5100, x: 54, y: 127, click: true },
    ],
  },
  {
    key: "storage",
    nav: 1,
    title: "Store every file",
    caption: "Upload, keep every version, and get deleted files back from Trash.",
    View: Storage,
    cursor: [
      { at: 0, x: 54, y: 127 },
      { at: 450, x: 585, y: 63 },
      { at: 1150, x: 585, y: 63, click: true },
      { at: 2300, x: 430, y: 300 },
      { at: 3500, x: 596, y: 182 },
      { at: 4500, x: 54, y: 153 },
      { at: 5150, x: 54, y: 153, click: true },
    ],
  },
  {
    key: "apps",
    nav: 2,
    title: "Install business apps",
    caption: "Spare Parts, Pharmacy and Pay install in one click, with no internet.",
    View: Apps,
    cursor: [
      { at: 0, x: 54, y: 153 },
      { at: 350, x: 546, y: 222 },
      { at: 1100, x: 546, y: 222, click: true },
      { at: 3300, x: 330, y: 330 },
      { at: 4500, x: 54, y: 179 },
      { at: 5150, x: 54, y: 179, click: true },
    ],
  },
  {
    key: "people",
    nav: 3,
    title: "Invite your team",
    caption: "Give each person a role. Everything they do is in the audit log.",
    View: People,
    cursor: [
      { at: 0, x: 54, y: 179 },
      { at: 450, x: 300, y: 120 },
      { at: 750, x: 300, y: 120, click: true },
      { at: 2200, x: 482, y: 120 },
      { at: 2400, x: 482, y: 120, click: true },
      { at: 2650, x: 582, y: 120 },
      { at: 2850, x: 582, y: 120, click: true },
      { at: 4500, x: 54, y: 101 },
      { at: 5150, x: 54, y: 101, click: true },
    ],
  },
];
