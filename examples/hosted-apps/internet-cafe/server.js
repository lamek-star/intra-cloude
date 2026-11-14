"use strict";
// The internet café website: its pages, and a small API the pages call. Run by IntraForge's app runner as
// `node server.js` with PORT, IF_API_URL, IF_API_TOKEN and IF_SITE_NAME set. No outside packages.

const http = require("node:http");
const fs = require("node:fs");
const path = require("node:path");
const { createClient } = require("./lib/intraforge");
const { createStore } = require("./lib/store");
const { createOrders, UserError } = require("./lib/orders");
const { createRateLimiter, clientAddress } = require("./lib/limits");

const PUBLIC_DIR = path.join(__dirname, "public");
const TYPES = {
  ".html": "text/html; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".svg": "image/svg+xml",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".webp": "image/webp",
  ".ico": "image/x-icon",
  ".webmanifest": "application/manifest+json",
};
const SECURITY_HEADERS = {
  "Content-Security-Policy":
    "default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; connect-src 'self'; " +
    "frame-ancestors 'none'; base-uri 'none'; form-action 'self'",
  "X-Content-Type-Options": "nosniff",
  "Referrer-Policy": "no-referrer",
  "Cross-Origin-Opener-Policy": "same-origin",
  "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
};
const MAX_BODY = 8 * 1024;

function log(message) {
  // Never the token, a phone number or a voucher code: only what happened.
  console.log(`${new Date().toISOString()} ${message}`);
}

function send(res, status, body, headers = {}) {
  res.writeHead(status, { ...SECURITY_HEADERS, "Cache-Control": "no-store", ...headers });
  res.end(body);
}
function sendJson(res, status, data) {
  send(res, status, JSON.stringify(data), { "Content-Type": "application/json; charset=utf-8" });
}

function readJson(req) {
  return new Promise((resolve, reject) => {
    if (!/^application\/json\b/i.test(req.headers["content-type"] || "")) {
      reject(new UserError(415, "Send JSON.", "type"));
      return;
    }
    let size = 0;
    const chunks = [];
    req.on("data", (chunk) => {
      size += chunk.length;
      if (size > MAX_BODY) {
        reject(new UserError(413, "Too much data.", "size"));
        req.destroy();
        return;
      }
      chunks.push(chunk);
    });
    req.on("end", () => {
      try {
        const value = JSON.parse(Buffer.concat(chunks).toString("utf8") || "{}");
        if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error("not an object");
        resolve(value);
      } catch {
        reject(new UserError(400, "That was not valid JSON.", "json"));
      }
    });
    req.on("error", reject);
  });
}

function serveStatic(req, res, urlPath) {
  let rel;
  try {
    rel = decodeURIComponent(urlPath);
  } catch {
    return send(res, 400, "Bad request");
  }
  if (rel === "/" || rel === "") rel = "/index.html";
  const file = path.normalize(path.join(PUBLIC_DIR, rel));
  if (!file.startsWith(PUBLIC_DIR + path.sep)) return send(res, 404, "Not found");
  fs.stat(file, (err, stat) => {
    if (err || !stat.isFile()) {
      // Unknown page: the home page (the site uses #sections, not separate pages).
      if (!path.extname(rel)) return serveStatic(req, res, "/index.html");
      return send(res, 404, "Not found", { "Content-Type": "text/plain; charset=utf-8" });
    }
    const type = TYPES[path.extname(file).toLowerCase()] || "application/octet-stream";
    const cache = file.endsWith(".html") ? "no-cache" : "public, max-age=300";
    res.writeHead(200, { ...SECURITY_HEADERS, "Content-Type": type, "Content-Length": stat.size, "Cache-Control": cache });
    if (req.method === "HEAD") return res.end();
    fs.createReadStream(file).pipe(res);
  });
}

function walletUrl(settings, req) {
  if (settings.wallet_url) return settings.wallet_url;
  // Default: IntraForge Pay's wallet page on the same PC, IntraForge's own port (8443).
  const host = String(req.headers["x-forwarded-host"] || req.headers.host || "").replace(/:\d+$/, "");
  if (!/^[A-Za-z0-9.-]+$|^\[[0-9a-fA-F:]+\]$/.test(host)) return "";
  return `https://${host}:8443/apps/pay-1/wallet`;
}

