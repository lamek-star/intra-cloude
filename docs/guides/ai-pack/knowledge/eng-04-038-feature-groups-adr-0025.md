# Chapter 4 — Security and permissions — Feature groups (ADR-0025)

Topic for: software engineers. Source: IntraForge Engineering Handbook, Chapter 4 — Security and permissions.

`system/features.py` defines four groups (`business_apps`, `pay_media`, `websites_developer`, `files_data`). Whole URL
modules are wrapped with `features.gated(group, "x.urls")`, so new views are covered automatically; a switched-off
group answers `403 feature_disabled`. Only the Super Administrator (`system.admin`) changes `FeatureSettings`
(`PATCH /api/v1/system/features/`, audited). Hiding `websites_developer` is refused while the internet gate is on.
