# User Guide — IntraForge

Status: VERIFIED (the frontend described below was built and the flows in
this guide were driven end-to-end against the real backend through the
live Caddy proxy — session-cookie login, CSRF-protected mutations, file
upload/download, and the database builder's row API all confirmed
working, not just assumed from the code)
Last updated: 2026-08-10

This is the end-user companion to
[docs/deployment/LOCAL_DEPLOYMENT.md](../deployment/LOCAL_DEPLOYMENT.md)
(which covers getting the stack running) — this document covers what to
do once it's up: how to sign in and use the web interface, and where to
find the platform's other real, tested features that don't have a
screen yet.

## 1. Quick Start

| | |
|---|---|
| Open | `https://localhost:8443/login` |
| Demo email | `demo@example.com` |
| Demo password | `Demo-Password-123!` |

The first time you open the URL, your browser will warn about the
certificate — this deployment signs its own HTTPS certificate (Caddy's
local CA, `infrastructure/proxy/Caddyfile`) rather than using a public
one, appropriate for a local/LAN-first deployment
(`docs/deployment/LOCAL_DEPLOYMENT.md` Section 6). Click through
**Advanced → Proceed**. It only appears once per browser.

## 2. How It's Organized

Everything you create lives inside exactly one thing above it, in this
order:

```
Organization            e.g. "Acme Corp" — owns members and permissions
  └─ Workspace           e.g. "Engineering" — groups projects
      └─ Project          e.g. "Demo Project" — where work happens
          ├─ Storage bucket    holds files
          └─ Database          holds tables
```

A bucket or a database always belongs to exactly one project; a project
always belongs to exactly one workspace; a workspace always belongs to
exactly one organization.

## 3. Sign In

Use the demo account above, or register your own from the sign-in
page's "Create one" link. A freshly registered account starts with no
organizations — you'll create your first one from an empty state.

If a login asks for a 6-digit code, that account has two-factor
authentication enabled (Section 6) — the demo account doesn't.

### Passkeys: sign in with your phone

**Your account > Passkeys > Add a passkey.** Enter your password (and your authenticator code, if two-step
sign-in is on); the browser then shows a QR code. Scan it with your phone's camera and confirm with your
fingerprint or face. From then on, **Sign in with a passkey** on the sign-in page does the same: scan, confirm,
and you are in -- no password, and no authenticator code (the passkey counts as both).

- Bluetooth must be on, on both the phone and the PC, and both need an internet connection for the phone link
  (the browsers relay it). Without that, keep the passkey on the PC itself (Windows Hello) or a USB security key.
- A passkey belongs to the address it was made at: `https://localhost:8443` on the shop PC, or the shop-network
  name. Addresses made of numbers (`https://192.168.1.20:8443`) cannot use passkeys.
- **Sign in with passkey only** switches password sign-in off for your account: even the right password is
  refused. Use it for the owner's Super Administrator account, which also runs IntraForge Pay. To switch it back,
  confirm with your passkey. Lost the phone? On the shop PC, an administrator runs
  `docker compose exec backend python manage.py passkey_reset <email>` (add `--remove-all` to delete the lost
  passkeys too), and the password works again.

### The welcome tour

The first time you reach IntraForge after signing in, a five-slide tour shows what it does: storing files, building
databases and apps, connecting other apps, and who sees what. It opens once per person on each browser. **Skip tour** or
**Esc** closes it; **Take the tour** in the sidebar (or the account menu on a phone) opens it again. Setup's last screen
has a "Show me a quick tour" box: unticked, the tour does not open by itself. The foot of the sidebar shows the installed
version and the copyright (© 2026 lamek-rusoom).

## 4. Organizations

The Organizations page is what you land on after signing in — every
organization you're a member of, as a card.

1. **New organization** (top right) → name it → you become its
   administrator immediately, no approval step.
2. Open an organization to see its **workspaces** and its **members**
   list.
