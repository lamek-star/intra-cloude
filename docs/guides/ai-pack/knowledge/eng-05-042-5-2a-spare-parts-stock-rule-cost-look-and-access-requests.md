# Chapter 5 — Applications on IntraForge — 5.2a Spare Parts: stock rule, cost, look and access requests

Topic for: software engineers. Source: IntraForge Engineering Handbook, Chapter 5 — Applications on IntraForge.

- **One stock rule** (`src/server/standalone/repos/stockRule.ts`, `AVAILABLE_SQL`, `NEEDS_ORDERING_SQL`) feeds the
  Low stock tile, the filter, the lowStock report and `stockStatus`; the browser never does stock arithmetic.
- **Cost on receipt** (`src/server/domain/purchasing.ts`, `averagedCost`): weighted average; zero-cost lines and other
  currencies are skipped; audited as `product.cost_change`.
- **Look** (`src/ui/glass.tsx`, `src/app/globals.css`): colours are CSS variables, dark under `:root`, light under
  `[data-theme="light"]` (`localStorage` key `sp-theme`); `CountUp`, `SalesChart` (`/reports/daily-sales`), all
  respecting `prefers-reduced-motion`.
- **Sign-out on IntraForge** (`src/ui/session.tsx`): the status goes to "loading", never to this app's own sign-in,
  until the server says where to go (e2e test "on IntraForge, sign-out goes straight...").
- **Access requests** (platform mode): `src/server/platform/accessRequests.ts` (gateway), `app.accessRequests`,
  routes `GET /access-requests` and `POST /access-requests/:id/decide` (`users.manage`), and `src/ui/accessRequests.tsx`
  on the Users page. IntraForge makes the real decision.
- Server messages are translated by `src/ui/serverMessages.ts`: every new server message needs a `srv.*` key in all
  four languages (the test `server-messages.test.ts` fails otherwise).
