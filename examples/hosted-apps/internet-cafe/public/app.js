"use strict";
// The page's behaviour. Every price, amount and code comes from the server; this file only shows them.
// All requests use addresses relative to the page, so the site works at https://<pc>:8445/<site>/ and under
// its own name alike.

(function () {
  const $ = (id) => document.getElementById(id);
  const STORE_KEY = "cafe-current-order";
  const ICONS = { "wi-fi": "i-wifi", wifi: "i-wifi", pcs: "i-monitor", pc: "i-monitor", computers: "i-monitor", printing: "i-printer", print: "i-printer", snacks: "i-coffee", drinks: "i-coffee", coffee: "i-coffee" };
  let info = null;
  let current = null; // the order being paid: { number, expiresAt, ... }
  let pollTimer = null;
  let clockTimer = null;

  function remember(order) {
    try {
      if (order) localStorage.setItem(STORE_KEY, JSON.stringify(order));
      else localStorage.removeItem(STORE_KEY);
    } catch { /* private mode: the order number on screen is enough */ }
  }
  function remembered() {
    try {
      return JSON.parse(localStorage.getItem(STORE_KEY) || "null");
    } catch {
      return null;
    }
  }

  async function api(method, path, body) {
    const response = await fetch(`api/${path}`, {
      method,
      headers: body ? { "Content-Type": "application/json" } : {},
      body: body ? JSON.stringify(body) : undefined,
      credentials: "same-origin",
    });
    let data = null;
    try {
      data = await response.json();
    } catch { /* not JSON */ }
    if (!response.ok) {
      const err = new Error((data && data.message) || "Something went wrong. Please try again.");
      err.status = response.status;
      err.data = data;
      throw err;
    }
    return data;
  }

  function toast(text) {
    const el = $("toast");
    el.textContent = text;
    el.hidden = false;
    clearTimeout(toast.t);
    toast.t = setTimeout(() => (el.hidden = true), 2200);
  }
  async function copy(text) {
    try {
      await navigator.clipboard.writeText(text);
      toast("Copied");
    } catch {
      toast("Press and hold to copy");
    }
  }
  function minutesText(m) {
    if (m % 1440 === 0) return m === 1440 ? "1 day" : `${m / 1440} days`;
    if (m % 60 === 0) return m === 60 ? "1 hour" : `${m / 60} hours`;
    if (m > 60) return `${Math.floor(m / 60)} h ${m % 60} min`;
    return `${m} min`;
  }
  function el(tag, attrs = {}, children = []) {
    const node = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs)) {
      if (k === "text") node.textContent = v;
      else if (k === "class") node.className = v;
      else node.setAttribute(k, v);
    }
    for (const child of children) node.append(child);
    return node;
  }
  function icon(id) {
    const ns = "http://www.w3.org/2000/svg";
    const svg = document.createElementNS(ns, "svg");
    svg.setAttribute("class", "i");
    svg.setAttribute("aria-hidden", "true");
    const use = document.createElementNS(ns, "use");
    use.setAttribute("href", `#${id}`);
    svg.append(use);
    return svg;
  }

  // ---- the café's details -------------------------------------------------------------------------------
  function fillCafe(cafe) {
    document.title = `${cafe.cafe_name} — Wi-Fi, PCs and printing`;
    document.querySelectorAll("[data-cafe]").forEach((node) => {
      const value = cafe[node.dataset.cafe];
      if (typeof value === "string" && value) node.textContent = value;
    });
    $("c-address").hidden = !cafe.address;
    if (cafe.phone) {
      $("c-phone").hidden = false;
      $("c-phone-link").textContent = cafe.phone;
      $("c-phone-link").href = `tel:${cafe.phone.replace(/[^0-9+]/g, "")}`;
    }
    const wa = (cafe.whatsapp || "").replace(/[^0-9]/g, "");
    if (wa) {
      $("c-whatsapp").hidden = false;
      $("c-whatsapp-link").href = `https://wa.me/${wa}`;
    }
    const list = $("services-list");
    list.replaceChildren();
    for (const line of (cafe.services || "").split("\n")) {
      const [title, text] = line.split("|").map((s) => (s || "").trim());
      if (!title) continue;
      list.append(
        el("article", { class: "card service" }, [
          el("div", { class: "service-icon" }, [icon(ICONS[title.toLowerCase()] || "i-star")]),
          el("h3", { text: title }),
          el("p", { text: text || "" }),
        ]),
      );
    }
  }

  function fillPackages(packages, currency) {
    const list = $("packages-list");
    const choices = $("choice-list");
    list.replaceChildren();
    choices.replaceChildren();
    if (!packages.length) {
      list.append(el("p", { class: "muted", text: "Prices are coming soon. Please ask at the counter." }));
      return;
    }
    let firstAvailable = null;
    for (const p of packages) {
      const card = el("article", { class: `card package${p.available ? "" : " sold-out"}` }, [
        el("div", { class: "time", text: minutesText(p.minutes) }),
        el("div", { class: "name", text: p.name }),
        el("div", { class: "price", text: `${p.price} ${currency}` }),
      ]);
      if (!p.available) card.append(el("span", { class: "badge", text: "Sold out" }));
      const buy = el("button", { class: "btn btn-accent", type: "button", text: p.available ? "Buy" : "Ask at the counter" });
      buy.disabled = !p.available;
      buy.addEventListener("click", () => {
        const radio = document.querySelector(`input[name="package"][value="${CSS.escape(p.id)}"]`);
        if (radio) radio.checked = true;
        location.hash = "#buy";
        $("phone").focus({ preventScroll: true });
      });
      card.append(buy);
      list.append(card);

      const input = el("input", { type: "radio", name: "package", value: p.id, id: `pkg-${p.id}` });
      input.disabled = !p.available;
      if (p.available && !firstAvailable) firstAvailable = input;
      choices.append(
        el("label", { class: "choice", for: `pkg-${p.id}` }, [
          input,
          el("span", {}, [el("b", { text: minutesText(p.minutes) }), document.createTextNode(p.name), el("em", { text: p.available ? `${p.price} ${currency}` : "Sold out" })]),
        ]),
      );
    }
    if (firstAvailable) firstAvailable.checked = true;
  }

  async function loadInfo() {
    try {
      info = await api("GET", "info");
      $("setup-notice").hidden = true;
      fillCafe(info.cafe);
      fillPackages(info.packages, info.cafe.currency);
    } catch (err) {
      if (err.data && err.data.error === "setup") {
        $("setup-notice").hidden = false;
        const ul = $("setup-problems");
        ul.replaceChildren(...(err.data.problems || []).map((p) => el("li", { text: p })));
        $("packages-list").replaceChildren(el("p", { class: "muted", text: "Prices will appear here soon." }));
      } else {
        $("packages-list").replaceChildren(el("p", { class: "muted", text: "Prices could not be loaded. Pull down to refresh." }));
      }
    }
  }

  // ---- buying ------------------------------------------------------------------------------------------
  function showStep(name) {
    for (const step of ["choose", "pay", "done", "ended"]) $(`step-${step}`).hidden = step !== name;
    const order = ["choose", "pay", "done"];
    const at = order.indexOf(name === "ended" ? "pay" : name);
    document.querySelectorAll(".steps li").forEach((li, i) => {
      li.classList.toggle("active", i === at);
      li.classList.toggle("done", i < at);
    });
  }
  function stopTimers() {
    clearTimeout(pollTimer);
    clearInterval(clockTimer);
  }

  function showPayment(order) {
    current = order;
    remember({ number: order.number, expiresAt: order.expiresAt, payCode: order.payCode, qrImage: order.qrImage, amount: order.amount, packageName: order.packageName, minutes: order.minutes });
    $("pay-number").textContent = order.number;
    $("pay-amount").textContent = order.amount;
    $("pay-package").textContent = `${order.packageName} · ${minutesText(order.minutes)}`;
    $("pay-code").value = order.payCode || "";
    // A ready image address from the server (data:image/...): an <img> never runs anything inside it.
    const qr = typeof order.qrImage === "string" && order.qrImage.startsWith("data:image/") ? order.qrImage : "";
    $("pay-qr").closest("figure").hidden = !qr;
    if (qr) $("pay-qr").src = qr;
    const wallet = info && info.walletUrl;
    $("open-wallet").hidden = !wallet;
    if (wallet) $("open-wallet").href = wallet;
    $("pay-status").replaceChildren(el("span", { class: "dot" }), document.createTextNode(" Waiting for your payment…"));
    showStep("pay");
    tickClock();
    clearInterval(clockTimer);
    clockTimer = setInterval(tickClock, 1000);
    poll(1500);
  }
  function tickClock() {
    if (!current || !current.expiresAt) return;
    const left = Math.max(0, Math.round((Date.parse(current.expiresAt) - Date.now()) / 1000));
    const box = $("pay-countdown");
    box.textContent = `${Math.floor(left / 60)}:${String(left % 60).padStart(2, "0")}`;
    box.classList.toggle("low", left < 60);
  }
  function poll(delay) {
    clearTimeout(pollTimer);
    pollTimer = setTimeout(checkOrder, delay);
  }
  async function checkOrder() {
    if (!current) return;
    try {
      const order = await api("GET", `orders/${encodeURIComponent(current.number)}`);
      if (order.status === "paid") return showDone(order);
      if (order.status === "expired" || order.status === "cancelled") return showEnded(order.status);
      poll(2500);
    } catch (err) {
      if (err.status === 404) return showEnded("missing");
      poll(5000);
    }
  }
  function showDone(order) {
    stopTimers();
    remember(null);
    current = null;
    $("done-package").textContent = `${order.packageName} · ${minutesText(order.minutes)}`;
    $("done-voucher").textContent = order.voucher || "—";
    $("copy-voucher").hidden = !order.voucher;
    $("done-number").textContent = order.number;
    $("done-receipt").textContent = order.receipt || "—";
    $("done-notice").hidden = !order.notice;
    $("done-notice").textContent = order.notice || "";
    showStep("done");
    $("step-done").scrollIntoView({ block: "start" });
  }
  function showEnded(reason) {
    stopTimers();
    remember(null);
    current = null;
    const texts = {
      expired: ["This payment expired", "Nothing was charged. You can start again."],
      cancelled: ["This payment was cancelled", "Nothing was charged. You can start again."],
      missing: ["This order was not found", "Start again, or find a paid order under My code."],
    };
    const [title, text] = texts[reason] || texts.expired;
    $("ended-title").textContent = title;
    $("ended-text").textContent = text;
    showStep("ended");
  }

  async function submitBuy(event) {
    event.preventDefault();
    const picked = document.querySelector('input[name="package"]:checked');
    const phone = $("phone").value.trim();
    const error = $("buy-error");
    error.hidden = true;
    if (!picked) {
      error.textContent = "Choose how much time you want.";
      error.hidden = false;
      return;
    }
    if (!/^\+?[0-9 ()-]{7,24}$/.test(phone)) {
      error.textContent = "Enter your phone number (7 to 15 digits).";
      error.hidden = false;
      $("phone").focus();
      return;
    }
    const button = $("buy-btn");
    button.disabled = true;
    try {
      const order = await api("POST", "orders", { packageId: picked.value, phone });
      showPayment(order);
    } catch (err) {
      error.textContent = err.message;
      error.hidden = false;
      if (err.data && err.data.error === "sold_out") loadInfo();
    } finally {
      button.disabled = false;
    }
  }

  async function submitLookup(event) {
    event.preventDefault();
    const error = $("lookup-error");
    const result = $("lookup-result");
    error.hidden = true;
    result.hidden = true;
    try {
      const order = await api("POST", "lookup", { number: $("lookup-number").value, phone: $("lookup-phone").value });
      const parts = [el("p", { class: "muted", text: `${order.packageName} · ${minutesText(order.minutes)} · ${order.amount}` })];
      if (order.status === "paid" && order.voucher) {
        const code = el("div", { class: "voucher", text: order.voucher });
        const btn = el("button", { class: "btn btn-sm", type: "button", text: "Copy code" });
        btn.addEventListener("click", () => copy(order.voucher));
        parts.push(code, btn, el("p", { class: "muted small", text: `Receipt ${order.receipt || "—"}` }));
      } else if (order.status === "paid") {
        parts.push(el("div", { class: "notice notice-warn", text: order.notice || "Paid. Ask at the counter." }));
      } else if (order.status === "pending") {
        parts.push(el("div", { class: "notice notice-warn", text: "Not paid yet. Finish the payment in your IF Pay wallet." }));
      } else {
        parts.push(el("div", { class: "notice notice-bad", text: "This order was not paid. Nothing was charged." }));
      }
      result.replaceChildren(...parts);
      result.hidden = false;
    } catch (err) {
      error.textContent = err.message;
      error.hidden = false;
    }
  }

  function startAgain() {
    stopTimers();
    remember(null);
    current = null;
    showStep("choose");
    loadInfo();
  }

  document.addEventListener("DOMContentLoaded", async () => {
    $("year").textContent = String(new Date().getFullYear());
    $("buy-form").addEventListener("submit", submitBuy);
    $("lookup-form").addEventListener("submit", submitLookup);
    $("copy-pay-code").addEventListener("click", () => copy($("pay-code").value));
    $("copy-voucher").addEventListener("click", () => copy($("done-voucher").textContent));
    $("pay-cancel").addEventListener("click", startAgain);
    $("start-again").addEventListener("click", startAgain);
    $("buy-again").addEventListener("click", startAgain);
    await loadInfo();
    // Back after a refresh or after switching to the wallet app: carry on with the same order.
    // The payment may have gone through while the page was closed, even after the QR's time ran out: ask.
    const saved = remembered();
    if (saved && saved.number) {
      if (Date.parse(saved.expiresAt || 0) > Date.now()) {
        showPayment(saved);
      } else {
        current = saved;
        showStep("pay");
        checkOrder();
      }
      location.hash = "#buy";
    }
    document.addEventListener("visibilitychange", () => {
      if (document.visibilityState === "visible" && current) poll(100);
    });
  });
})();
