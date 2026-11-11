// Movie Shop mockups: icons (lucide.dev style, MIT), drawn movie covers (no real posters), and a fictional catalogue.
const I = {
  play: '<polygon points="6 3 20 12 6 21 6 3"/>',
  plus: '<path d="M5 12h14"/><path d="M12 5v14"/>',
  film: '<rect width="18" height="18" x="3" y="3" rx="2"/><path d="M7 3v18"/><path d="M3 7.5h4"/><path d="M3 12h18"/><path d="M3 16.5h4"/><path d="M17 3v18"/><path d="M17 7.5h4"/><path d="M17 16.5h4"/>',
  usb: '<circle cx="10" cy="7" r="1"/><circle cx="4" cy="20" r="1"/><path d="M4.7 19.3 19 5"/><path d="m21 3-3 1 2 2Z"/><path d="M9.26 7.68 5 12l2 5"/><path d="m10 14 5 2 3.5-3.5"/><path d="m18 12 1-1 1 1-1 1Z"/>',
  wallet: '<path d="M19 7V4a1 1 0 0 0-1-1H5a2 2 0 0 0 0 4h15a1 1 0 0 1 1 1v4h-3a2 2 0 0 0 0 4h3a1 1 0 0 0 1-1v-2a1 1 0 0 0-1-1"/><path d="M3 5v14a2 2 0 0 0 2 2h15a1 1 0 0 0 1-1v-4"/>',
  gift: '<rect x="3" y="8" width="18" height="4" rx="1"/><path d="M12 8v13"/><path d="M19 12v7a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2v-7"/><path d="M7.5 8a2.5 2.5 0 0 1 0-5A4.8 8 0 0 1 12 8a4.8 8 0 0 1 4.5-5 2.5 2.5 0 0 1 0 5"/>',
  megaphone: '<path d="m3 11 18-5v12L3 14v-3z"/><path d="M11.6 16.8a3 3 0 1 1-5.8-1.6"/>',
  search: '<circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>',
  star: '<polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>',
  wifi: '<path d="M12 20h.01"/><path d="M2 8.82a15 15 0 0 1 20 0"/><path d="M5 12.859a10 10 0 0 1 14 0"/><path d="M8.5 16.429a5 5 0 0 1 7 0"/>',
  qr: '<rect width="5" height="5" x="3" y="3" rx="1"/><rect width="5" height="5" x="16" y="3" rx="1"/><rect width="5" height="5" x="3" y="16" rx="1"/><path d="M21 16h-3a2 2 0 0 0-2 2v3"/><path d="M21 21v.01"/><path d="M12 7v3a2 2 0 0 1-2 2H7"/><path d="M3 12h.01"/><path d="M12 3h.01"/><path d="M12 16v.01"/><path d="M16 12h1"/><path d="M21 12v.01"/><path d="M12 21v-1"/>',
  tag: '<path d="M12.586 2.586A2 2 0 0 0 11.172 2H4a2 2 0 0 0-2 2v7.172a2 2 0 0 0 .586 1.414l8.704 8.704a2.426 2.426 0 0 0 3.42 0l6.58-6.58a2.426 2.426 0 0 0 0-3.42z"/><circle cx="7.5" cy="7.5" r=".5" fill="currentColor"/>',
  sliders: '<path d="M20 7h-9"/><path d="M14 17H5"/><circle cx="17" cy="17" r="3"/><circle cx="7" cy="7" r="3"/>',
  home: '<path d="M15 21v-8a1 1 0 0 0-1-1h-4a1 1 0 0 0-1 1v8"/><path d="M3 10a2 2 0 0 1 .709-1.528l7-5.999a2 2 0 0 1 2.582 0l7 5.999A2 2 0 0 1 21 10v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>',
  user: '<path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>',
  users: '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
  info: '<circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/>',
  filter: '<path d="M3 6h18"/><path d="M7 12h10"/><path d="M10 18h4"/>',
  refresh: '<path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8"/><path d="M21 3v5h-5"/><path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16"/><path d="M8 16H3v5"/>',
  coins: '<circle cx="8" cy="8" r="6"/><path d="M18.09 10.37A6 6 0 1 1 10.34 18"/><path d="M7 6h1v4"/><path d="m16.71 13.88.7.71-2.82 2.82"/>',
  tv: '<rect width="20" height="15" x="2" y="7" rx="2"/><polyline points="17 2 12 7 7 2"/>',
  check: '<path d="M20 6 9 17l-5-5"/>',
  folder: '<path d="M20 20a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.69-.9L9.6 3.9A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2Z"/>',
  harddrive: '<path d="M22 12H2"/><path d="M5.45 5.11 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z"/><path d="M6 16h.01"/><path d="M10 16h.01"/>',
  server: '<rect width="20" height="8" x="2" y="2" rx="2" ry="2"/><rect width="20" height="8" x="2" y="14" rx="2" ry="2"/><path d="M6 6h.01"/><path d="M6 18h.01"/>',
  chevronright: '<path d="m9 18 6-6-6-6"/>',
  chevrondown: '<path d="m6 9 6 6 6-6"/>',
  chevronleft: '<path d="m15 18-6-6 6-6"/>',
  x: '<path d="M18 6 6 18"/><path d="m6 6 12 12"/>',
  clock: '<circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/>',
  download: '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><path d="m7 10 5 5 5-5"/><path d="M12 15V3"/>',
  shieldcheck: '<path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"/><path d="m9 12 2 2 4-4"/>',
  lock: '<rect width="18" height="11" x="3" y="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>',
  phone: '<rect width="14" height="20" x="5" y="2" rx="2" ry="2"/><path d="M12 18h.01"/>',
  calendar: '<path d="M8 2v4"/><path d="M16 2v4"/><rect width="18" height="18" x="3" y="4" rx="2"/><path d="M3 10h18"/>',
  bell: '<path d="M10.268 21a2 2 0 0 0 3.464 0"/><path d="M3.262 15.326A1 1 0 0 0 4 17h16a1 1 0 0 0 .74-1.673C19.41 13.956 18 12.499 18 8A6 6 0 0 0 6 8c0 4.499-1.411 5.956-2.738 7.326"/>',
  image: '<rect width="18" height="18" x="3" y="3" rx="2" ry="2"/><circle cx="9" cy="9" r="2"/><path d="m21 15-3.086-3.086a2 2 0 0 0-2.828 0L6 21"/>',
  heart: '<path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7Z"/>',
  receipt: '<path d="M4 2v20l2-1 2 1 2-1 2 1 2-1 2 1 2-1 2 1V2l-2 1-2-1-2 1-2-1-2 1-2-1-2 1Z"/><path d="M16 8h-6a2 2 0 1 0 0 4h4a2 2 0 1 1 0 4H8"/><path d="M12 17.5v-11"/>',
  trending: '<polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/><polyline points="16 7 22 7 22 13"/>',
};
function icon(n, s = 18, w = 2) {
  if (w === 0) return `<svg width="${s}" height="${s}" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">${I[n] || ""}</svg>`;
  return `<svg width="${s}" height="${s}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="${w}" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${I[n] || ""}</svg>`;
}

