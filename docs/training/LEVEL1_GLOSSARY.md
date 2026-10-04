# Level 1 -- glossary

Simple meanings of the words used in IntraForge and Spare Parts, as the applications use them.

## IntraForge

| Term | Meaning |
|---|---|
| **IntraForge** | The private business system on the shop's PC (`https://localhost:8443`). |
| **Control Center** | The Windows program behind the **IntraForge** shortcut: status, start / stop, backup, restore, diagnostics, uninstall. Works even when IntraForge is not running. |
| **Organization** | A company inside IntraForge. Everything belongs to one organization; organizations are kept apart. |
| **Member** | A person who belongs to an organization. Must have an IntraForge account first. |
| **Account** | A person's sign-in (email + password, optionally a two-step code). |
| **Two-step sign-in (MFA)** | A 6-digit code from an authenticator app asked for at sign-in, when switched on for the account. |
| **Role** | A named set of permissions given to a member (for example *Organization Administrator*, *Spare Parts Sales*). |
| **Permission / Capability** | One specific right, for example `storage.write` or `spareparts.sales.manage`. The server checks it for every action. |
| **Default-deny** | Without a role or share that allows something, it is not allowed. |
| **Team** | A group of members, used to share with several people at once. |
| **Unit (organizational unit)** | A part of the organization's structure, such as a branch or department. |
| **Workspace** | A group of projects inside an organization. |
| **Project** | Holds buckets, databases, connected databases and dashboards. |
| **Bucket / Storage** | A file area for uploading and downloading files. |
| **Database (tenant database)** | A real database of the organization where you design tables. |
| **Table, column, row** | A table holds data in rows; columns are its fields. |
| **Connected database** | A read-only link to an external PostgreSQL database. |
| **CSV import** | Loading a CSV file into a table. |
| **Analytics / Dashboard** | Statistics on a table; a dashboard keeps live widgets. |
| **Share** | Giving one member or team access (read only or read & write) to one thing. |
| **Audit / Audit log** | The unchangeable history of who did what, when, and whether it was allowed. |
| **Apps** | The page where installed applications (Spare Parts) are opened and installed. |
| **Service application** | A separate program IntraForge installs, opens and backs up (Spare Parts). |
| **Template / Installed app (application platform)** | A design for a business application, and a copy of it installed in a project. Different from the Spare Parts service application. |
| **Application (developer)** | A registered outside program that connects to IntraForge with a credential. |
| **Credential / token** | The secret an outside program uses; shown only once; can be rotated or revoked. |
| **Environment** | Development, Staging or Production setup of an application, with its variables, secrets and webhooks. |
| **Webhook** | IntraForge sending an event message to another system (signed, at least once). |
| **Backup** | Three encrypted files (company data, business records, stored files) made daily. |
| **Restore** | Putting the shop back to a backup; a safety backup is taken first. |
| **Diagnostics** | A zip for support without passwords or keys. |
| **Keys file** | The shop's secret key file; needed to read its backups. |

## Spare Parts

| Term | Meaning |
|---|---|
| **Reference Catalogue** | Manufacturer / supplier reference data: part numbers, fitment, drawings. No shop prices or stock. |
| **OEM** | Original Equipment Manufacturer -- the vehicle maker's own part number and part. |
| **OEM number** | The manufacturer's part number. Search finds it with or without dashes or spaces. |
| **PNC** | The part group code from the manufacturer's catalogue (the import calls it "PNC / part group code"); it groups the same part on drawings. |
| **Fitment** | Which vehicles a part fits: make, model, chassis, engine, production dates, market. |
| **Chassis / frame** | A vehicle's model code (for example AT151). |
| **VIN** | Vehicle identification number. |
| **Drawing, callout** | An exploded-view picture of an assembly; callouts are the numbers pointing to parts. |
| **Supersession / superseded** | A part replaced by a newer number; status *Superseded*. |
| **Source** | Where catalogue data came from. |
| **Reference price** | A price from the source -- information only, not the shop's selling price. |
| **Import to My Products** | Creating a shop product from a reference part. |
| **My Products** | The parts the shop stocks and sells. |
| **SKU** | The shop's own unique product code. |
| **Part number types** | OEM, Aftermarket, Supplier, Cross reference, Replacement, Previous, Interchange, Other. |
| **Selling price / Cost price** | What the customer pays / what the shop pays (cost visible only with the cost permission). |
| **Reorder level** | At or below this, a product is *Low stock* / *Needs reordering*. |
| **Warehouse** | A store or building. |
| **Location; Rack, Shelf, Bin** | A place in a warehouse, made of rack, shelf and bin. |
| **On hand** | Units physically there. |
| **Reserved** | Units set aside for confirmed orders not yet delivered. |
| **Available** | On hand minus reserved. |
| **Stock movement** | A recorded change of stock: opening balance, receipt, sale, return in, transfer out / in, adjustment in / out. |
| **Receive** | Recording goods that arrived (stock goes up). |
| **Adjustment** | A correction of the stock count, always with a reason. |
| **Transfer** | Moving stock from one location to another. |
| **Reservation / release** | Setting stock aside for an order / freeing it when the order is cancelled. |
| **Integrity check** | A check that the stock ledger adds up. |
| **Supplier** | A company the shop buys from. |
| **Purchase order (PO)** | What the shop orders from a supplier; received when goods arrive. |
| **Customer** | A person or company the shop sells to. |
| **Enquiry** | What a customer asked for (parts, vehicle); collected in the enquiry cart. |
| **Quotation** | The price offer to the customer, issued as a PDF; accepted or rejected. |
| **Sales order** | The confirmed order; reserves stock. |
| **Delivery** | Goods leaving the shop for an order (stock goes down). |
| **Return** | Goods the customer brings back (stock goes up). |
| **Invoice** | The bill for delivered items. |
| **Payment** | Money received for an invoice (cash, bank transfer, card, other). Payments are permanent. |
| **Void** | Cancelling an invoice (with a reason). |
| **Back-order** | Creating an order although part of it is not in stock yet. |
| **Scan / Lookup** | Opening a product by scanning its barcode / QR label or typing a code. |
| **Label (barcode / QR)** | A printable product label; scanning it opens the product. |
| **Audit log (Spare Parts)** | The app's own history; also sent to IntraForge's audit log. |
| **Statuses** | Enquiry: Draft, Submitted, Quoted, Closed, Cancelled. Quotation: Draft, Issued, Accepted, Rejected, Expired, Cancelled. Order: Confirmed, Partially fulfilled, Fulfilled, Invoiced, Cancelled. Invoice: Issued, Partially paid, Paid, Void. Purchase order: Draft, Confirmed, Partially received, Received, Closed, Cancelled. Customer / supplier / product: Active, Inactive. |
