# Chapter 6 — The shop kit: build, install, upgrade, operate — Names on this PC, and the browser certificate

Topic for: software engineers. Source: IntraForge Engineering Handbook, Chapter 6 — The shop kit: build, install, upgrade, operate.

- `Set-IntraForgeNetwork.ps1 -Mode Names` (Control Center > Settings > Shop network > Open by name on this PC):
  writes the app names to the hosts file as 127.0.0.1, writes `names.caddy`, adds the names to `SHOP_TLS_HOSTNAMES`,
  `ALLOWED_HOSTS` (`.lan`) and `CSRF_TRUSTED_ORIGINS` (`https://*.lan`), and sets `SHOP_NAMES_PORT=443`. The proxy
  has one extra port line `${SHOP_BIND_V4}:${SHOP_NAMES_PORT:-8443}:443`; unset, it equals the first line and compose
  merges it away. `-Mode ThisPC` undoes everything. No firewall rule: loopback only.
- The Control Center's **Browser certificate** card (`BrowserCertificate` in `ControlCenter.cs`) reads Caddy's local
  root from the proxy, accepts only a self-signed `Caddy Local Authority` root, and adds it to the Windows user's Root
  store; Windows asks the person to confirm.
- **Owner card:** `manage.py super_administrators list|grant|revoke` and `manage.py approver_account create`
  (the phone approver, ADR-0026) are run from the Control Center, so only someone at the PC can use them.