// A drawn cover: a colour story, a simple motif and the title -- every title here is invented.
const MOTIFS = {
  sun: (a) => `<circle cx="100" cy="128" r="46" fill="${a}" opacity=".9"/><path d="M0 190 Q60 150 100 175 T200 160 V300 H0Z" fill="#000" opacity=".55"/><path d="M0 215 Q70 180 120 205 T200 195 V300 H0Z" fill="#000" opacity=".7"/>`,
  mountain: (a) => `<path d="M0 230 L60 130 L95 175 L140 95 L200 200 V300 H0Z" fill="#000" opacity=".55"/><path d="M140 95 L155 120 L130 125Z" fill="#fff" opacity=".8"/><circle cx="160" cy="55" r="16" fill="${a}" opacity=".8"/>`,
  wave: (a) => `<path d="M0 170 Q50 140 100 170 T200 170 V300 H0Z" fill="${a}" opacity=".45"/><path d="M0 200 Q50 170 100 200 T200 200 V300 H0Z" fill="#000" opacity=".45"/><path d="M60 120 L100 60 L104 120Z" fill="#fff" opacity=".85"/><path d="M52 122 H112 L104 134 H60Z" fill="#000" opacity=".7"/>`,
  city: (a) => `${[0, 26, 48, 80, 104, 130, 158, 178].map((x, i) => `<rect x="${x}" y="${120 + ((i * 37) % 60)}" width="${22 + (i % 3) * 6}" height="200" fill="#000" opacity=".6"/>`).join("")}${[30, 60, 95, 140, 170].map((x, i) => `<rect x="${x}" y="${150 + i * 9}" width="4" height="4" fill="${a}"/>`).join("")}`,
  moon: (a) => `<circle cx="130" cy="80" r="34" fill="${a}" opacity=".9"/><circle cx="144" cy="72" r="30" fill="#000" opacity=".35"/>${[[30, 40], [60, 90], [170, 140], [20, 120], [90, 30]].map(([x, y]) => `<circle cx="${x}" cy="${y}" r="1.6" fill="#fff"/>`).join("")}<path d="M0 220 Q100 180 200 225 V300 H0Z" fill="#000" opacity=".6"/>`,
  road: (a) => `<path d="M90 300 L98 150 H102 L110 300Z" fill="${a}" opacity=".7"/><path d="M0 300 L95 150 H105 L200 300Z" fill="#000" opacity=".45"/><path d="M0 150 H200" stroke="${a}" stroke-width="1" opacity=".6"/>`,
  circle: (a) => `<circle cx="100" cy="120" r="70" fill="none" stroke="${a}" stroke-width="10" opacity=".8"/><circle cx="100" cy="120" r="44" fill="${a}" opacity=".25"/>`,
  bird: (a) => `<path d="M40 130 Q70 100 100 128 Q130 100 160 130 Q130 115 100 145 Q70 115 40 130Z" fill="${a}" opacity=".9"/><path d="M0 240 Q100 200 200 245 V300 H0Z" fill="#000" opacity=".6"/>`,
  cup: (a) => `<rect x="65" y="110" width="70" height="70" rx="10" fill="${a}" opacity=".85"/><path d="M135 125 h14 a12 12 0 0 1 0 30 h-14" fill="none" stroke="${a}" stroke-width="8"/><path d="M85 95 q8-14 0-26 M105 95 q8-14 0-26" stroke="#fff" stroke-width="4" fill="none" opacity=".7"/>`,
  camel: (a) => `<path d="M40 200 q10-40 30-40 q10-20 25 0 q12-24 28 0 q20 0 22 20 l14-30 q8-4 10 4 l-14 46 v38 h-8 v-34 h-50 v34 h-8 v-38 z" fill="${a}" opacity=".9"/><circle cx="160" cy="60" r="18" fill="#fff" opacity=".8"/>`,
};
function cover(m, opts = {}) {
  const [c1, c2, accent] = m.c;
  const art = MOTIFS[m.m](accent);
  return `<div class="cover" style="background:linear-gradient(165deg,${c1},${c2})">
    <svg viewBox="0 0 200 300" preserveAspectRatio="xMidYMid slice" class="cover-art">${art}</svg>
    <div class="cover-shade"></div>
    ${m.badge ? `<span class="cover-badge">${m.badge}</span>` : ""}
    ${opts.price !== false && m.p ? `<span class="cover-price">${icon("coins", 11, 2.4)} ${m.p}</span>` : ""}
    <div class="cover-title" style="font-size:${m.t.length > 12 ? 15 : 18}px">${m.t}</div>
  </div>`;
}

