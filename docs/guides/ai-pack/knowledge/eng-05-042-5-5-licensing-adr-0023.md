# Chapter 5 — Applications on IntraForge — 5.5 Licensing (ADR-0023)

Topic for: software engineers. Source: IntraForge Engineering Handbook, Chapter 5 — Applications on IntraForge.

A new installation has a 30-day trial. Then it needs a **serial number** and an **activation code** made for that PC's
code (`licensing/codes.py`, Ed25519-signed by the vendor tool `scripts/licensing/intraforge-license.py`). Without a
valid licence, `LicenceMiddleware` makes IntraForge **read-only**: anything that would change data is refused except
signing in and out, consent screens, activating the licence and the internal service API. Data is never lost. The
private key and the serial registry live only with the vendor — never in a repository, kit or shop PC.