function createApp({ store, orders }) {
  const limits = {
    order: createRateLimiter({ max: 6, windowMs: 60_000 }),
    lookup: createRateLimiter({ max: 10, windowMs: 60_000 }),
    poll: createRateLimiter({ max: 90, windowMs: 60_000 }),
    read: createRateLimiter({ max: 120, windowMs: 60_000 }),
  };

  async function api(req, res, route) {
    const who = clientAddress(req);
    const limited = (name) => {
      if (!limits[name].take(who)) throw new UserError(429, "Too many tries. Wait a minute and try again.", "rate");
    };
    if (req.method === "GET" && route === "info") {
      limited("read");
      const { settings, packages } = await store.load();
      const withStock = await Promise.all(
        packages.map(async (p) => ({
          id: p.id,
          name: p.name,
          minutes: p.minutes,
          price: (p.priceMinor / 100).toFixed(2),
          available: (await store.availableCount(p.minutes)) > 0,
        })),
      );
      const { wallet_url: _hidden, ...publicSettings } = settings;
      return sendJson(res, 200, { cafe: publicSettings, walletUrl: walletUrl(settings, req), packages: withStock });
    }
    if (req.method === "POST" && route === "orders") {
      limited("order");
      const body = await readJson(req);
      const order = await orders.create({ packageId: body.packageId, phone: body.phone });
      log(`order ${order.number} waiting for payment (${order.packageName})`);
      return sendJson(res, 201, order);
    }
    const m = /^orders\/([A-Za-z0-9-]{1,20})$/.exec(route);
    if (req.method === "GET" && m) {
      limited("poll");
      return sendJson(res, 200, await orders.get(m[1]));
    }
    if (req.method === "POST" && route === "lookup") {
      limited("lookup");
      const body = await readJson(req);
      return sendJson(res, 200, await orders.lookup({ number: body.number, phone: body.phone }));
    }
    if (req.method === "GET" && route === "setup") {
      limited("read");
      return sendJson(res, 200, await store.setupStatus());
    }
    throw new UserError(404, "Not found.", "not_found");
  }

  return async function handle(req, res) {
    let url;
    try {
      url = new URL(req.url, "http://site");
    } catch {
      return send(res, 400, "Bad request");
    }
    const m = /^\/api\/(.+)$/.exec(url.pathname);
    if (!m) {
      if (req.method !== "GET" && req.method !== "HEAD") return send(res, 405, "Method not allowed");
      return serveStatic(req, res, url.pathname);
    }
    try {
      await api(req, res, m[1].replace(/\/+$/, ""));
    } catch (err) {
      if (err instanceof UserError) return sendJson(res, err.status, { error: err.code, message: err.message });
      if (err && err.setup) {
        return sendJson(res, 503, { error: "setup", message: "The website is not set up yet.", problems: err.setup });
      }
      log(`error: ${err && err.message ? err.message : err}`);
      return sendJson(res, 500, { error: "server", message: "Something went wrong. Please try again or ask at the counter." });
    }
  };
}

function main() {
  const client = createClient({ baseUrl: process.env.IF_API_URL, token: process.env.IF_API_TOKEN });
  const store = createStore(client);
  const orders = createOrders({ store, client, log });
  const server = http.createServer(createApp({ store, orders }));
  server.headersTimeout = 15_000;
  server.requestTimeout = 30_000;
  const port = Number(process.env.PORT || 3000);
  server.listen(port, () => log(`internet café website listening on ${port}`));
  const sweep = () => orders.sweep().catch((err) => log(`sweep: ${err.message}`));
  setTimeout(sweep, 5_000);
  setInterval(sweep, 60_000).unref();
  for (const signal of ["SIGTERM", "SIGINT"]) process.on(signal, () => server.close(() => process.exit(0)));
}

if (require.main === module) main();

module.exports = { createApp, walletUrl };
