# Chapter 2 — The backend — Rate limits

Topic for: software engineers. Source: IntraForge Engineering Handbook, Chapter 2 — The backend.

`DEFAULT_THROTTLE_RATES`: anonymous 30/min, signed-in 300/min, **auth 10/min** (sign-in, register, MFA — intentional;
never loosen it, space tests instead), import 20/min per organization. Counters live in Valkey (`CACHES`), so all
gunicorn workers share one budget.
