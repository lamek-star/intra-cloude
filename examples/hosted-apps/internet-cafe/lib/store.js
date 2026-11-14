"use strict";
// The café's data lives in IntraForge, in one database the owner creates and grants to this website (read and
// write only). The website finds it by its four tables and checks their columns, so a missing table or column is
// reported plainly on the setup page instead of failing somewhere in the middle of a sale.

const TABLES = {
  cafe_settings: { key: ["varchar", "text"], value: ["text", "varchar"] },
  cafe_packages: {
    name: ["varchar", "text"],
    minutes: ["integer", "bigint"],
    price: ["decimal", "integer", "bigint"],
    active: ["boolean"],
  },
  cafe_vouchers: {
    code: ["varchar", "text"],
    minutes: ["integer", "bigint"],
    status: ["varchar", "text"],
    order_number: ["varchar", "text"],
  },
  cafe_orders: {
    number: ["varchar", "text"],
    phone: ["varchar", "text"],
    package_name: ["varchar", "text"],
    minutes: ["integer", "bigint"],
    amount: ["decimal", "integer", "bigint"],
    status: ["varchar", "text"],
    pay_request: ["varchar", "text"],
    receipt: ["varchar", "text"],
    voucher: ["varchar", "text"],
    created_at: ["datetime"],
  },
};
// Columns that must refuse a duplicate: the database itself is what stops one code being sold twice.
const UNIQUE = { cafe_vouchers: ["code"], cafe_orders: ["number", "voucher"], cafe_settings: ["key"] };

const DEFAULT_SETTINGS = {
  cafe_name: "Your Internet Café",
  tagline: "Fast Wi-Fi, comfortable PCs and printing — pay with IF Pay.",
  about:
    "A friendly place to work, study and play. Buy Wi-Fi time here on your phone with IF Pay and get online in a minute.",
  address: "",
  hours: "Every day 8:00 – 22:00",
  phone: "",
  whatsapp: "",
  wifi_name: "Cafe-WiFi",
  services:
    "Wi-Fi | Fast internet on your own phone or laptop\nPCs | Desktop computers for work, study and games\nPrinting | Print, copy and scan documents\nSnacks | Drinks and snacks at the counter",
  currency: "IF Credits",
  wallet_url: "",
};

function asList(data) {
  if (Array.isArray(data)) return data;
  if (data && Array.isArray(data.results)) return data.results;
  return [];
}

function createStore(client, { cacheMs = 30000 } = {}) {
  let found = null; // { databaseId, databaseName, tables: { name: id }, problems: [] }
  let cache = { at: 0, settings: null, packages: null };

  async function discover() {
    const problems = [];
    const organizations = asList(await client.get("organizations/"));
    for (const org of organizations) {
      let databases = [];
      try {
        databases = asList(await client.get(`organizations/${org.id}/tenant-databases/`));
      } catch {
        continue;
      }
      for (const db of databases) {
        let tables = [];
        try {
          tables = asList(await client.get(`tenant-databases/${db.id}/tables/`));
        } catch {
          continue;
        }
        const byName = Object.fromEntries(tables.map((t) => [t.name, t]));
        if (!Object.keys(TABLES).some((name) => byName[name])) continue;
        for (const [name, columns] of Object.entries(TABLES)) {
          const table = byName[name];
          if (!table) {
            problems.push(`Table "${name}" is missing.`);
            continue;
          }
          const have = Object.fromEntries((table.columns || []).map((c) => [c.name, c]));
          for (const [column, types] of Object.entries(columns)) {
            if (!have[column]) problems.push(`Table "${name}" needs a column "${column}" (${types[0]}).`);
            else if (!types.includes(have[column].data_type))
              problems.push(`Column "${name}.${column}" should be ${types[0]}, not ${have[column].data_type}.`);
          }
          for (const column of UNIQUE[name] || []) {
            if (have[column] && !have[column].is_unique) problems.push(`Column "${name}.${column}" must be unique.`);
          }
        }
        return {
          databaseId: db.id,
          databaseName: db.name,
          tables: Object.fromEntries(Object.keys(TABLES).map((n) => [n, byName[n] ? byName[n].id : null])),
          problems,
        };
      }
    }
    return { databaseId: null, databaseName: null, tables: {}, problems: ["No database with the café tables was found. Create it and give this website read and write access to it."] };
  }

  async function ensure() {
    if (!found || found.problems.length) found = await discover();
    if (found.problems.length) {
      const err = new Error("The café database is not set up yet.");
      err.setup = found.problems;
      throw err;
    }
    return found;
  }

  async function rows(table, params = {}) {
    const { tables } = await ensure();
    const query = new URLSearchParams(params).toString();
    return client.get(`tables/${tables[table]}/rows/${query ? `?${query}` : ""}`);
  }
  async function insert(table, values) {
    const { tables } = await ensure();
    return client.post(`tables/${tables[table]}/rows/`, values);
  }
  async function update(table, rowId, values) {
    const { tables } = await ensure();
    return client.patch(`tables/${tables[table]}/rows/${rowId}/`, values);
  }

  async function load(force = false) {
    if (!force && cache.settings && Date.now() - cache.at < cacheMs) return cache;
    const settingRows = (await rows("cafe_settings", { limit: 200 })).results;
    const settings = { ...DEFAULT_SETTINGS };
    for (const row of settingRows) {
      if (row.key && Object.prototype.hasOwnProperty.call(DEFAULT_SETTINGS, row.key) && row.value != null) {
        settings[row.key] = String(row.value);
      }
    }
    const packages = (await rows("cafe_packages", { limit: 100, ordering: "minutes" })).results
      .filter((p) => p.active !== false && p.name && Number(p.minutes) > 0 && Number(p.price) > 0)
      .map((p) => ({
        id: p.id,
        name: String(p.name),
        minutes: Number(p.minutes),
        priceMinor: Math.round(Number(p.price) * 100),
      }));
    cache = { at: Date.now(), settings, packages };
    return cache;
  }

  async function availableCount(minutes) {
    const data = await rows("cafe_vouchers", { f_status: "available", f_minutes: String(minutes), limit: 1 });
    return data.count || 0;
  }

  async function setupStatus() {
    try {
      found = await discover();
    } catch (err) {
      return { ready: false, problems: [`IntraForge refused: ${err.message}`] };
    }
    return { ready: found.problems.length === 0, database: found.databaseName, problems: found.problems };
  }

  return { rows, insert, update, load, availableCount, setupStatus, invalidate: () => (cache.at = 0) };
}

module.exports = { createStore, TABLES, UNIQUE, DEFAULT_SETTINGS };
