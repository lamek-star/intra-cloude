# Making the IntraForge web app feel smooth

Measured 2026-11-04 on the 1.5.0 test copy (this PC, Docker, Chrome-based pane). Nothing here is built yet: it is a plan
to pick from (the feature freeze applies; each step is small and can ship on its own).

## Why it feels rigid (measured, not guessed)

| what | measurement | effect you feel |
| --- | --- | --- |
| Requests in a chain | Dashboard: page shell ready at **79 ms**, content at **756 ms**. Its 6 API calls run one after another (csrf → me → organizations → organization → audit → apps). The same calls together take **138 ms** | every page waits ~0.5–0.8 s on a spinner |
| No data cache | 41 pages fetch in `useEffect` on every visit; nothing is kept between pages | going Back, or reopening a page, waits again for data you just saw |
| Whole-page spinner | 52 pages render `<PageLoading />` (a spinner in a 256 px box), then the real layout | the page blanks, then jumps into place |
| No route loading state | 0 `loading.tsx` files | a click shows nothing until the new page's code and data are both there |
| Almost no motion | 2 `animate-` uses; dialogs, banners and list changes appear/vanish instantly | changes feel abrupt rather than connected |
| Buttons wait for the server | Enable/Disable, Allow Pay, Save show the result only after the round trip | a click feels "dead" for 100–300 ms |

The server is not the problem: single API calls answer in 20–110 ms, HTML in 56 ms, 160 KB of JavaScript.

## The fixes, in order of effect per hour of work

### 1. Stop the request chains (no new dependency) — biggest win
Start independent requests together with `Promise.all`, and only chain the ones that truly need an earlier answer.
Dashboard: 756 ms → about 250 ms. Same on the application page (4 sequential awaits) and the org page.
Rule for reviews: two `await api.get` in a row with no data dependency is a bug.

### 2. Cache data between pages: **TanStack Query** (`@tanstack/react-query`, one dependency)
- Pages read through `useQuery(['service-apps'], …)`: revisiting shows the last data **instantly** and refreshes it in
  the background (stale-while-revalidate). Back/forward becomes immediate.
- `queryClient.prefetchQuery` on link hover / focus: the next page's data is often there before the click lands.
- Mutations (`useMutation`) with **optimistic updates** for toggles (Enable, Allow IntraForge Pay, Trash/restore): the
  UI changes on click and rolls back with an error banner if the server refuses.
- Invalidation after a change (`invalidateQueries(['service-apps'])`) replaces today's hand-written `load()` calls.
- Alternative: **SWR** (smaller, fewer features). TanStack Query is the better fit here because of mutations.
- Why a dependency is justified (CLAUDE.md "add dependencies only when needed"): it replaces ~41 hand-written
  fetch/loading/error blocks; record it in an ADR-lite note and pin the exact version.

### 3. Skeletons instead of the spinner, and stable layout (no dependency)
- Replace `PageLoading` with page-shaped skeletons (`PageHeader` + grey card/table rows, `animate-pulse`) so nothing
  jumps when data arrives. Give tables and cards their final heights.
