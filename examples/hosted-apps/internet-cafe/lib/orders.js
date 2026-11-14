"use strict";
// Buying Wi-Fi time. The rules that keep money and codes straight:
//  1. A voucher is reserved for an order BEFORE the customer is asked to pay, so nobody pays for a code that
//     is no longer there. The order's "voucher" column is unique: the database refuses to give one code to two
//     orders, whatever happens in this program.
//  2. The code is shown only after IntraForge Pay says the payment is "paid". The price and the amount come from
//     the café's own packages here, never from the browser.
//  3. A reservation whose payment expired, was cancelled or never started is released by itself.
//  4. Every step can be repeated safely (a refresh, two tabs, a restart in the middle).

const crypto = require("node:crypto");
const { IntraForgeError } = require("./intraforge");

const ALPHABET = "23456789ABCDEFGHJKMNPQRSTUVWXYZ";
const STALE_NEW_MS = 5 * 60 * 1000;
const PAY_CHECK_MS = 2000;

class UserError extends Error {
  constructor(status, message, code) {
    super(message);
    this.status = status;
    this.code = code || "refused";
  }
}

function newOrderNumber() {
  let s = "";
  for (let i = 0; i < 8; i++) s += ALPHABET[crypto.randomInt(ALPHABET.length)];
  return `IC-${s.slice(0, 4)}-${s.slice(4)}`;
}

function normalizePhone(raw) {
  const text = String(raw ?? "").trim();
  if (!/^\+?[0-9 ()-]{7,24}$/.test(text)) return null;
  const digits = text.replace(/[^0-9]/g, "");
  if (digits.length < 7 || digits.length > 15) return null;
  return (text.startsWith("+") ? "+" : "") + digits;
}

function normalizeOrderNumber(raw) {
  const text = String(raw ?? "").toUpperCase().replace(/[^0-9A-Z]/g, "");
  const body = text.startsWith("IC") ? text.slice(2) : text;
  if (body.length !== 8 || [...body].some((c) => !ALPHABET.includes(c))) return null;
  return `IC-${body.slice(0, 4)}-${body.slice(4)}`;
}

// IF Pay sends the QR as a ready image address (data:image/svg+xml;base64,...). Only an image address is passed
// on to the page; raw SVG markup is wrapped into one, and anything else is dropped (the page then shows the code).
function qrImage(value) {
  const text = String(value || "");
  if (/^data:image\/(svg\+xml|png);base64,[A-Za-z0-9+/=]+$/.test(text)) return text;
  if (text.trimStart().startsWith("<svg")) return `data:image/svg+xml;base64,${Buffer.from(text).toString("base64")}`;
  return null;
}

function formatAmount(minor, currency) {
  return `${(minor / 100).toFixed(2)} ${currency}`;
}

// One change at a time: reserving and releasing codes never interleave inside this program.
function createLock() {
  let tail = Promise.resolve();
  return (fn) => {
    const run = tail.then(fn, fn);
    tail = run.then(
      () => undefined,
      () => undefined,
    );
    return run;
  };
}

