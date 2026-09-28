# IntraForge, explained from zero

*A complete, plain-language guide to what IntraForge is, what it does, how it works and how it keeps a business's data
safe. Written for someone who has never heard of it and is not technical. Situation as of September 2026, shop kit
version 1.1.0.*

---

## 1. IntraForge in one minute

**IntraForge is a private business system that runs on your own computer.** A shop (or any small business) installs it
from one file on one PC. From then on it has, in one place:

- a secure place for its **files** and documents,
- its **business application** -- today **Spare Parts / Inventory & Sales**: products, stock, customers, quotations,
  orders, invoices and payments,
- **people and permissions** (who may see and do what),
- a **history of everything that was done** (the audit log),
- **automatic backups** and a safe way to restore them.

Its motto is **"Build. Store. Connect. Privately."** The most important word is *privately*: the business's data stays
**on its own PC**. Nothing is sent to the internet, there is no monthly cloud subscription, and it keeps working when the
internet is down.

---

## 2. The problem it solves

Small businesses usually end up with a mix of paper, spreadsheets, a cheap program for invoices, photos on a phone and
files on a USB stick. That causes the same problems again and again:

| The everyday problem | What IntraForge does instead |
|---|---|
| "How many of this part do we really have?" -- the stock on paper is not the stock on the shelf | Stock is a **ledger**: it only changes when something is received, delivered or corrected with a reason, so the number can always be explained |
| Customer, supplier and price information is scattered | One place for products, customers, suppliers and documents |
| Nobody knows who changed what | Every important action is recorded in an **audit log** that cannot be edited |
| Everyone can see everything, including costs | Each person gets a **role**: sales staff can sell, inventory staff can receive stock, only the owner sees everything |
| Cloud software costs money every month and needs the internet | Runs on the shop's own PC; **no internet needed** |
| A broken PC means lost data | **Daily encrypted backups**, a weekly automatic test that they can really be restored, and a guided restore |

---

## 3. Who it is for

- **The first user is a spare-parts shop** (car parts). IntraForge is being piloted in the owner's own shop.
- The design fits any small business that wants its own private system: one PC in the shop, one to ten people using it.
- The long-term idea is a platform for many business applications (school, HR, customer management, purchasing,
  assets, projects, documents, warehouses already exist as templates), but **only Spare Parts is qualified for real use
  today**.

---

## 4. The four things you actually get

Think of IntraForge as a **private office building** on your PC:

1. **IntraForge itself -- the building.** It has the front door (sign-in), the staff list (people and roles), the
   filing room (files), the security guard (permissions), the logbook (audit) and the safe (backups).
2. **Apps -- the shops inside the building.** Today there is one: **Spare Parts / Inventory & Sales**. It uses the
   building's front door, staff list, filing room, logbook and safe -- it does not have its own.
3. **The Control Center -- the caretaker's desk.** A small Windows program (the one "IntraForge" shortcut on the
   desktop) that shows whether everything is running and lets the owner start, stop, back up, restore and remove
   IntraForge -- even when the rest is not working.
4. **The installer -- the moving company.** One file, `IntraForge-Setup-1.1.0.exe`, that sets everything up on a PC with
   no internet, and also upgrades an older installation without losing data.

---

## 5. What IntraForge itself offers

Everything below is available to every organization (company) inside IntraForge:

- **Accounts and sign-in.** Each person has their own account (email + password). An optional **two-step code** from a
  phone app adds extra protection. Too many wrong passwords are slowed down on purpose (at most 10 attempts a minute).
- **Organizations, members and roles.** A company is an *organization*. The first account becomes the administrator.
  Members get **roles** such as administrator, editor, viewer or auditor, and app roles such as "Spare Parts sales".
- **File storage.** Like a private drive: folders, files, versions of a file, size limits, and (optionally) a virus scan
  that blocks a file it cannot check.
