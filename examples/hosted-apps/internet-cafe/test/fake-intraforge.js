"use strict";
// An in-memory stand-in for the parts of IntraForge the website uses (organizations, databases, tables, rows,
// IF Pay payment requests), answering the way the real API does -- including a 400 for a duplicate value in a
// unique column. Tests drive payments with markPaid / expire.

const crypto = require("node:crypto");
const { TABLES, UNIQUE } = require("../lib/store");
const { IntraForgeError } = require("../lib/intraforge");

function createFake({ tables = TABLES, unique = UNIQUE } = {}) {
  const db = { id: "db-1", name: "Internet Cafe" };
  const meta = {};
  const data = {};
  for (const [name, columns] of Object.entries(tables)) {
    const id = `t-${name}`;
    meta[name] = {
      id,
      name,
      columns: [
        { name: "id", data_type: "uuid", is_unique: true },
        ...Object.entries(columns).map(([col, types]) => ({
          name: col,
          data_type: types[0],
          is_unique: (unique[name] || []).includes(col),
        })),
      ],
    };
    data[id] = [];
  }
  const payments = new Map();
  const calls = [];
  const fake = { calls, payments, data, meta, failPayWith: null, delayMs: 0 };

  function tableById(id) {
    return Object.values(meta).find((t) => t.id === id);
  }
  // The same value rules as IntraForge's rows API (databases/values.py) for the types the café uses.
  function checkValues(table, values) {
    for (const [name, value] of Object.entries(values)) {
      const col = table.columns.find((c) => c.name === name);
      if (!col) throw new IntraForgeError(400, `unknown column: ${name}`, {});
      if (value == null) continue;
      if (col.data_type === "datetime" && !/^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(Z|\+00:00)?$/.test(String(value))) {
        throw new IntraForgeError(400, `expected an ISO datetime string, got '${value}'`, {});
      }
      if (col.data_type === "integer" && !Number.isInteger(Number(value))) {
        throw new IntraForgeError(400, `expected an integer, got '${value}'`, {});
      }
    }
  }
  function checkUnique(table, row, selfId) {
    for (const col of table.columns) {
      if (!col.is_unique || col.name === "id" || row[col.name] == null || row[col.name] === "") continue;
      if (data[table.id].some((r) => r.id !== selfId && r[col.name] === row[col.name])) {
        throw new IntraForgeError(400, "a row with this value already exists (the value must be unique)", {});
      }
    }
  }

  async function handle(method, path, body) {
    calls.push({ method, path, body });
    if (fake.delayMs) await new Promise((r) => setTimeout(r, fake.delayMs));
    const url = new URL(path, "http://x/");
    const p = url.pathname.replace(/^\//, "");
    if (method === "GET" && p === "organizations/") return { results: [{ id: "org-1", name: "Cafe" }] };
    if (method === "GET" && p === "organizations/org-1/tenant-databases/") return [db];
    if (method === "GET" && p === `tenant-databases/${db.id}/tables/`) return Object.values(meta);
    let m = /^tables\/([^/]+)\/rows\/$/.exec(p);
    if (m) {
      const table = tableById(m[1]);
      if (!table) throw new IntraForgeError(404, "Not found.", {});
      if (method === "GET") {
        let rows = data[table.id].slice();
        for (const [key, value] of url.searchParams) {
          if (!key.startsWith("f_")) continue;
          const col = key.slice(2);
          rows = rows.filter((r) => String(r[col] ?? "") === value);
        }
        const ordering = url.searchParams.get("ordering");
        if (ordering) rows.sort((a, b) => (a[ordering] > b[ordering] ? 1 : -1));
        const limit = Number(url.searchParams.get("limit") || 50);
        const offset = Number(url.searchParams.get("offset") || 0);
        return { count: rows.length, limit, offset, results: rows.slice(offset, offset + limit).map((r) => ({ ...r })) };
      }
      if (method === "POST") {
        checkValues(table, body);
        const row = { id: crypto.randomUUID(), ...body };
        checkUnique(table, row, null);
        data[table.id].push(row);
        return { ...row };
      }
    }
    m = /^tables\/([^/]+)\/rows\/([^/]+)\/$/.exec(p);
    if (m && method === "PATCH") {
      const table = tableById(m[1]);
      const row = data[table.id].find((r) => r.id === m[2]);
      if (!row) throw new IntraForgeError(404, "Not found.", {});
      checkValues(table, body);
      checkUnique(table, { ...row, ...body }, row.id);
      Object.assign(row, body);
      return { ...row };
    }
    if (method === "POST" && p === "pay/payment-requests/") {
      if (fake.failPayWith) throw new IntraForgeError(fake.failPayWith, "refused", {});
      const id = crypto.randomUUID();
      const request = {
        id,
        status: "pending",
        amount_minor: body.amountMinor,
        reference: body.reference,
        external_id: body.externalId,
        receipt_number: null,
        expires_at: new Date(Date.now() + 5 * 60_000).toISOString(),
        code: `IFPAY1.${id.replace(/-/g, "")}.sig`,
        // Like IF Pay: a ready image address.
        qr_svg: `data:image/svg+xml;base64,${Buffer.from("<svg xmlns='http://www.w3.org/2000/svg'/>").toString("base64")}`,
      };
      payments.set(id, request);
      return { ...request };
    }
    m = /^pay\/payment-requests\/([^/]+)\/$/.exec(p);
    if (m && method === "GET") {
      const request = payments.get(m[1]);
      if (!request) throw new IntraForgeError(404, "No such payment request.", {});
      const { code: _code, qr_svg: _qr, ...rest } = request;
      return rest;
    }
    throw new IntraForgeError(404, `fake: no route ${method} ${p}`, {});
  }

  fake.client = {
    get: (path) => handle("GET", path),
    post: (path, body) => handle("POST", path, body ?? {}),
    patch: (path, body) => handle("PATCH", path, body),
  };
  fake.rows = (name) => data[meta[name].id];
  fake.add = (name, row) => {
    const full = { id: crypto.randomUUID(), ...row };
    data[meta[name].id].push(full);
    return full;
  };
  fake.markPaid = (externalId, receipt = "R-000123") => {
    for (const request of payments.values()) {
      if (request.external_id === externalId) Object.assign(request, { status: "paid", receipt_number: receipt });
    }
  };
  fake.expire = (externalId) => {
    for (const request of payments.values()) if (request.external_id === externalId) request.status = "expired";
  };
  return fake;
}

module.exports = { createFake };
