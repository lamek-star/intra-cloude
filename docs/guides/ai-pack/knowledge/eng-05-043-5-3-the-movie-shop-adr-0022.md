# Chapter 5 — Applications on IntraForge — 5.3 The Movie Shop (ADR-0022)

Topic for: software engineers. Source: IntraForge Engineering Handbook, Chapter 5 — Applications on IntraForge.

- **Catalogue** (`models.py`, `scanning.py`): only metadata lives in IntraForge. The films stay on the shop's drives;
  covers are ordinary files in the shop's `movie-covers` bucket. Every folder in a library becomes a category.
- **The media agent** (`scripts/shop-kit/media-agent/MediaAgent.cs`) is a small Windows program on the shop PC. It
  reports drives, scans library folders and copies sold titles onto the customer's USB drive. IntraForge checks every
  value it sends (`scanning.py`) — nothing is trusted because it came from our own agent.
- **Counter sales** (`sales.py`): a cart for one customer, paid through IntraForge Pay or cash, then copied by the agent;
  each title's copy progress is tracked; a failed copy can be retried.
- **The customer portal** (`portal.py`, `portal_views.py`, frontend `components/portal/`): customers sign up on the
  shop Wi-Fi (`https://movies.lan:8443` through the shop-names service), wait for approval, browse and order, and
  collect points (welcome, referral, birthday, every Nth title free). Ads (`ads.py`) show on the portal.
- Capabilities: `movies.read`, `movies.sell`, `movies.manage`.