- **A no-code database builder.** Create your own tables (for example "Vehicles we service") with fields and links,
  browse and edit the rows like a spreadsheet, and import data from CSV/Excel-style files.
- **Analytics and dashboards.** Automatic data-quality checks of a table, statistics (averages, trends, comparisons) and
  saved dashboards.
- **Sharing.** Give one colleague access to one thing (a folder, a table) without giving them everything.
- **The audit log.** Who did what, when, on which item, and whether it was allowed. It cannot be edited.
- **Backups and restore** (section 10).
- **Export of a whole organization** into one encrypted package that can be brought back into IntraForge.
- **Controlled connections for other programs** (for a developer or a partner system), only to what is explicitly
  granted, and switched off by default.
- **Apps** -- installing and opening business applications (next section).

---

## 6. The Spare Parts app, feature by feature

Spare Parts / Inventory & Sales is the shop's daily tool. It opens from **IntraForge > Apps > Open**, with no second
sign-in.

**Reference Catalogue.** A searchable list of parts from manufacturers or suppliers (part number, description, maker,
vehicle, category, drawings). It can be filled by importing a supplier's CSV file (match the columns, preview, import).
Search finds a part **however the number is typed**: `11110-36F00` and `1111036f00` find the same part. 20,000 parts import in about two minutes; a search answers in well under a tenth of a second.

**My Products.** The parts the shop actually sells: its own code (SKU), cost price, selling price, photos, and the
supplier it buys from. A catalogue part becomes a product with one button (**Import to my products**).

**Suppliers and purchase orders.** Who the shop buys from, at what cost, and what was ordered and received.

**Stock & Locations.** Stores/warehouses and shelves. Stock is a **ledger**: every change is a recorded movement
(received, delivered, adjusted with a reason). Nobody types a stock number. An integrity check confirms the ledger adds
up.

**Customers.** Garages and walk-in customers, with their history.

**Selling, step by step:**

1. **Enquiry** -- a customer asks for parts; they go into an enquiry (like a shopping cart).
2. **Quotation** -- one click turns it into a quotation with prices; it can be issued as a **PDF**.
3. **Order** -- when the customer accepts, the quotation becomes an order.
4. **Delivery** -- the goods leave; **stock goes down** automatically.
5. **Invoice** -- one click invoices what was delivered.
6. **Payment** -- recording the payment marks the invoice **Paid**.

Mistakes are corrected the honest way: cancel a quotation or order, record a return, void an invoice, or adjust stock
with a reason. The history always stays complete.

**Reports and dashboard.** Sales and payments this month, stock value, low stock, and more.

**Shop settings.** Shop name, address, currency, tax and document details (used on quotations and invoices).

**Roles inside Spare Parts** (given by IntraForge):

| Role | Can do |
|---|---|
| Spare Parts manager | Everything |
| Spare Parts sales | Customers, enquiries, quotations, orders, invoices, payments |
| Spare Parts inventory | Products, stock, suppliers, purchase orders |
| Spare Parts viewer | Look only |

People without a Spare Parts role do not see the app.

---

## 7. How IntraForge and Spare Parts work together

Spare Parts was first built as a separate program that ran on its own (it had its own address, its own logins and kept
data only in the browser). In version 1.1 it was **integrated into IntraForge** so that the shop has one system, not two:

| Topic | How it works now |
|---|---|
| Signing in | **One sign-in**, to IntraForge. "Open" takes the person straight into Spare Parts. Signing out of IntraForge also signs them out of Spare Parts. |
| People and permissions | Managed in IntraForge (members and roles). Spare Parts asks IntraForge on every action whether the person is still allowed. |
| Data | Stored in IntraForge's database, in a separate, locked compartment that only Spare Parts can use. |
| Photos and documents | Stored in IntraForge's file storage. |
| History | Every important action in Spare Parts also appears in IntraForge's audit log. |
| Settings | Kept in IntraForge. |
| Backups | Spare Parts' data and files are part of IntraForge's backups. |
| Address | `https://localhost:8443/apps/spare-parts/` -- inside IntraForge; the old separate address (port 3000) is gone. |

