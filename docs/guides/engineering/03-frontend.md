# Chapter 3 — The frontend

## Layout

```
apps/frontend/
  src/app/                 Next.js App Router: one folder per route
    (app)/                 every signed-in screen, wrapped by layout.tsx -> AppShell (sidebar, header, palette)
    login/ register/ welcome/ oauth-consent/ share/[token]/ portal/   public screens
    globals.css            design tokens (colour variables, light and dark), Tailwind v4 theme
  src/components/          shared components; ui.tsx is the component kit
    business/              the built-in Spare Parts / Pharmacy screens (BusinessApp, SellStock, ReceiveStock, Labels...)
    movies/  portal/       Movie Shop owner screens and the customer portal
  src/lib/                 API client, types, query layer, auth, helpers (each with its .test.ts)
  e2e/                     Playwright browser tests
```

The app is **client-rendered**: pages are React client components that call the API in the browser through the same
Caddy origin, so there is no CORS and no server-side data access in Next.js.

## Talking to the API — `src/lib/api.ts`

- `api.get / post / patch / delete` call `/api/v1/...` with `credentials: "include"` (the session cookie).
- Before the first write, `ensureCsrfCookie()` calls `GET /auth/csrf/`; every mutating call sends `X-CSRFToken`.
- Errors become `ApiError` with `status`, the backend's `code` and `requestId`. `ErrorBanner` shows a friendly message
  and offers "View technical details".
- The response types (`User`, `Organization`, `Bucket`, `DBTable`…) live in the same file — keep them in step with the
  serializers (Reference A lists the endpoints).

## Data on screen — `src/lib/query.tsx`, `queries.ts`

TanStack Query caches page data in the tab's memory: a page seen before shows at once and refreshes in the background
(30 s stale time). A 403/404 is never retried. The cache is cleared whenever the signed-in person changes
(`auth-context.tsx`), so one person's data never shows to another.

## Signing in — `src/lib/auth-context.tsx`

`useAuth()` exposes `user`, `login` (which may answer `mfaRequired`), `verifyMfa`, `signInWithPasskey`, `register`,
`logout`, `refresh`. Passkeys use WebAuthn through `src/lib/passkeys.ts`. After a password reset the backend refuses
everything except changing the password; `PasswordForm` handles that screen.

## The component kit — `src/components/ui.tsx`

Use these instead of raw elements so every screen looks and behaves the same: `Button` (primary, secondary, danger,
ghost), `LinkButton`, `Input`, `Textarea`, `Select`, `Checkbox`, `Label`, `Card`, `Badge`, `Spinner`, `PageLoading`,
`EmptyState`, `ErrorBanner`, `CopyButton`, `SecretReveal` (a secret shown once), `PageHeader`, `Table`/`THead`/`Th`/
`Td`/`TRow`, `Modal` (focus trap via `use-dialog-a11y.ts`), `StatCard`. Confirmations go through `ConfirmProvider`.

## Design rules

- **Colours are tokens** (`--color-brand-600`, `--color-navy`, …) defined in `globals.css` and redefined for dark mode
  under `html[data-theme="dark"]`. `ThemeToggle` and `lib/theme.ts` store the choice (system / light / dark) in the
  browser. Never hard-code a hex colour in a component. The brand is described in `DESIGN.md`.
- **Icons are `lucide-react` components, never emoji** (emoji render differently across fonts and platforms).
- Accessible by default: labels on every input, visible focus rings, `Modal` traps focus, motion respects
  `prefers-reduced-motion` (`use-reduced-motion.ts`).
- The screen hiding a button is a courtesy; the server's capability check is the lock. Always handle a 403 with a
  clear "you don't have permission" message.

## Routes

The signed-in routes (inside `(app)/`) include: `/dashboard`, `/apps` and `/apps/[instanceId]/…` (the business app:
products, inventory, receive, sales, customers, suppliers, warehouses, part numbers), `/orgs/[orgId]/…` (storage,
databases, audit, teams, units, sites, app templates, the developer area), `/buckets/[bucketId]`, `/tables/[tableId]`
(with `/import` and `/analytics`), `/tenant-databases/[dbId]`, `/connected-databases/[id]`, `/dashboards/[id]`,
`/environments/[id]`, `/applications/[id]`, `/service-apps/[appId]/open|settings`, `/movies` and `/movies/[shopId]`,
`/account`, `/backups`, `/health`, `/license`, `/internet`. Public: `/login`, `/register`, `/welcome`,
`/oauth-consent`, `/share/[token]`, `/portal` and `/portal/[shopId]` (the Movie Shop customer portal, phone layout).

## Adding a screen

1. Create `src/app/(app)/<route>/page.tsx` as a client component; use `PageHeader` and the kit.
2. Add the response type to `lib/api.ts` and a query hook (or `useQuery` inline) keyed by the resource id.
3. Handle loading (`PageLoading`), empty (`EmptyState`), error (`ErrorBanner`) and 403 states.
4. Add it to the sidebar (`AppShell.tsx`) or the command palette (`CommandPalette.tsx`) if people need to find it.
5. Add a Vitest test for any logic in `lib/`, and a Playwright spec for a whole workflow.

## Tests

- `npm test` — Vitest unit tests (`*.test.ts(x)` next to the code).
- `npm run e2e` — Playwright against a running stack (`e2e/`: auth, tenant isolation, the Spare Parts cashier,
  flagship and accessibility journeys, app platform).
- `npm run lint`, `npx tsc --noEmit` (after `npm run build`), `npm audit --omit=dev --audit-level=high`.