function createOrders({ store, client, log = () => {}, now = () => Date.now() }) {
  const locked = createLock();
  const lastPayCheck = new Map();

  async function findOrder(number) {
    const data = await store.rows("cafe_orders", { f_number: number, limit: 1 });
    return data.results[0] || null;
  }
  async function findVoucher(code) {
    const data = await store.rows("cafe_vouchers", { f_code: code, limit: 1 });
    return data.results[0] || null;
  }

  async function releaseVoucher(order, newStatus) {
    if (order.voucher) {
      const voucher = await findVoucher(order.voucher);
      if (voucher && voucher.status === "reserved" && voucher.order_number === order.number) {
        await store.update("cafe_vouchers", voucher.id, { status: "available", order_number: "" });
      }
    }
    await store.update("cafe_orders", order.id, { status: newStatus, voucher: null });
    store.invalidate();
  }

  async function reserve(order, minutes) {
    // A few tries: a code another order already holds is skipped (the unique column refuses it).
    for (let attempt = 0; attempt < 5; attempt++) {
      const data = await store.rows("cafe_vouchers", {
        f_status: "available",
        f_minutes: String(minutes),
        limit: 1,
        offset: String(attempt),
      });
      const voucher = data.results[0];
      if (!voucher) return null;
      try {
        await store.update("cafe_orders", order.id, { voucher: voucher.code });
      } catch (err) {
        if (err instanceof IntraForgeError && err.status === 400) {
          log(`voucher ${voucher.id} is already held by another order; skipping`);
          continue;
        }
        throw err;
      }
      await store.update("cafe_vouchers", voucher.id, { status: "reserved", order_number: order.number });
      return voucher;
    }
    return null;
  }

  async function create({ packageId, phone }) {
    const cleanPhone = normalizePhone(phone);
    if (!cleanPhone) throw new UserError(400, "Enter your phone number (7 to 15 digits).", "phone");
    const { packages, settings } = await store.load();
    const pkg = packages.find((p) => p.id === String(packageId));
    if (!pkg) throw new UserError(400, "Choose one of the packages.", "package");

    const order = await locked(async () => {
      if ((await store.availableCount(pkg.minutes)) < 1) {
        throw new UserError(409, `${pkg.name} is sold out right now. Please ask at the counter.`, "sold_out");
      }
      let row = null;
      for (let attempt = 0; attempt < 3 && !row; attempt++) {
        try {
          row = await store.insert("cafe_orders", {
            number: newOrderNumber(),
            phone: cleanPhone,
            package_name: pkg.name,
            minutes: pkg.minutes,
            amount: (pkg.priceMinor / 100).toFixed(2),
            status: "new",
            pay_request: "",
            receipt: "",
            // IntraForge's datetime columns take whole seconds in UTC.
            created_at: new Date(now()).toISOString().replace(/\.\d{3}Z$/, "Z"),
          });
        } catch (err) {
          if (!(err instanceof IntraForgeError && err.status === 400 && /unique/i.test(err.message))) throw err;
        }
      }
      if (!row) throw new UserError(503, "Please try again.", "busy");
      const voucher = await reserve(row, pkg.minutes);
      if (!voucher) {
        await store.update("cafe_orders", row.id, { status: "sold_out" });
        throw new UserError(409, `${pkg.name} is sold out right now. Please ask at the counter.`, "sold_out");
      }
      return { ...row, voucher: voucher.code };
    });

    let payment;
    try {
      payment = await client.post("pay/payment-requests/", {
        amountMinor: pkg.priceMinor,
        reference: `Wi-Fi ${pkg.name} (${order.number})`.slice(0, 120),
        externalId: order.number,
      });
    } catch (err) {
      await locked(() => releaseVoucher(order, "failed"));
      if (err instanceof IntraForgeError && (err.status === 403 || err.status === 404)) {
        log(`IF Pay refused the payment request: ${err.status} ${err.message}`);
        throw new UserError(503, "Paying online is not switched on yet. Please pay at the counter.", "pay_off");
      }
      if (err instanceof IntraForgeError && err.status === 400) {
        throw new UserError(400, err.message || "IF Pay refused this payment.", "pay_refused");
      }
      log(`IF Pay could not be reached: ${err.message}`);
      throw new UserError(503, "IF Pay is not available right now. Please try again in a minute.", "pay_down");
    }
    await store.update("cafe_orders", order.id, { status: "pending", pay_request: String(payment.id) });
    lastPayCheck.set(order.number, now());
    return {
      number: order.number,
      status: "pending",
      packageName: pkg.name,
      minutes: pkg.minutes,
      amount: formatAmount(pkg.priceMinor, settings.currency),
      payCode: payment.code,
      qrImage: qrImage(payment.qr_svg),
      expiresAt: payment.expires_at,
    };
  }

  // Looks at IntraForge Pay for a waiting order and settles it (paid -> the code is sold; expired or
  // cancelled -> the code goes back). Safe to call any number of times.
  async function settle(order, { force = false } = {}) {
    if (order.status !== "pending" || !order.pay_request) return order;
    const last = lastPayCheck.get(order.number) || 0;
    if (!force && now() - last < PAY_CHECK_MS) return order;
    lastPayCheck.set(order.number, now());
    let payment;
    try {
      payment = await client.get(`pay/payment-requests/${encodeURIComponent(order.pay_request)}/`);
    } catch (err) {
      log(`could not ask IF Pay about ${order.number}: ${err.message}`);
      return order;
    }
    if (payment.status === "paid") {
      return locked(async () => {
        const fresh = await findOrder(order.number);
        if (!fresh || fresh.status === "paid") return fresh;
        await store.update("cafe_orders", fresh.id, { status: "paid", receipt: String(payment.receipt_number || "") });
        if (fresh.voucher) {
          const voucher = await findVoucher(fresh.voucher);
          if (voucher && voucher.status !== "sold") await store.update("cafe_vouchers", voucher.id, { status: "sold", order_number: fresh.number });
        }
        lastPayCheck.delete(order.number);
        store.invalidate();
        return { ...fresh, status: "paid", receipt: String(payment.receipt_number || "") };
      });
    }
    if (payment.status === "expired" || payment.status === "cancelled") {
      return locked(async () => {
        const fresh = await findOrder(order.number);
        if (!fresh || fresh.status !== "pending") return fresh;
        await releaseVoucher(fresh, payment.status);
        lastPayCheck.delete(order.number);
        return { ...fresh, status: payment.status, voucher: null };
      });
    }
    return order;
  }

  function publicView(order, settings) {
    const view = {
      number: order.number,
      status: order.status,
      packageName: order.package_name,
      minutes: Number(order.minutes),
      amount: formatAmount(Math.round(Number(order.amount) * 100), settings.currency),
      receipt: order.receipt || null,
    };
    if (order.status === "paid") {
      view.voucher = order.voucher || null;
      if (!order.voucher) view.notice = "Paid. Show this receipt at the counter to get your code.";
    }
    return view;
  }

  async function get(numberRaw) {
    const number = normalizeOrderNumber(numberRaw);
    if (!number) throw new UserError(404, "No such order.", "not_found");
    let order = await findOrder(number);
    if (!order) throw new UserError(404, "No such order.", "not_found");
    order = (await settle(order)) || order;
    const { settings } = await store.load();
    return publicView(order, settings);
  }

  async function lookup({ number: numberRaw, phone }) {
    const number = normalizeOrderNumber(numberRaw);
    const cleanPhone = normalizePhone(phone);
    if (!number || !cleanPhone) throw new UserError(404, "No order with that number and phone.", "not_found");
    let order = await findOrder(number);
    if (!order || normalizePhone(order.phone) !== cleanPhone) {
      throw new UserError(404, "No order with that number and phone.", "not_found");
    }
    order = (await settle(order, { force: true })) || order;
    const { settings } = await store.load();
    return publicView(order, settings);
  }

  // Every minute: codes held by orders that will never be paid go back on sale.
  async function sweep() {
    const reserved = (await store.rows("cafe_vouchers", { f_status: "reserved", limit: 200 })).results;
    for (const voucher of reserved) {
      const order = voucher.order_number ? await findOrder(voucher.order_number) : null;
      if (order && order.status === "pending") {
        await settle(order, { force: true });
        continue;
      }
      if (order && order.status === "paid") {
        await locked(() => store.update("cafe_vouchers", voucher.id, { status: "sold" }));
        continue;
      }
      const age = order && order.created_at ? now() - Date.parse(order.created_at) : Infinity;
      if (order && order.status === "new" && age < STALE_NEW_MS) continue;
      await locked(async () => {
        const current = await findVoucher(voucher.code);
        if (!current || current.status !== "reserved") return;
        if (order && order.voucher === voucher.code && order.status !== "paid") {
          await store.update("cafe_orders", order.id, { status: order.status === "new" ? "failed" : order.status, voucher: null });
        }
        await store.update("cafe_vouchers", current.id, { status: "available", order_number: "" });
        log(`released voucher ${current.id} (order ${voucher.order_number || "none"})`);
      });
    }
    // An order the program stopped working on before it asked IF Pay (a restart in the middle) still holds its
    // code in the unique column: let it go.
    const stuck = (await store.rows("cafe_orders", { f_status: "new", limit: 200 })).results;
    for (const order of stuck) {
      if (now() - Date.parse(order.created_at || 0) < STALE_NEW_MS) continue;
      await locked(async () => {
        const fresh = await findOrder(order.number);
        if (fresh && fresh.status === "new") await releaseVoucher(fresh, "failed");
      });
    }
    store.invalidate();
  }

  return { create, get, lookup, sweep };
}

module.exports = { createOrders, UserError, normalizePhone, normalizeOrderNumber, newOrderNumber, formatAmount, qrImage };