A simple way to picture it: Spare Parts is a shop **inside** the IntraForge building. It uses the building's entrance,
guard, logbook and safe, and has its own locked room for its stock and papers.

---

## 8. A day in the shop

**Morning.** The owner switches on the PC and signs in to Windows. IntraForge starts by itself (about 1-2 minutes). The
Control Center shows a green **Healthy**.

**A part arrives.** Rashid (inventory role) opens Spare Parts, finds the product, and records the delivery from the
supplier. The stock goes up by the delivered quantity, and the movement is recorded with his name and the time.

**A customer calls.** Sara (sales role) searches the part number exactly as the customer reads it out -- with or without
dashes. She adds two parts to an enquiry, turns it into a quotation and sends the PDF.

**The customer accepts.** Sara creates the order, records the delivery (the stock goes down), invoices it and records
the payment. The invoice shows **Paid**.

**The owner checks.** On the dashboard: today's sales and payments. In the audit log: who did what. Sara cannot see cost
prices; the owner can.

**Evening.** At 19:00 the automatic backup runs. Once a week the owner plugs in a USB drive and presses **Backup to a
folder / USB** in the Control Center, so a copy exists away from the PC.

---

## 9. The Control Center

The Control Center is the **one IntraForge shortcut** on the desktop and in the Start menu. It is a small Windows
program that opens in about a second **even when IntraForge or Docker is not running** -- because it is the place where
problems are fixed.

**It shows one status at the top:**

| Status | Meaning | What to do |
|---|---|---|
| Healthy (green) | Everything runs | Nothing |
| Starting (blue) | Starting up after Windows starts | Wait a minute |
| Degraded (orange) | IntraForge answers but a part does not | Restart services |
| Stopped (grey) | Not running | Press Start |
| Failed (red) | Started but not ready | Restart services, then Diagnostics |
| Repair required (red) | Something is missing | Run the setup file again |

Below the status: the **installed apps** with an **Open** button, and each check with a plain explanation (free disk
space, memory, Docker, the services, the last backup). When something is wrong it says *why* -- for example
"virtualization is switched off in the PC's BIOS" or "Docker is not running, press Start".

**Buttons:** Open IntraForge - Start - Restart services - Stop - Backup now - Backup to a folder / USB - Restore -
Settings - Diagnostics - Uninstall.

**Diagnostics** creates a zip file for support (status, logs, versions). It never contains passwords or keys -- this was
checked by searching the zip for every secret value.

---

## 10. Backups and restore: the safety net

**Backups happen automatically:**

- **Every day at 19:00** (or at the next start if the PC was off).
- **Every Sunday** a test proves that the newest backup can really be restored (into a throw-away copy, never over the
  real data).
- Each backup is **three files** together: the company data, the business records, and the stored files (photos,
  documents). They are **encrypted**; a changed byte is detected.
- The newest 30 are kept on the PC; **Backup to a folder / USB** puts a copy on a USB drive. *A backup only on the shop
  PC's disk is not a backup.*

**The keys file.** Backups are locked with the shop's own key (`intraforge-keys.env`). Without it a backup cannot be
read. The owner copies it once to a USB drive (Control Center > Settings) and keeps it separate from the backups.

**Restoring is guided and safe:**

1. **Choose** a backup (on this PC, or on a USB drive).
2. **Check it** -- nothing changes yet. IntraForge opens every file, verifies every checksum, and shows when the backup
   was made, which apps it contains and how many products, customers and invoices, and whether this version can use it.
3. **Confirm** by typing `RESTORE`.
4. IntraForge first takes a **safety backup of the current state**, then restores, updates the data to the current
   version, and checks that everything is healthy.
