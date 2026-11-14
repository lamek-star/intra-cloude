# Chapter 5 — Applications on IntraForge

Topic for: software engineers. Source: IntraForge Engineering Handbook, Chapter 5 — Applications on IntraForge.

IntraForge runs business applications in three different ways. Know which one you are touching:

| Kind | Example | Code lives in | Data lives in |
|---|---|---|---|
| **Built-in app (App Platform)** — defined as data, run by one generic engine | Spare Parts / Inventory & Sales, Pharmacy, Repair Shop, Rentals | `app_platform/` + `frontend/src/components/business/` | The organization's tenant schema |
| **Service application** — a separate program with its own image | IntraForge Pay, the Spare Parts shop app, the Pharmacy app | Its own repository; `service_apps/` is IntraForge's side | Its own schema in the tenant database (+ IntraForge storage) |
| **Feature app** — a normal IntraForge app with its own models | Movie Shop, hosted websites | `movie_shop/`, `sites/` | The control database (metadata) + object storage; films stay on the shop's drives |