3. **Add member** attaches an existing account to the organization by
   email — it doesn't send an invite; the person needs an account
   already.

No member list visible, or an action fails? You're a member without
administrative rights in that organization — expected, not a bug. Only
administrators manage membership and roles.

## 5. Workspaces & Projects

Open a workspace from inside an organization to see its **projects**.
Open a project to reach its buckets and databases. For a small demo,
one workspace and one project is completely normal — the extra level
exists to keep large organizations tidy, not because you need it.

## 6. Storage

A bucket is a flat space for files — think a shared drive folder.

1. Inside a project: **New bucket**, give it a name (e.g.
   `shared-docs`).
2. Open it, then **Upload files** — pick one or several at once.
3. Use the search box to filter by filename. **Download** streams the
   file back through the backend. **Delete** is a soft delete —
   recoverable via the API even though it disappears from this list.

File type is detected from the actual file content on upload, not the
filename — renaming a file to `.txt` won't fool it.

## 7. Databases

A database here is a real, isolated PostgreSQL schema — not a
simulation.

1. Inside a project: **New database**, give it a name.
2. Open it → **New table**, give it a name. It's created with an
   automatic `id` column.
3. Open the table → **Add column** for each field, choosing a type from
   the table below.
4. **Add row** inserts data through a form built from your columns;
   **Edit** changes a row; **Delete** removes it.
5. The search box filters across text columns. **Export CSV** streams
   every row down as a file.

| Type | Stores | Notes |
|---|---|---|
| `text` / `varchar` | A string | `varchar` has a max length; `text` doesn't. |
| `integer` / `bigint` | A whole number | No decimals. |
| `decimal` | A precise number | Set precision (total digits) and scale (digits after the point) — good for money. |
| `boolean` | True / false | |
| `date` / `datetime` | A calendar date, with or without a time | Uses your browser's native date picker. |
| `uuid` | A unique identifier | Useful for referencing something external. |
| `json` | Any nested structure | Typed as raw JSON, e.g. `{"a": 1}`. |

Mark a column **Required** to forbid empty values, or **Unique** to
forbid duplicates — both enforced by PostgreSQL itself, not just the
form.

### The Pharmacy (built-in application, pilot preview)

**Project > Applications > Pharmacy > Install.** It is the Spare Parts application in its pharmacy edition: the
same stock, receiving and selling, with medicines instead of products and item numbers instead of part numbers.

- **Import a catalogue:** Medicines > *Import medicines* and choose a CSV such as `medicines.csv`. Each medicine
  gets its name, generic name, pack, manufacturer, origin, prescription flag, what it is listed for, the
  catalogue's price as a **reference price (INR)**, links to its pictures and an item number (`NM-847249`) for
  its label. A medicine listed under several diseases becomes one medicine. The catalogue's descriptions are
  not copied. Importing the same file again skips what is already there, so an interrupted import can simply
  be repeated. Optionally give *your price per 1 INR* to fill in selling prices; otherwise you set them.
- **Your price, shelf and pictures:** open a medicine > *Edit* to set your price, cost, shelf location and any
  other fact. The catalogue's pictures show from its website while the PC is online; add your own photos under
  *Files* (as many as you like), and those are kept in IntraForge and its backups.
- **Labels:** a medicine's (or a spare part's) page > *Print label*: the item or part number as a Code 128
  barcode with the name, generic name and pack, price, shelf and "Rx" when a prescription is needed. Choose a
  50 × 30 mm label printer or an A4 sheet of 24, and the number of copies.
- In the shop kit the Pharmacy is offered as a pilot preview (`BUILT_IN_APP_PREVIEWS=pharmacy`); set it empty
  in `.env` to hide it.

### The Movie Shop

**Movie Shop** turns the films, series and music on the shop PC's own drives into a catalogue (ADR-0022). It is an app
like the others: **Apps > Available to install > Movie Shop** creates a shop, and each shop then appears under
**Installed applications** with **Open**. The files never move into IntraForge: it keeps their names, sizes, covers and
prices.

