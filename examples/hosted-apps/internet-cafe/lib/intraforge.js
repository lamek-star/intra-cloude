"use strict";
// The website's only way to IntraForge: its own address and token, given by IntraForge when the app starts
// (IF_API_URL, IF_API_TOKEN). The token never leaves this server: no page, answer or log line contains it.

class IntraForgeError extends Error {
  constructor(status, message, body) {
    super(message);
    this.status = status;
    this.body = body;
  }
}

function detailOf(body) {
  if (!body || typeof body !== "object") return "";
  if (typeof body.detail === "string") return body.detail;
  if (body.error && typeof body.error.message === "string") return body.error.message;
  const first = Object.values(body)[0];
  if (Array.isArray(first) && typeof first[0] === "string") return first[0];
  if (typeof first === "string") return first;
  return "";
}

function createClient({ baseUrl, token, fetchImpl = globalThis.fetch, timeoutMs = 15000 }) {
  if (!baseUrl || !token) throw new Error("IF_API_URL and IF_API_TOKEN are not set: start the app from IntraForge.");
  // IntraForge hands over its API address (".../api/v1"); a bare server address works too.
  const root = baseUrl.replace(/\/+$/, "").replace(/\/api\/v1$/, "");

  async function call(method, path, body) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    let response;
    try {
      response = await fetchImpl(`${root}/api/v1/${path}`, {
        method,
        headers: {
          Authorization: `Bearer ${token}`,
          Accept: "application/json",
          ...(body === undefined ? {} : { "Content-Type": "application/json" }),
        },
        body: body === undefined ? undefined : JSON.stringify(body),
        signal: controller.signal,
      });
    } catch {
      throw new IntraForgeError(503, "IntraForge could not be reached.", null);
    } finally {
      clearTimeout(timer);
    }
    const text = await response.text();
    let data = null;
    if (text) {
      try {
        data = JSON.parse(text);
      } catch {
        data = null;
      }
    }
    if (!response.ok) {
      throw new IntraForgeError(response.status, detailOf(data) || `IntraForge answered ${response.status}.`, data);
    }
    return data;
  }

  return {
    get: (path) => call("GET", path),
    post: (path, body) => call("POST", path, body ?? {}),
    patch: (path, body) => call("PATCH", path, body),
  };
}

module.exports = { createClient, IntraForgeError };
