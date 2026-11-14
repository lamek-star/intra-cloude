# Lesson 2 — The owner: the Control Center, the licence and people — The Control Center (on the shop PC)

Topic for: shop owners, managers and staff. Source: IntraForge Training Guide, Lesson 2 — The owner: the Control Center, the licence and people.

The **IntraForge Control Center** is the program on the shop PC (the **IntraForge** shortcut on the Desktop). It starts
and stops IntraForge, shows whether everything is healthy, takes backups and restores them, and lets the other PCs in
the shop in.

Screenshot: `screenshots/control-center/1-main.png` — The Control Center's main window

![The Control Center's main window](http://localhost:8765/screenshots/control-center/1-main.png)

- **Start / Stop / Restart** IntraForge. **Open IntraForge** opens it in the browser.
- The checks show green when all is well; a yellow or red line says what to do.
- **Back up now** takes a complete backup (it also runs every night by itself).

### Settings and the shop network

**Settings** shows where IntraForge is installed, whether it starts with Windows, and the **shop network**.

Screenshot: `screenshots/control-center/2-settings.png` — Settings

![Settings](http://localhost:8765/screenshots/control-center/2-settings.png)

To let the other PCs and phones in the shop use IntraForge:

1. In Windows, make sure the shop's Wi-Fi is a **Private** network (Settings > Network & internet > Wi-Fi > your
   network > Network profile type: Private). Never do this on a café or customer Wi-Fi.
2. In the Control Center: **Settings > Shop network > Allow other PCs in this shop...**, tick that this is the shop's
   own network and press **Allow**.

Screenshot: `screenshots/control-center/3-shop-network.png` — Allowing the other PCs in the shop

![Allowing the other PCs in the shop](http://localhost:8765/screenshots/control-center/3-shop-network.png)

3. Each other PC runs **Trust-IntraForge-on-this-PC.cmd** once (from the folder `C:\IntraForgeData\shop-network`) and
   opens the address shown in Settings.

No router in the shop? **Create a shop Wi-Fi from this PC** makes the PC itself the shop's Wi-Fi.

Screenshot: `screenshots/control-center/8-settings-shop-wifi.png` — The shop Wi-Fi made by this PC

![The shop Wi-Fi made by this PC](http://localhost:8765/screenshots/control-center/8-settings-shop-wifi.png)

> If the PC moves to another network, IntraForge still starts for the PC itself. Back on the shop Wi-Fi, press
> **Settings > Shop network > Update the address** so the other PCs can reach it again.

### Backups and restoring

IntraForge backs everything up every night and tests that each backup can be restored. To put a backup back (for
example after a mistake), use **Restore** in the Control Center. Restoring replaces today's data with the backup's, so
it is done only here, never from a browser.

Screenshot: `screenshots/control-center/4-restore.png` — Restoring a backup

![Restoring a backup](http://localhost:8765/screenshots/control-center/4-restore.png)
