// The five welcome-tour slides. tourHtml(n) returns the dialog for slide n (1-5).
const B = "../brand/generated/";
const SLIDES = [
  {
    eyebrow: "Welcome",
    title: "Welcome to IntraForge",
    body: "Your organization's private cloud. Files, databases and business apps for your whole team, running on your own computer, with or without the internet.",
    points: [["folder", "Store your files and documents"], ["database", "Build databases and business apps"], ["link", "Connect your other apps safely"]],
    next: "Take the tour",
    art: `
      <svg style="position:absolute;inset:0" width="410" height="520"><g stroke="#93c5fd" stroke-width="1.5" stroke-dasharray="4 5" fill="none">
        <path d="M205 250 L88 132"/><path d="M205 250 L326 136"/><path d="M205 250 L90 384"/><path d="M205 250 L322 388"/></g></svg>
      <div class="card" style="left:130px;top:176px;width:150px;height:150px;border-radius:34px;display:grid;place-items:center;box-shadow:0 0 0 12px rgba(255,255,255,.55),0 0 0 1px rgba(15,23,42,.06),0 22px 50px rgba(30,58,138,.22)">
        <img src="${B}intraforge-icon.png" width="104"></div>
      <div class="chip" style="left:30px;top:112px"><span class="d blue">${icon("folder", 14)}</span>Store</div>
      <div class="chip" style="left:268px;top:116px"><span class="d teal">${icon("database", 14)}</span>Build</div>
      <div class="chip" style="left:26px;top:366px"><span class="d green">${icon("link", 14)}</span>Connect</div>
      <div class="chip" style="left:262px;top:370px"><span class="d amber">${icon("shield", 14)}</span>Protect</div>
      <div style="position:absolute;left:0;right:0;bottom:30px;text-align:center;font-size:12px;font-weight:600;letter-spacing:.08em;color:#1e3a8a;opacity:.7">BUILD · STORE · CONNECT · PRIVATELY</div>`,
  },
  {
    eyebrow: "Store",
    title: "Files, like a cloud drive",
    body: "Create buckets and folders, upload anything, and share each one with exactly the people who need it.",
    points: [["history", "Every change keeps the earlier version"], ["trash", "Deleted files wait in Trash first"], ["users", "Share a folder, not a password"]],
    art: `
      <div class="card" style="left:34px;top:70px;width:300px;padding:14px 16px 6px">
        <div style="display:flex;align-items:center;gap:7px;font-size:12px;color:var(--text-3)">${icon("folder", 14)}<b style="color:var(--text)">Shop documents</b>› Invoices</div>
        <div class="row" style="margin-top:10px"><span style="color:var(--brand)">${icon("folder", 15)}</span>2026 receipts<span class="m">48 files</span></div>
        <div class="row"><span style="color:#0d9488">${icon("table", 15)}</span>Price list.xlsx<span class="m"><span class="pill blue">v3</span></span></div>
        <div class="row"><span style="color:var(--text-3)">${icon("file", 15)}</span>Supplier contract.pdf<span class="m">1.2 MB</span></div>
      </div>
      <div class="card" style="left:200px;top:236px;width:176px;padding:12px 14px">
        <div style="display:flex;align-items:center;gap:6px;font-size:12px;font-weight:600">${icon("history", 14)}Versions</div>
        <div class="row" style="margin-top:6px"><b style="color:var(--brand-700)">v3</b><span class="m">Today 10:42</span></div>
        <div class="row">v2<span class="m">Yesterday</span></div>
        <div class="row">v1<span class="m">3 Nov</span></div>
      </div>
      <div class="chip" style="left:40px;top:300px"><span class="d slate">${icon("trash", 14)}</span>Trash · 30 days</div>
      <div class="card" style="left:34px;top:410px;width:342px;height:76px;border:2px dashed #93c5fd;box-shadow:none;background:rgba(255,255,255,.7);display:flex;align-items:center;justify-content:center;gap:10px;font-size:13px;color:var(--brand-700);font-weight:600">${icon("upload", 18)}Drop files to upload</div>`,
  },
  {
    eyebrow: "Build",
    title: "Databases and business apps",
    body: "Design tables without code, import your spreadsheets, or install a ready-made app and start working today.",
    points: [["box", "Spare Parts and Pharmacy, ready to install"], ["upload", "Import CSV files in a few clicks"], ["layout", "Statistics and dashboards on your data"]],
    art: `
      <div class="card" style="left:30px;top:64px;width:350px;padding:12px 14px 4px">
        <div style="display:flex;align-items:center;gap:7px;font-size:12px;font-weight:600">${icon("table", 14)}Parts <span class="pill slate" style="margin-left:auto">1,284 rows</span></div>
        <div class="row th" style="margin-top:8px;border-top:none"><span style="width:96px">Part no.</span><span style="flex:1">Name</span><span style="width:46px;text-align:right">Stock</span><span style="width:60px;text-align:right">Price</span></div>
        ${[["04465-0K290", "Brake pads", "12", "48.00"], ["90915-YZZE1", "Oil filter", "40", "6.50"], ["17801-0L040", "Air filter", "3", "14.90"], ["88568-0K010", "Cabin filter", "0", "9.80"]]
          .map(([n, name, s, p]) => `<div class="row"><span class="mono" style="width:96px;font-size:11px;color:var(--text-2)">${n}</span><span style="flex:1">${name}</span><span class="mono" style="width:46px;text-align:right;font-size:11px;${s === "0" ? "color:#b91c1c;font-weight:600" : ""}">${s}</span><span class="mono" style="width:60px;text-align:right;font-size:11px">${p}</span></div>`).join("")}
      </div>
      <div class="card" style="left:30px;top:300px;width:164px;padding:14px">
        <span class="d" style="width:38px;height:38px;border-radius:10px;display:grid;place-items:center;background:var(--brand-50);color:var(--brand-700)">${icon("wrench", 20)}</span>
        <b style="display:block;margin-top:10px;font-size:13.5px">Spare Parts</b><span style="font-size:11.5px;color:var(--text-3)">Stock, sales, labels</span>
        <div style="margin-top:10px"><span class="pill green">${icon("check", 11, 3)}Installed</span></div></div>
      <div class="card" style="left:216px;top:300px;width:164px;padding:14px">
        <span class="d" style="width:38px;height:38px;border-radius:10px;display:grid;place-items:center;background:var(--teal-50);color:var(--teal-700)">${icon("pill", 20)}</span>
        <b style="display:block;margin-top:10px;font-size:13.5px">Pharmacy</b><span style="font-size:11.5px;color:var(--text-3)">Medicines, prices</span>
        <div style="margin-top:10px"><span class="pill blue">Install</span></div></div>
      <div class="chip" style="left:30px;top:458px"><span class="d teal">${icon("upload", 14)}</span>medicines.csv</div>`,
  },
  {
    eyebrow: "Connect",
    title: "Connect apps, safely",
    body: "Give every app its own key and its own environment. Try changes in Development, then move them to Production.",
    points: [["layout", "Development, Staging and Production kept apart"], ["key", "API keys and signed webhooks"], ["lock", "Internet stays off until you turn it on"]],
    art: `
      <svg style="position:absolute;inset:0" width="410" height="520"><g stroke="#93c5fd" stroke-width="1.5" fill="none">
        <path d="M150 230 C 190 230, 190 230, 205 230"/><path d="M265 230 C 290 230, 290 120, 312 120"/><path d="M265 230 L312 230"/><path d="M265 230 C 290 230, 290 340, 312 340"/></g></svg>
      <div style="position:absolute;left:26px;top:150px;display:flex;flex-direction:column;gap:10px">
        <span class="pill slate" style="padding:6px 11px;font-size:12px">Development</span>
        <span class="pill amber" style="padding:6px 11px;font-size:12px">Staging</span>
        <span class="pill green" style="padding:6px 11px;font-size:12px">${icon("shield", 12)}Production</span>
      </div>
      <div class="card" style="left:150px;top:184px;width:116px;height:96px;display:grid;place-items:center;border-radius:20px"><img src="${B}intraforge-icon.png" width="76"></div>
      <div class="chip" style="left:300px;top:102px;padding-right:10px"><span class="d blue">${icon("globe", 14)}</span>Website</div>
      <div class="chip" style="left:300px;top:212px;padding-right:10px"><span class="d teal">${icon("phone", 14)}</span>Phone</div>
      <div class="chip" style="left:300px;top:322px;padding-right:10px"><span class="d slate">${icon("webhook", 14)}</span>Your app</div>
      <div class="card" style="left:30px;top:408px;width:350px;padding:12px 14px;display:flex;align-items:center;gap:12px">
        <span class="d" style="width:34px;height:34px;border-radius:9px;display:grid;place-items:center;background:var(--sunken);color:var(--text-2)">${icon("lock", 17)}</span>
        <div><b style="display:block;font-size:13px">Internet access</b><span style="font-size:11.5px;color:var(--text-3)">Off · local network only</span></div>
        <span class="toggle" style="margin-left:auto"></span></div>`,
  },
  {
    eyebrow: "Protect",
    title: "You decide who sees what",
    body: "Give people roles, not passwords. Every action is recorded, and your data is backed up every day.",
    points: [["users", "Roles and sharing for every folder and app"], ["fingerprint", "Passkeys and two-step sign-in"], ["calendar", "Audit log and tested daily backups"]],
    next: "Start using IntraForge",
    art: `
      <div class="card" style="left:30px;top:60px;width:350px;padding:14px 16px 6px">
        <div style="font-size:12px;font-weight:600;display:flex;align-items:center;gap:7px">${icon("users", 14)}People</div>
        ${[["SA", "#2563eb", "Selam", "Owner", "blue"], ["DM", "#0d9488", "Daniel", "Manager", "teal"], ["LH", "#7c3aed", "Lula", "Cashier", "slate"]]
          .map(([a, c, n, r, k]) => `<div class="row"><span class="avatar" style="background:${c}">${a}</span>${n}<span class="m"><span class="pill ${k}">${r}</span></span></div>`).join("")}
      </div>
      <div class="card" style="left:30px;top:236px;width:350px;padding:14px 16px 6px">
        <div style="font-size:12px;font-weight:600;display:flex;align-items:center;gap:7px">${icon("scroll", 14)}Audit log</div>
        <div class="row"><span class="mono" style="font-size:11px;color:var(--text-3)">10:42</span>Lula sold 2 × Oil filter<span class="m">${icon("check", 13, 2.5)}</span></div>
        <div class="row"><span class="mono" style="font-size:11px;color:var(--text-3)">11:05</span>Daniel received 40 parts<span class="m">${icon("check", 13, 2.5)}</span></div>
        <div class="row"><span class="mono" style="font-size:11px;color:var(--text-3)">11:20</span>Lula tried to change a price<span class="m"><span class="pill" style="background:#fef2f2;color:#b91c1c">Denied</span></span></div>
      </div>
      <div class="chip" style="left:44px;top:420px"><span class="d green">${icon("calendar", 14)}</span>Backup 19:00 · restore tested</div>
      <div class="card" style="left:296px;top:398px;width:78px;height:78px;border-radius:22px;display:grid;place-items:center;color:var(--brand)">${icon("shieldcheck", 40, 1.8)}</div>`,
  },
];

function tourHtml(n) {
  const s = SLIDES[n - 1];
  return `<div class="tour">
    <div class="art"><div class="mesh"></div>${s.art}</div>
    <div class="content">
      <span class="close">${icon("x", 18)}</span>
      <span class="eyebrow">${s.eyebrow} · ${n} of 5</span>
      <h2>${s.title}</h2>
      <p class="body">${s.body}</p>
      <div class="points">${s.points.map(([i, t]) => `<div class="point"><span class="ic">${icon(i, 17)}</span>${t}</div>`).join("")}</div>
      <div class="nav">
        <div class="dots">${[1, 2, 3, 4, 5].map((k) => `<i class="${k === n ? "on" : ""}"></i>`).join("")}</div>
        ${n === 5 ? "" : `<span class="btn link">Skip tour</span>`}
        ${n === 1 ? "" : `<span class="btn">Back</span>`}
        <span class="btn primary">${s.next || "Next"}${icon("arrowright", 16)}</span>
      </div>
    </div></div>`;
}
function fillMeshes() { document.querySelectorAll(".art .mesh").forEach((m) => (m.innerHTML = meshSvg(410, 520, 11))); }