5. **If anything goes wrong, the safety backup is put back automatically** -- the shop is exactly as it was before the
   attempt. (This was proven by deliberately restoring a damaged backup: IntraForge refused it and put everything back.)

A backup made by an **older version** of IntraForge can be restored into the newer one; it is updated automatically.

---

## 11. Installing, upgrading and removing

**Installing (about 15-20 minutes, no internet):**

1. Double-click `IntraForge-Setup-1.1.0.exe`. Windows warns "Unknown publisher" (the file is not code-signed yet):
   *More info > Run anyway*.
2. Setup checks the PC (Windows version, memory, disk, virtualization) and shows each result.
3. It switches on the Windows parts it needs (one administrator prompt) and **restarts the PC**.
4. After signing in again it continues by itself: it installs WSL and Docker Desktop (the engine IntraForge runs on) and
   IntraForge -- all from the file itself.
5. The Control Center opens. There is one shortcut, "IntraForge", and an entry in Windows' *Installed apps*.

**Upgrading from an older version:** run the newer setup file. It takes a **complete backup first**, installs the new
version, keeps all data and keys, checks that it is healthy -- and **if anything fails, it puts the previous version back
by itself**, running, with the data. (This happened once during testing and worked exactly as designed.)

**Removing (Control Center > Uninstall), three choices:**

- **A. Remove, keep data** -- installing again brings the shop back as it was.
- **B. Back up first, then remove.**
- **C. Complete removal** -- a backup first (nothing is deleted if it fails), then the data, program and images are
  deleted. You must type `DELETE-MY-SHOP-DATA`.

In every choice the **backups, the keys file and the logs are kept**, and Docker Desktop stays installed.

---

## 12. Privacy and security, in plain words

- **It stays on this PC.** IntraForge can only be reached from the PC it is installed on. The programs inside it have no
  route to the internet (checked: an attempt to reach a website is blocked).
- **Every action is checked on the server.** Hiding a button on screen is only a courtesy; the real lock is the check
  that happens for every request: *does this person have this permission for this item?*
- **Least privilege.** Spare Parts has its own database user that can only touch its own compartment.
- **Separate companies stay separate.** One organization can never reach another's data, even by guessing addresses
  (this is tested for every kind of item).
- **Everything important is logged**, and the log cannot be changed.
- **Backups are encrypted** and tamper-evident.
- **Secrets never leave**: the keys are never included in diagnostics or exports.
- **Sign-in protection**: optional two-step code; slowed down after repeated wrong passwords.

---

## 13. Under the hood (for the curious)

IntraForge is made of about ten small programs that run together inside **Docker** (a standard way to package programs so
they run the same on every PC). Each has one job:

| Part | Everyday comparison | What it does |
|---|---|---|
| Proxy | Reception desk | The single entrance; secures the connection (HTTPS) and sends each request to the right place |
| Frontend | The shop window | The screens you see in the browser |
| Backend | The manager | Every rule and every permission check |
| Worker and scheduler | The night shift | Background jobs: imports, backups, the daily and weekly schedules |
| Control database | The staff register | Users, companies, roles, apps, the audit log |
| Tenant database | The stockroom | The business data, each company in its own compartment |
| Object storage | The filing cabinet | Files and photos |
| Cache | The notepad | Short-term memory and the job queue |
| Spare Parts | A shop inside the building | The Spare Parts app, using everything above |

The Control Center and the installer are ordinary Windows programs outside Docker, so they work even when Docker does not.

---

## 14. How it was tested

IntraForge is tested at three levels, and every result is recorded honestly (pass, fail, blocked):

- **Automatic tests on every change:** 1,116 backend tests on real databases, 84 screen tests, and 142 Spare Parts tests
  (plus the same suite on PostgreSQL).
- **A complete shop day in a real browser:** sign in, install Spare Parts, import a catalogue, find a part, create a
  product with a photo, receive stock, customer, enquiry, quotation (PDF), order, delivery, invoice, payment -- then check
  that stock, reports and the audit log agree.
