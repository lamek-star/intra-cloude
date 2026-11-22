# Lesson 2 — The owner: the Control Center, the licence and people — Opening IntraForge without a warning, and by name

Topic for: shop owners, managers and staff. Source: IntraForge Training Guide, Lesson 2 — The owner: the Control Center, the licence and people.

**"Your connection is not private"** means this PC does not trust IntraForge's own certificate yet. It is not a fault
and not the network. Fix it once: **Control Center > Settings > Browser certificate > Trust IntraForge on this PC**,
choose **Yes** in Windows' question, then close and reopen the browser. It comes back only if IntraForge was removed
with its data and installed again (that makes a new certificate): trust it again. The shop's other PCs and phones use
`Trust-IntraForge-on-this-PC.cmd` from the shop-network folder.

**Opening by name instead of `https://localhost:8443`:** **Control Center > Settings > Shop network > Open by name on
this PC**. Windows asks for administrator rights once. Then IntraForge opens at **https://intraforge.lan** and each app
at its own name, such as **https://spare-parts.lan** and **https://pay.lan**, with no port number. The old address
keeps working. Each name is its own address, so you sign in once on each. **Stop using the names** goes back.
