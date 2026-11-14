# Chapter 3 — The frontend — Layout

Topic for: software engineers. Source: IntraForge Engineering Handbook, Chapter 3 — The frontend.

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