1. **New movie shop**: give it a name and choose the project that keeps the covers.
2. **Connect the shop's drives**: create the connection key, then run the command shown once in PowerShell on the shop
   PC. The media agent (`C:\IntraForge\IntraForgeMediaAgent.exe`) then starts by itself at every sign-in. It only talks
   to IntraForge on this PC and opens nothing to the network.
3. **Choose the folders** (or type one, such as `D:\Movies`; a NAS works when it is mapped as a drive letter). Each
   folder inside becomes a category, each video a title, a folder of videos a series. The title and year come from the
   file name (`Desert Wind (2025).mp4`); a picture with the same name, or `poster.jpg` in the film's folder, becomes the
   cover, and titles without one get a drawn cover. **Music** works the same way: an audio file (`.mp3 .m4a .flac
   .wav .aac .ogg .opus .wma`) is a song, and a folder of songs is an album.
4. **Prices** sets one price for every title and one per category (in IntraForge Pay credits); **Edit** on a title
   corrects its name, year or category, sets its own price or hides it, and **Change poster** puts your own picture on
   it (JPEG, PNG or WebP up to 3 MB); your poster stays when the folder is scanned again, until you choose **Use the
   folder's picture**. **Scan again** on a library after adding films. The pencil next to the shop's name renames the
   shop; **Rename** on a library renames it. Every dialog has **Cancel**, and nothing is saved until you press Save.

5. **Selling at the counter** (needs `movies.sell` on the shop): plug the customer's USB drive into the shop PC and
   press **Add** on each title they want. The cart on the right lists the drive the media agent sees (the shop's own
   library disks are never offered), the free space and the total. Choose **IF Pay** or **Cash** and press **Charge**.
   - **IF Pay** shows the payment request's QR code and code from the shop's IntraForge Pay; the customer pays in their
     wallet and the sale turns paid by itself. The person at the counter needs `ifpay.checkout` in Pay. If they pay in
     cash after all, press **Paid in cash instead**.
   - **Cash** waits for **Paid in cash** to be pressed once the money is in the till.
   - Once paid, the media agent copies each title into `<shop name>\<category>` on the drive and the sale shows each
     title's progress. A copy is written under a `.part` name and renamed at the end, so a pulled drive leaves no half
     file; a different file with the same name is kept and the copy is saved as `name (2)`. **Copy the failed titles
     again** restarts any title that failed (for example, the drive was pulled out).
   - **Sales** in the header lists the shop's sales; open one to see its payment and copying again.

