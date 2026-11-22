# Chapter 7 — The other repositories — 7.3 Licensing tool (vendor only)

Topic for: software engineers. Source: IntraForge Engineering Handbook, Chapter 7 — The other repositories.

`scripts/licensing/intraforge-license.py` makes serial numbers and activation codes with the vendor's private key, using
the same rules as `licensing/codes.py`. The private key (`licensing/private-key.pem`) and the serial registry stay in
the private `licensing` folder on the vendor's machine: never in a repository, a kit or a shop PC.
