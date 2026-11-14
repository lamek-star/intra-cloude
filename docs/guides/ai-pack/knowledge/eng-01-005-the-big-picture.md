# Chapter 1 — Architecture — The big picture

Topic for: software engineers. Source: IntraForge Engineering Handbook, Chapter 1 — Architecture.

```
 Shop staff (browser)      Customers' phones (portal)      Other programs (bearer token)
         |  https://localhost:8443 or https://<shop name>:8443        |
         v                                                             v
 +-------------------------------------------------------------------------------+
 | proxy (Caddy 2): HTTPS, security headers, routing by path; :8445 hosted sites |
 +---+-------------------+-----------------------+-------------------------------+
     | pages             | /api/* /healthz       | /apps/pay-1, /apps/spare-parts, /apps/pharmacy
     v                   v                       v
 +----------+   +-------------------+   +------------------------------------+
 | frontend |   | backend (Django,  |   | service applications (own images): |
 | Next.js  |   | gunicorn)         |<--| Pay (FastAPI), Spare Parts and     |
 +----------+   +----+---------+----+   | Pharmacy (Next.js) — internal API  |
                     |         |        +------------------------------------+
        +------------+    +----+------------------+--------------+
        v                 v                       v              v
 +--------------+  +----------------+       +--------+     +-----------+    +--------------+
 | postgres-    |  | postgres-      |       | valkey |     | object-   |    | worker, beat |
 | control      |  | tenant         |       | cache, |     | storage   |    | (Celery)     |
 | the catalog  |  | business data, |       | queue  |     | (MinIO)   |    | runner (apps)|
 +--------------+  | schema per org |       +--------+     +-----------+    +--------------+
                   +----------------+
```

Everything runs as Docker containers on one machine, on a private Docker network **with no route to the internet**.
Only the proxy publishes ports, and by default only on the loopback address (`127.0.0.1` and `::1`); opening it to the
shop network is a deliberate step (Control Center > Shop network, `Set-IntraForgeNetwork.ps1`).
