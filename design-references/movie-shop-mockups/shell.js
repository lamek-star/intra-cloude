// The owner's Movie Shop frame: top bar (logo, search, portal status) and the left side (storage list, then sections).
function shell(active, main) {
  const nav = [
    ["film", "Catalogue"],
    ["receipt", "Sales"],
    ["users", "Customers"],
    ["gift", "Prices & rewards"],
    ["megaphone", "Ads"],
  ];
  return `<div class="app">
    <header class="top">
      <div class="brand"><span class="mark">${icon("play", 16, 2.6)}</span><div><b>LAMEK MOVIE SHOP</b><small>Owner · IntraForge app</small></div></div>
      <div class="input" style="width:380px;margin-left:24px">${icon("search", 16)} Search movies, series, actors...</div>
      <div style="margin-left:auto;display:flex;align-items:center;gap:10px">
        <span class="chip live"><span class="dot"></span>Customer portal live · shop Wi-Fi</span>
        <span class="chip">${icon("qr", 13)} shop.local/movies</span>
        <span class="chip teal">${icon("wallet", 13)} IF Pay connected</span>
        <span style="width:34px;height:34px;border-radius:50%;background:linear-gradient(135deg,#f5a524,#b45309);display:grid;place-items:center;font-weight:800;color:#1a1203;font-size:13px;margin-left:6px">L</span>
      </div>
    </header>
    <aside class="side">
      <span class="label">Storage</span>
      <div class="store on"><span class="ic" style="color:var(--amber2)">${icon("harddrive", 16)}</span><div style="flex:1"><b>Movies drive (D:)</b><span>1.8 of 4 TB · 1,021 titles</span><div class="bar" style="margin-top:6px"><i style="width:45%"></i></div></div></div>
      <div class="store"><span class="ic">${icon("server", 16)}</span><div style="flex:1"><b>NAS · Movies</b><span>3.1 of 8 TB · 2,340 titles</span><div class="bar" style="margin-top:6px"><i style="width:39%;background:#64748b"></i></div></div></div>
      <div class="store"><span class="ic" style="color:var(--teal)">${icon("usb", 16)}</span><div style="flex:1"><b>Kingston USB (E:)</b><span>Customer drive · 41 GB free</span><div style="margin-top:6px"><span class="chip teal" style="font-size:10px;padding:2px 7px">Copy target</span></div></div></div>
      <div class="nav" style="color:var(--muted)">${icon("plus", 16)} Add storage</div>
      <span class="label" style="margin-top:10px">Shop</span>
      ${nav.map(([i, n]) => `<div class="nav ${n === active ? "on" : ""}">${icon(i, 17)} ${n}</div>`).join("")}
      <div style="margin-top:auto;padding:12px;border-radius:12px;background:var(--bg2);border:1px solid var(--line);font-size:11.5px;color:var(--muted)">
        <b style="color:var(--text);font-size:12px;display:block;margin-bottom:4px">Today</b>
        38 movies sold · 1,640 credits<br>12 new customers on Wi-Fi
      </div>
    </aside>
    <main class="main">${main}</main>
  </div>`;
}