6. **The customer portal** (needs `movies.manage`): **Customers** in the header opens it. **Open the portal**, then
   give customers the address shown (`https://<shop PC>:8443/portal/...`; on a phone use the shop PC's network name or
   IP address, not `localhost`). It works on the shop network only, never through the internet gateway. Set the
   rewards there: welcome points, every Nth title free, points for inviting a friend, birthday points (1 point = 1
   credit off a Movie Shop purchase; 0 switches a reward off).
   - Customers sign up with their name, phone number and a password (optionally a birthday and a friend's code). They
     can look around at once; they order once you approve them.
   - **Add to IF Pay** approves a customer: IntraForge Pay opens their wallet and shows its username and a one-time
     first password **once**. Give both to the customer; the wallet makes them choose their own password at the
     first sign-in. You need the Pay Manager role (`ifpay.customers.manage`) in Pay. **Reject**, **Block** (signs
     them out and cancels their waiting orders) and **Unblock** are there too.
   - **Edit** corrects a customer's name, phone number or birthday.
   - **Forgotten passwords, with your permission only.** A customer who forgot their portal password chooses
     **Forgot password?** on the portal; they show as **Asks for a new password** in Customers. **Password code** gives
     you a one-time code (valid one hour, shown once) to hand them; they enter it under **I have a code** with a new
     password, and their other sign-ins end. **Wallet password** gives their IF Pay wallet a new one-time password
     (you need the Pay Manager role); the wallet asks them to choose their own again.
   - A customer's order appears in **Sales** marked PORTAL. When they come with their USB drive, open it, choose the
     drive and IF Pay or cash, and press **Charge this order**: the free titles and their points apply then. **Cancel
     this order** cancels it; a cancelled or expired sale gives the points back.

7. **Ads** in the header (needs `movies.manage`) puts ads at the top of your portal, marked "Ad": a new film, an offer,
   or another shop or business you advertise for (**For**). Give it a title, a short text, a picture (JPEG, PNG or
   WebP up to 2 MB; keep the right side for the picture) and, if you like, first and last days. A tap can open one of
   your films or a web page (`https://...`; it opens only when the customer's phone has internet). The preview shows
   it as customers see it. The list shows whether each ad is showing, its views and taps; switch it on or off, move it
   up or down, edit or delete it.

Sell only films and series you hold the rights or a licence to sell.

### The licence

IntraForge Local Edition works fully for **30 days** from its first start; a line at the top of every page says how
many days are left. After that, without a licence, it is **read-only**: everyone can still sign in, see and export
everything, and backups keep running, but nothing can be added or changed. To activate (an administrator): open
**Licence** (the link in that line, or `/license`), send **this PC's code** (`PC-....`) and your **serial number** to your
IntraForge supplier, and enter the **activation code** they send back. An SN works on one PC; a new PC needs the
supplier to move it. The copying speed of the Movie Shop: titles for one customer's drive copy one after another with
Windows' own copy engine, and two customers' drives fill at the same time.

## 8. Where to Find the Newer Screens

Everything in IntraForge now has a page. The ones added most recently, and where they are:

| Screen | Where | Who sees it |
|---|---|---|
| Storage and its usage | Organization page > **Storage**: every bucket you may open, with its files, size, kept versions and Trash, and the totals | Anyone with read access to a bucket |
| Databases | Organization page > **Databases**: every database you may open, with its table count | Anyone with read access to a database |
| Earlier versions of a file | A bucket > a file's **Versions**: **Download** an earlier content, or **Restore** it (the current content is kept, so you can go back) | Download: read access; Restore: write access |
| Uploading a whole folder | A bucket > **Upload folder**: the folder's sub-folders are made in the bucket and each file goes into its own | Write access |
| Backups | Dashboard > System health > **Backups**: the last good backup of each kind, whether its restore test passed, **Back up now**. Restoring is done in the Control Center on the shop PC | The Super Administrator |
| Requests of an application | An application's page > **Requests**: every call it made with its credentials in the last 30 days, and its result | Read access to applications |
| Logs of a hosted app | Organization page > **Websites** > a server app's **Logs** | Whoever may manage the site |
| Signing in to another application | An application that is not IntraForge's own shows **"... wants to sign you in"** once, with what it will see; **Allow** or **Deny** | Everyone |
| The customer portal's short address | On the shop network: **https://movies.lan:8443** opens the Movie Shop's portal | Customers on the shop Wi-Fi |

Everything here is also reachable through the API at `/api/v1/` (Django REST Framework's browsable interface once
you are signed in).

## 9. Troubleshooting

| What you see | What it means |
|---|---|
| Browser refuses to load the page at all | The self-signed certificate warning wasn't accepted yet — reopen the URL and click through it. |
| "You don't have permission to do that" | Correct behavior, not a bug — your account lacks the required role in that organization. |
| A page stays on its loading spinner | The backend stack isn't running — start it per `docs/deployment/LOCAL_DEPLOYMENT.md` Section 4. |
| Data from an earlier session is missing | The stack's volumes were reset (`docker compose down -v`). Nothing survives a full data wipe; day-to-day restarts (`docker compose down` / `up -d`) keep everything. |
