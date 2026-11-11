# ADR-0021 — The shop's own names: a name server on the shop PC

Status: accepted; implemented in 1.5.1 (shop kit).
Date: 2026-11-08. Builds on ADR-0012 (Windows deployment), ADR-0020 (hosted sites under their own name) and the shop
network (`Set-IntraForgeNetwork.ps1`). Adds one container image; no new datastore or identity provider.

## Problem

On the shop network, people open IntraForge as `https://192.168.1.20:8443` or `https://shop-pc:8443` and an app as
`https://shop-pc:8443/apps/pharmacy/`. The owner wants each app to have its own name. A name only works if every
device can look it up, and phones cannot edit a hosts file: the shop needs a name server that the devices ask.

## Decision

1. **Names.** Every name ending in the shop's domain is the shop PC. The domain is `lan` by default and can be a name
   under the shop's own domain (`shop.harmongt.uk`); `.local` (multicast DNS) and addresses are refused. IntraForge is
   `intraforge.<domain>`; each app the installation runs gets its name: `spare-parts`, `pharmacy`, `pay` (the first Pay
   slot). The name's front page redirects to the app's page (`https://pharmacy.lan:8443/` →
   `/apps/pharmacy/`), so the apps keep running under their path on IntraForge's own origin, with the same cookie
   isolation as before (ADR-0018); nothing about routing behind the name changes. Hosted sites' own names
   (ADR-0020, port 8445) resolve through the same wildcard.
2. **Router network: CoreDNS** (`coredns/coredns:1.15.0`, Apache-2.0, pinned, bundled offline like every other image)
   runs as the compose service `names`, only when the shop network is on with a router (`COMPOSE_PROFILES=names` in
   `.env`). Its configuration is generated: a `template` answers every A query in the shop's domain with the PC's
   address (and no AAAA answer, so phones don't wait for one); everything else is forwarded to the name servers this
   PC itself uses (the router). It listens on the PC's shop-network address only, port 53 UDP and TCP; the Windows
   Firewall admits the local subnet on Private networks and blocks Public ones, like port 8443. It runs read-only,
   unprivileged, with only `NET_BIND_SERVICE`. **The owner sets the router's DHCP DNS server to the shop PC once**;
   the Control Center and the script say so.
3. **Shop Wi-Fi (hotspot): no extra server.** Windows' hotspot (Internet Connection Sharing) already runs the name
   service for its clients on 192.168.137.1:53 and answers from the PC's own resolver, which includes the hosts file;
   CoreDNS could not listen there anyway. The names are written to a marked block of the hosts file (only that block
   is ever touched). The same block is written in router mode too, so the shop PC itself finds the names.
4. **Never a reason not to start.** If the PC no longer has the recorded address (the router gave it another),
   `Start-IntraForgeShop.ps1` starts everything without the name server and logs it; "Update the address" rewrites
   the configuration. Switching to this-computer-only stops the service and removes the hosts block; uninstall
   removes the block too.
5. Django: `ALLOWED_HOSTS` gains `.<domain>`, `CSRF_TRUSTED_ORIGINS` gains `https://*.<domain>:<port>`, the proxy's
   certificate names the hosts (Caddy's own CA, which staff PCs already trust). A passkey (ADR-0019) works at
   `intraforge.<domain>`, a real domain name, unlike a bare PC name.

### Internet names: built in, switched off

The owner wants the same apps under `harmongt.uk` on the internet later. That stays **off**: the internet gate
(ADR-0020 decision 4) serves published hosted sites only, never IntraForge, its API, its sign-in or a service app,
and this ADR does not change that. When it is wanted, the app names here map one to one (`pharmacy.lan` ↔
`pharmacy.harmongt.uk`) through the existing Cloudflare tunnel. Before anyone switches it on, a separate decision
must cover at least: passkey-only sign-in for every administrator (ADR-0019), the internet-gateway hardening
(`docs/deployment/INTERNET_GATEWAY.md`: tighter auth throttle, MFA on administrative grants), which apps may be
reachable and by whom, and the customer wallet's exposure. Until then no code path publishes an app or the sign-in.

## Consequences

- Phones and PCs open `https://pharmacy.lan:8443` once the router hands out the shop PC as name server, or at once
  on the PC's own Wi-Fi. The port stays in the address (8443 is IntraForge's port; 443 may be taken on a shop PC).
- While the shop PC is off, devices that use it as their name server cannot look up any name (internet browsing on
  them stops too). The guide says to keep the PC on; a router that allows a second DNS server should not be given
  one, since devices pick either server and the names would work only some of the time.
- Not verified on hardware here: a phone using the router-handed name server, and ICS answering hotspot clients from
  the hosts file. Verified here: CoreDNS 1.15.0 with the generated configuration answering on this PC's own network
  address over UDP and TCP and forwarding other names; the proxy redirecting `pharmacy.lan` to the Pharmacy; the
  generators and the hosts-file editing (Pester).
