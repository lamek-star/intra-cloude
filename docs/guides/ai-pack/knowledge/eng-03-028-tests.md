# Chapter 3 — The frontend — Tests

Topic for: software engineers. Source: IntraForge Engineering Handbook, Chapter 3 — The frontend.

- `npm test` — Vitest unit tests (`*.test.ts(x)` next to the code).
- `npm run e2e` — Playwright against a running stack (`e2e/`: auth, tenant isolation, the Spare Parts cashier,
  flagship and accessibility journeys, app platform).
- `npm run lint`, `npx tsc --noEmit` (after `npm run build`), `npm audit --omit=dev --audit-level=high`.