- Add `app/(app)/loading.tsx` (one file) so a click immediately shows the shell while the next page loads.
- Keep the old data on screen while refreshing (TanStack Query's `placeholderData: keepPreviousData`) for filters and
  pagination (audit log, bucket listing).

### 4. Motion that explains change (mostly no dependency)
- **Page transitions: React View Transitions.** React 19.2 has `<ViewTransition>`; Next 16 enables it with
  `experimental: { viewTransition: true }` in `next.config`. A short cross-fade/slide between pages, and shared
  elements (an app card growing into its Settings header). No library; the browser animates. (Skill available:
  `vercel-react-view-transitions`.)
- **Dialogs, toasts, banners:** CSS only — `transition` + `@starting-style` for enter, `transition-behavior:
  allow-discrete` for exit; 150–200 ms, ease-out.
- **Lists that change** (files, members, Trash): `motion` (formerly Framer Motion, `motion/react`) `AnimatePresence` +
  `layout` if CSS is not enough. Optional; only where items are added/removed often.
- Always honour `prefers-reduced-motion` (Tailwind `motion-safe:` / `motion-reduce:`).
- Durations: 120–200 ms for UI feedback, ≤ 300 ms for page changes. Never animate while the user waits on data.

### 5. Feedback on every click (no dependency)
- Buttons show a pending state (`useFormStatus` / `useTransition`) and keep their width (no text jumping to "...").
- `:active` scale (e.g. `active:scale-[0.98]`) and focus rings that animate in, so a press is felt immediately.
- A thin top progress bar during route changes (CSS, or `nextjs-toploader` if you prefer a ready plugin).

### 6. Measure before and after
- Chrome DevTools > Performance (record a click), and the **Web Vitals** extension: watch **INP** (click → paint,
  aim < 200 ms) and **CLS** (layout jumps, aim < 0.1).
- React DevTools Profiler for slow re-renders (large tables: virtualise with `@tanstack/react-virtual` past ~200 rows).
- Lighthouse in the browser for an overall score; keep the JS budget (160 KB today) from growing more than ~30 KB.

## Suggested rollout (each step shippable alone)

| step | size | dependency | where first |
| --- | --- | --- | --- |
| A. Parallel requests | S | none | dashboard, application page, org page |
| B. `loading.tsx` + skeleton components | S | none | `(app)` layout, Apps, bucket, audit |
| C. TanStack Query + optimistic toggles | M | `@tanstack/react-query` | Apps, app Settings, bucket, sharing |
| D. View transitions + CSS dialog motion | S | none (Next flag) | page changes, Modal, ConfirmProvider |
| E. Lists motion / virtualisation | S | optional `motion`, `@tanstack/react-virtual` | bucket files, audit log |

Skills that help when building it: `vercel-react-best-practices` (waterfalls, caching), `vercel-react-view-transitions`,
`vercel-composition-patterns`, `web-design-guidelines` (review), `redesign-existing-projects` (visual polish pass).

## Done so far

**A and B — 432c7c6 (2026-11-04).** Parallel requests on sign-in, dashboard, organization page and application page;
`PageLoading` is a delayed, page-shaped placeholder; `app/(app)/loading.tsx` added. Dashboard, warm, timed from the
first request: organizations and workspaces on screen ~460 ms → ~235 ms; everything including health ~620 → ~490 ms;
6 chained requests → 3 mostly parallel waves. What is slowest now is server-side: `/service-apps/` (asks every app
whether it is alive, 70–400 ms) and `/readyz` — no longer blocking the rest of the page; a cache of the last health
answer would be the next server-side win. Still to do: C (TanStack Query cache + optimistic toggles), D (view
transitions, dialog motion), E (list motion / virtualisation).

**C — 1e38f45, d190da3 (2026-11-04).** `@tanstack/react-query` 5.104.5 (pinned, more than two weeks old). Apps, app
Settings and the dashboard read through a cache that is emptied whenever the signed-in person changes; Enable/Disable
and the application page's IntraForge Pay switch change on the click and roll back on a refusal. Measured in the
test copy: Back to the dashboard 74–107 ms (a full ~700 ms reload before); Apps after the dashboard 36 ms (the
dashboard's health line already filled the Apps cache). A page never opened before is unchanged (~1 s for
Organizations: its code plus its first data) — prefetching on hover is the next lever. Not yet on the cache: the
organization page and most detail pages (they keep their own loading, parallel since A).

The release audit for C found **next 16.3.5 with critical advisories** (RCE in the image optimizer and `use cache`,
SSRF, cache poisoning); upgraded to 16.4.5 in 1e38f45, production audit 0 vulnerabilities. Development-only
advisories remain in eslint/vitest/vite tooling (not shipped).
