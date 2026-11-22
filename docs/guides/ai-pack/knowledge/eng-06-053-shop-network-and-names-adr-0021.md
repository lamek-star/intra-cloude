# Chapter 6 — The shop kit: build, install, upgrade, operate — Shop network and names (ADR-0021)

Topic for: software engineers. Source: IntraForge Engineering Handbook, Chapter 6 — The shop kit: build, install, upgrade, operate.

By default IntraForge answers only on `127.0.0.1`/`::1`. **Control Center > Shop network** (or
`Set-IntraForgeNetwork.ps1`) binds the proxy to the PC's LAN address, opens the firewall for the private network and
starts the `names` service (CoreDNS, compose profile `names`), which answers the shop's names (`myshop.lan`,
`movies.lan`) with the PC's address and passes everything else to the router. Point the router's DNS at the PC (or set
it per device) so phones find `movies.lan`.

**When the PC changes network** (for example to a phone hotspot), the saved LAN address no longer exists and Docker
refuses to bind port 53 on it. The start and upgrade scripts then use the `without-names` profile so IntraForge still
starts; **Shop network > Update the address** fixes it. (In Windows PowerShell, setting `$env:COMPOSE_PROFILES=''`
*deletes* the variable, so an explicit profile name is used instead of an empty one.)
