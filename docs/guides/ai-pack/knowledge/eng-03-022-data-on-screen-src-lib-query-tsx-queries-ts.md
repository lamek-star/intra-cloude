# Chapter 3 — The frontend — Data on screen — `src/lib/query.tsx`, `queries.ts`

Topic for: software engineers. Source: IntraForge Engineering Handbook, Chapter 3 — The frontend.

TanStack Query caches page data in the tab's memory: a page seen before shows at once and refreshes in the background
(30 s stale time). A 403/404 is never retried. The cache is cleared whenever the signed-in person changes
(`auth-context.tsx`), so one person's data never shows to another.