const MOVIES = [
  { t: "Desert Wind", y: 2025, d: "1h 58m", s: "2.1 GB", g: "Action", p: 50, m: "sun", c: ["#f59e0b", "#7c2d12", "#fde68a"], badge: "NEW", r: 4.6 },
  { t: "Iron Harbor", y: 2024, d: "2h 06m", s: "2.4 GB", g: "Action", p: 50, m: "wave", c: ["#0ea5e9", "#0c1e3e", "#7dd3fc"], badge: "4K", r: 4.3 },
  { t: "Red Mountain", y: 2024, d: "1h 49m", s: "1.9 GB", g: "Action", p: 40, m: "mountain", c: ["#ef4444", "#3b0a0a", "#fca5a5"], r: 4.1 },
  { t: "Night Runner", y: 2023, d: "1h 52m", s: "1.8 GB", g: "Action", p: 40, m: "city", c: ["#6366f1", "#0b0b2e", "#fbbf24"], r: 4.4 },
  { t: "Last Signal", y: 2025, d: "2h 11m", s: "2.6 GB", g: "Action", p: 50, m: "circle", c: ["#10b981", "#032b22", "#6ee7b7"], badge: "NEW", r: 4.5 },
  { t: "Black Falcon", y: 2022, d: "1h 44m", s: "1.7 GB", g: "Action", p: 30, m: "bird", c: ["#334155", "#020617", "#f97316"], r: 3.9 },
  { t: "Dust & Thunder", y: 2023, d: "2h 02m", s: "2.2 GB", g: "Action", p: 40, m: "road", c: ["#d97706", "#1c1007", "#fcd34d"], r: 4.0 },
  { t: "Steel Horizon", y: 2024, d: "1h 57m", s: "2.0 GB", g: "Action", p: 50, m: "moon", c: ["#8b5cf6", "#140a2e", "#e9d5ff"], badge: "4K", r: 4.2 },
  { t: "Zero Hour", y: 2021, d: "1h 41m", s: "1.6 GB", g: "Action", p: 30, m: "circle", c: ["#f43f5e", "#1f0510", "#fecdd3"], r: 3.8 },
  { t: "The Long Road", y: 2022, d: "2h 15m", s: "2.7 GB", g: "Action", p: 40, m: "road", c: ["#64748b", "#0f172a", "#e2e8f0"], r: 4.1 },
];
const SERIES = [
  { t: "The Coffee House", y: 2025, d: "3 seasons", s: "38 GB", g: "Series", p: 20, m: "cup", c: ["#a16207", "#1c0f05", "#fde68a"], badge: "S3" },
  { t: "Harbor Lights", y: 2024, d: "2 seasons", s: "26 GB", g: "Series", p: 20, m: "wave", c: ["#14b8a6", "#042f2e", "#99f6e4"], badge: "S2" },
  { t: "Old Asmara", y: 2023, d: "1 season", s: "11 GB", g: "Series", p: 20, m: "city", c: ["#b45309", "#1a0e04", "#fde68a"] },
  { t: "Little Camel", y: 2025, d: "1h 22m", s: "1.2 GB", g: "Kids", p: 30, m: "camel", c: ["#fb923c", "#7c2d12", "#fff7ed"] },
  { t: "Red Sea Deep", y: 2024, d: "58m", s: "0.9 GB", g: "Documentary", p: 30, m: "wave", c: ["#0284c7", "#03111f", "#bae6fd"] },
  { t: "Wedding Week", y: 2025, d: "1h 46m", s: "1.7 GB", g: "Comedy", p: 40, m: "circle", c: ["#ec4899", "#2a0517", "#fbcfe8"], badge: "NEW" },
  { t: "Two Uncles", y: 2023, d: "1h 38m", s: "1.5 GB", g: "Comedy", p: 30, m: "sun", c: ["#eab308", "#271c02", "#fef08a"] },
];
const FOLDERS = [
  { n: "Series", c: 142, m: SERIES[0] },
  { n: "Action", c: 318, m: MOVIES[0] },
  { n: "Comedy", c: 204, m: SERIES[5] },
  { n: "Drama", c: 177, m: MOVIES[7] },
  { n: "Kids", c: 96, m: SERIES[3] },
  { n: "Documentary", c: 58, m: SERIES[4] },
];

function hydrate() {
  document.querySelectorAll("i[data-i]").forEach((el) => (el.outerHTML = icon(el.dataset.i, Number(el.dataset.s || 18), Number(el.dataset.w || 2))));
}
