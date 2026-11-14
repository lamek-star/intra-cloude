# Chapter 3 — The frontend — Routes

Topic for: software engineers. Source: IntraForge Engineering Handbook, Chapter 3 — The frontend.

The signed-in routes (inside `(app)/`) include: `/dashboard`, `/apps` and `/apps/[instanceId]/…` (the business app:
products, inventory, receive, sales, customers, suppliers, warehouses, part numbers), `/orgs/[orgId]/…` (storage,
databases, audit, teams, units, sites, app templates, the developer area), `/buckets/[bucketId]`, `/tables/[tableId]`
(with `/import` and `/analytics`), `/tenant-databases/[dbId]`, `/connected-databases/[id]`, `/dashboards/[id]`,
`/environments/[id]`, `/applications/[id]`, `/service-apps/[appId]/open|settings`, `/movies` and `/movies/[shopId]`,
`/account`, `/backups`, `/health`, `/license`, `/internet`. Public: `/login`, `/register`, `/welcome`,
`/oauth-consent`, `/share/[token]`, `/portal` and `/portal/[shopId]` (the Movie Shop customer portal, phone layout).