- **Backup and restore round trip:** back up, change things (add a customer, receive stock, delete a photo, change a
  price), restore -- and check every value came back exactly, including the photo byte-for-byte.
- **A clean Windows PC with no internet** (a virtual machine): fresh install from nothing, upgrade from the previous
  version, restore of an older backup, a damaged backup, a restart, stopping Docker, and all three removal options.
  Those tests found **six real defects that ordinary tests could not find**; all were fixed and re-tested, and the final
  installer file passed every scenario.
- **Performance:** 20,000 catalogue parts import in about 2 minutes; searches answer in 0.06-0.1 seconds; lists and the
  dashboard in about 0.02 seconds. A 2-second delay that users had noticed was found (Windows trying the wrong network
  address first) and fixed.
- **Dependency checks:** no known vulnerabilities in the components used.

---

## 15. Honest status: what is ready and what is not

**Ready for the owner's own-shop pilot:**

- IntraForge with Spare Parts integrated, offline, on one PC.
- Install, upgrade (with automatic rollback), backup, guided restore (with automatic rollback), removal.
- The Control Center.

**Not done yet, or blocked by something outside the project:**

- **Code signing** -- needs a certificate; until then Windows shows "Unknown publisher".
- **Use from other computers on the shop network** -- not tested (no second machine), and off by design for now.
- **An independent security scan** (HawkScan) -- not run (no account key).
- **A real restart test on the shop's own PC** -- tested on a virtual machine so far.
- **Catalogue search by manufacturer name** (for example "toyota pump") is not supported yet.
- IntraForge starts when someone **signs in to Windows**, not when the PC switches on.

During the pilot the shop keeps its existing records (paper or spreadsheet) as the official record and compares daily.
The pilot ends with a decision, not an automatic switch.

---

## 16. Glossary

| Word | Meaning |
|---|---|
| **App** | A business application inside IntraForge, such as Spare Parts |
| **Audit log** | The unchangeable history of who did what |
| **Backup set** | The three files (company data, business records, stored files) that together are one backup |
| **Control Center** | The Windows program behind the "IntraForge" shortcut: status, start/stop, backup, restore, removal |
| **Docker** | Standard software that runs IntraForge's parts in separate, identical boxes |
| **Keys file** | The shop's secret key file; needed to read its backups |
| **Ledger** | A list of every stock movement; the stock is the sum of the movements |
| **Offline** | Works without the internet |
| **Organization** | A company inside IntraForge |
| **Role** | A named set of permissions given to a person |
| **Rollback** | Automatically putting things back as they were when something fails |
| **SKU** | The shop's own product code |
| **WSL** | A Windows component Docker Desktop needs; installed by Setup |

---

## 17. Suggested presentation outline (12 slides)

1. **Title** -- IntraForge: your business system, on your own PC. "Build. Store. Connect. Privately."
2. **The problem** -- paper, spreadsheets, lost stock counts, no history, cloud costs, lost data (section 2).
3. **What IntraForge is** -- one private system: files, apps, people, history, backups; no internet (sections 1, 4).
4. **The building picture** -- IntraForge = building; Apps = shops inside; Control Center = caretaker; installer = moving
   company (section 4).
5. **Spare Parts in the shop** -- catalogue, products, stock ledger, customers (section 6).
6. **From enquiry to payment** -- the six steps (section 6).
7. **One system, not two** -- one sign-in, one set of people, one backup (section 7).
8. **A day in the shop** -- the story (section 8).
9. **The Control Center** -- the status lights and buttons (section 9).
10. **Never lose data** -- daily encrypted backups, USB copy, the keys file, guided restore with automatic rollback
    (section 10).
11. **Private and secure** -- stays on the PC, permissions, audit, encryption (section 12).
12. **Proven, and what is next** -- how it was tested, the pilot, what is still open (sections 14, 15).
