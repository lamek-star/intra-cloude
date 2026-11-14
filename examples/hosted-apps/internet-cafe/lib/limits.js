"use strict";
// A small per-address limit on how often the buying and lookup endpoints may be called, so nobody can try order
// numbers by the thousand or fill the orders table. Kept in memory: one app, one process.

function clientAddress(req) {
  // IntraForge's proxy is the only way in; it puts the real address first in X-Forwarded-For.
  const forwarded = String(req.headers["x-forwarded-for"] || "").split(",")[0].trim();
  return forwarded || req.socket.remoteAddress || "unknown";
}

function createRateLimiter({ max, windowMs, now = () => Date.now() }) {
  const hits = new Map();
  return {
    take(key) {
      const t = now();
      const recent = (hits.get(key) || []).filter((at) => t - at < windowMs);
      if (recent.length >= max) {
        hits.set(key, recent);
        return false;
      }
      recent.push(t);
      hits.set(key, recent);
      if (hits.size > 5000) {
        for (const [k, list] of hits) if (!list.some((at) => t - at < windowMs)) hits.delete(k);
      }
      return true;
    },
  };
}

module.exports = { createRateLimiter, clientAddress };
