# Spare Parts Shop -- Level 1 guide

*For a brand-new employee who has never used the system. Describes the Spare Parts application as implemented
(branch `intraforge/platform-integration`, commit `12d4d4b`) when it runs inside IntraForge. Every statement comes from
the code; anything the code does not confirm is marked NOT CONFIRMED. Page-by-page detail: SPARE_PARTS_LEVEL1_UI_INVENTORY.md;
every field, button and column: the SPARE_PARTS_*_REFERENCE.md files.*

---

## 1. What Spare Parts is

Spare Parts / Inventory & Sales is the shop's daily program for **parts, stock, customers and sales**. It runs **inside
IntraForge**: you sign in to IntraForge once, open **Apps**, and press **Open** next to Spare Parts. You never sign in to
Spare Parts separately. Its address is `https://localhost:8443/apps/spare-parts/`.

What you can do in it (each area only if your role allows -- see section 12):

| Area | In one sentence |
|---|---|
| Dashboard | Today's figures and what needs attention |
| Reference Catalogue | Look up any manufacturer part: numbers, which vehicles it fits, drawings |
| Import | Load a supplier's / manufacturer's parts list into the catalogue |
| My Products | The parts the shop actually sells: own code, prices, photos, stock |
| Stock & Locations | How many are where; receive, correct and move stock |
| Scan / Lookup | Scan a label or type a code to open the product |
| Purchase Orders | What the shop orders from suppliers, and receiving it |
| Enquiries, Quotations, Orders, Invoices & Payments | Selling, from the customer's question to the money |
| Customers, Suppliers | Who you sell to and buy from |
| Reports | Live figures from stock, invoices and payments |
| Users, Shop settings, Audit log | Administration |

---

## 2. The screen

- **Left menu**, in groups: *Overview* (Dashboard), *Catalogue* (Reference Catalogue, Import), *Inventory* (My Products,
  Stock & Locations, Scan / Lookup, Purchase Orders), *Sales* (Enquiries, Quotations, Orders, Invoices & Payments),
  *Contacts* (Customers, Suppliers), *Insights* (Reports), *Administration* (Users, Shop settings, Audit log).
  **You only see the items your permissions allow** (each menu item has its own permission, `ui/Shell.tsx`). The menu
  can be collapsed.
- **Top bar**: a search box *"Scan or type a SKU / part number…"* (opens the product), and your name and role; the
  account menu has **Sign out**.
- **Sign out** (since 1.2.0) signs you out of IntraForge as well and shows the shop's own sign-in page ("Spare Parts --
  <shop name>"), so on a shared counter PC the next person signs in as themselves. Signing out of IntraForge also ends
  your Spare Parts session (within about 5 seconds).
- If your Spare Parts session is missing or expired, the app sends you back through IntraForge's **Open** automatically
  (straight back in while you are still signed in to IntraForge; otherwise to that sign-in page).
- Most lists share the same controls: a **search box**, a **status filter** where the list has statuses, **paging**, and the
  number / name as a link that opens the record. Success and error messages appear as short notices.

---

## 3. Dashboard ("Business overview")

Shows, as your permissions allow: **Products**, **Low stock**, **Stock value (cost)**, **Sales this month**; **Open enquiries**,
**Open quotations**, **Open orders**, **Outstanding invoices**; and the panels **New enquiries**, **Needs reordering**
("Nothing is below its reorder level." when all is fine) and **Unpaid invoices** (Invoice, Customer, Overdue, Balance).
The subtitle shows who is signed in and their role. Next step: open a list or search.

---

## 4. Reference Catalogue vs My Products -- the most important idea

The application keeps **two different kinds of part information**. Mixing them up is the most common beginner mistake.

| | REFERENCE CATALOGUE | MY PRODUCTS |
|---|---|---|
| What it is | Manufacturer / supplier **reference data** about parts that exist in the world | The parts **your shop** stocks and sells |
| The page says | "Manufacturer part numbers, fitment and drawings. This is reference data — it holds no shop prices or stock." | Your own codes, prices, photos, stock |
| Contains | OEM number, OEM description, manufacturer, PNC, vehicle (make, model, chassis, engine), fitment, production dates, market, catalogue / section, drawings and callouts, supersessions (status *Superseded*), source, external ID, reference price (**info only**) | Shop **SKU** (your own code), name, brand, manufacturer, category, condition, **selling price**, **cost price**, unit, reorder level, photos, extra part numbers, suppliers (their part number, their cost, preferred), **stock** per warehouse location (rack / shelf / bin) |
| Prices | Reference prices from the source -- "**not your selling prices**" | Your selling price and cost price |
| Stock | None | On hand, reserved, available per location |
| Who changes it | Imported by administrators (Import) | Inventory staff and managers |

**How a reference part becomes something you sell:**

```
Reference Catalogue  (find the part, check fitment)
        ↓   IMPORT TO MY PRODUCTS  (on the part's page)
Shop product in My Products  (your SKU, name, prices, reorder level, supplier, location, stock now)
        ↓   Receive stock / opening stock
Inventory  (on hand / reserved / available per location)
        ↓
Quotations, orders, invoices use the shop product
```

The shop product stays **linked** to its reference part ("Linked to the Reference Catalogue"), so its fitment can be shown
(product page, *Fitment* and *OEM Reference* tabs). A product can also be created directly with **New product**, without a
reference part, and linked later ("Link to a reference part").

---

## 5. Reference Catalogue

**Searching.** Type a part number **in any format** -- the page explains: "“90915-10009”, “9091510009” and “90915 10009” all
find the same part" -- or a description, vehicle or chassis ("Part number (any format), description, vehicle or chassis…").
Press **Search**. Results: Part number, Description, Fits, Drawings, Status, My Products (whether the shop already stocks it).

**Browsing with filters** (when not searching): Manufacturer, Model, Chassis / frame (example "AT151"), Engine, Market,
Part status (Active, Ended / discontinued, Superseded), "Only parts that appear on a drawing".

**Part details** (click a part number) shows the description and numbers, **Fitment** (Make, Model, Chassis, Engine,
Production, Market, Catalogue / section, Notes), **drawings** with the callout, **source records** (Source, Description,
Status, Reference price *info only*, Recorded, Source record, External ID, Catalogue, Imported, Link), whether it is
already **in My Products**, and buttons **Add to enquiry** and **IMPORT TO MY PRODUCTS**. Catalogue administrators also see
*Verification*.

**Drawings** show the exploded view with numbered callouts and the list of parts on it (No., Part number, Description,
Qty, Status) with a filter "Filter by number, name or callout"; **Add to enquiry** works from here too.

### Import to My Products

On a part's page press **IMPORT TO MY PRODUCTS**. The dialog asks:
- **Your SKU** (required) -- the shop's own unique code; an existing SKU is refused ("SKU … already exists.").
- **Product name** (required).
- **Selling price**, **Cost price** (cost only if your role may see costs), **Reorder level**.
- **Supplier**, **Store in** (a location) and **Quantity in stock now** (recorded as an opening balance).

Saving creates the product, linked to the reference part (permission `products.write`). Next: open the product and complete
it (photos, more part numbers, suppliers).

### Catalogue Import (administrators)

*Catalogue > Import* has three tabs: **CSV import**, **Offline package**, **History**.

1. **CSV import**: choose a UTF-8 CSV with a header row (quoted fields, commas and line breaks in quotes, and a byte-order mark
   are allowed). The app reports how many data rows it found and **suggests a match for each column** -- check them.
2. Optional defaults: **Default manufacturer**, **Default source name**, **Default market**.
3. Tick **"I confirm that my organisation is allowed to use this data."** -- required; without it the import is refused.
4. Every row is checked before anything is stored: new, already present, changed, duplicated or invalid, with problems listed.
5. The **job page** shows counts (New, Updated, Unchanged, Skipped, Errors) and row-by-row status; start the import there.
   Big imports continue in the background. Measured: 20,000 rows in about 2 minutes inside IntraForge.
6. **Offline package**: a zip with parts, drawings and images; images are kept only if you confirm the shop is licensed to store
   and display them ("Without this, images are skipped and only their source links are kept.").

---

## 6. My Products

The list shows Product, Category, Available, On hand, Price, Cost (only with the cost permission), Status, with search
("Search name, SKU, brand or part number"), **Low stock only** and an Active / Inactive status filter.

**New product** asks: **SKU (your own code)** (required), **Name** (required), Brand, Manufacturer, Category, **Condition**
(New, Used, Remanufactured, Other), **Selling price**, **Cost price**, Unit, Description, Status, **Default supplier**,
**Opening stock location**, **Opening stock quantity** (the shelf count when you create it; needs a location).

**Product details** has tabs:
- **Overview** -- details and prices, photos, labels.
- **Fitment** -- vehicles (from the linked reference part; link it on *OEM Reference* to see it).
- **Stock** -- per warehouse / location: On hand, Reserved, Available; buttons Receive, Transfer, Adjust; movements.
- **Supplier** -- suppliers of this product: their part number, cost, preferred; **Add / update supplier**.
- **OEM Reference** -- extra part numbers (Number, Type: OEM, Aftermarket, Supplier, Cross reference, Replacement, Previous,
  Interchange, Other; Brand, Source, Notes) via **Add number**, and the linked reference part.
- **Sales** -- invoices with this product ("Your role cannot see sales figures." if not allowed).
- **History** -- who changed what ("Your role cannot see history." if not allowed).

**Photos (product images):** PNG, JPEG, GIF or WebP only; **Make primary** chooses the main photo; **← Earlier / Later →**
reorder them. They are stored in IntraForge's file storage and are part of its backups.

**Labels:** choose **Barcode label** (Code 128) or **QR label**, then **Open to print**. "Scanning this label in
“Scan / Lookup” opens this product."

**Edit product** changes the details; cost prices can only be changed with the cost permission ("You may not change cost
prices." otherwise). The shop SKU cannot be removed from the product's numbers.

---

## 7. Inventory -- stock, locations and movements

### Words you will see

| Term | Meaning (as implemented) |
|---|---|
| **On hand** | Units physically there (sum of all stock movements for that product and location) |
| **Reserved** | Units set aside for confirmed sales orders not yet delivered |
| **Available** | `available = on_hand − reserved` -- what you can still sell or move |
| **Reorder level** | A product at or below it shows as *Low stock* / *Needs reordering* |
| **Warehouse** | A store or building (name, address) |
| **Location** | A place in a warehouse made of **Rack**, **Shelf** and **Bin** (and a description); its location code must be unique in the warehouse |

Where a product is: product page *Stock* tab, or *Stock & Locations > Stock* (Product, SKU, Warehouse, Location, On hand,
Reserved, Available).

### Stock movement types (the only ones that exist)

| Type | Created by |
|---|---|
| `OPENING_BALANCE` | Opening stock when a product is created / imported |
| `RECEIPT` | **Receive** (with or without a purchase order) |
| `SALE` | **Save delivery** on a sales order (stock leaves) |
| `RETURN_IN` | **Record return** (customer brings goods back) |
| `RETURN_OUT` | Allowed by the database, but no screen or operation in the code creates it (return to a supplier is NOT IMPLEMENTED in the user interface) |
| `TRANSFER_OUT` + `TRANSFER_IN` | **Transfer** between two locations |
| `ADJUSTMENT_IN` / `ADJUSTMENT_OUT` | **Adjust** (with a required reason) |

**Reservation and release** are not movements: confirming an order **reserves** (reserved goes up), cancelling **releases**
(reserved goes down), delivering reduces both on hand and reserved.

### Stock & Locations page

Tabs: **Stock**, **Warehouses & locations** (**New warehouse**, **Add rack / shelf / bin**, **Edit**), **Movements** (When,
Product, Type, Location, Change, Note), **Integrity check** (only with `inventory.write`: proves the ledger adds up).

- **Receive**: Location, **Quantity received** (required), Note (delivery note, source) -> stock goes up.
- **Adjust**: Location, **Change in quantity** (required, + or −, not zero), **Reason** (required: "Give a reason for the stock
  adjustment.") -> refused if it would drop below what is reserved ("… of the stock here is reserved for orders; release those first.").
- **Transfer**: **From**, **To** (must be different: "Choose two different locations."), **Quantity** (at most what is available
  there: "Only … available to transfer from this location."), Note.

Stock is never typed in directly; every change is a recorded movement with your name and the time.

### Scan / Lookup

"Scan a barcode or QR label with a scanner, or type a SKU or any part number, then press Enter." The product opens. If
nothing matches: "No product in My Products matches that code. Search the Reference Catalogue instead."

### Purchase Orders

Statuses: `DRAFT`, `CONFIRMED`, `PARTIALLY_RECEIVED`, `RECEIVED`, `CLOSED`, `CANCELLED`.
1. **New purchase order**: Supplier, Expected date, Receive into (location), Notes, lines (products or a free-text line; at
   most 200 lines) -> **Save draft**.
2. **Confirm** -> `CONFIRMED`.
3. When goods arrive: **Receive goods** (quantity per line, pre-filled with what is outstanding) -> **Receive into stock**:
   stock goes up ("Enter what actually arrived. Stock increases when you save.") -> `PARTIALLY_RECEIVED` or `RECEIVED`.

---

## 8. Customers and Suppliers

Lists: Code, Name, Contact, Phone, Email, Status, with search ("Search name, code, phone or email") and Active / Inactive.
**New customer**: Name (required), Contact person, Phone, Email, Country, Tax number, Currency (3 letters, e.g. AED), Payment
terms, Billing address, Shipping address, Credit limit, Notes, Status. **New supplier**: the same without addresses / credit
limit. A customer's page shows their quotations, orders and invoices; a supplier's page their purchase orders. Inactive
customers cannot be used on new documents ("That customer is inactive.").

---

## 9. Selling: Enquiry → Quotation → Order → Delivery → Invoice → Payment

```
Customer ─► Enquiry ─► Quotation ─► Sales order ─► Delivery ─► Invoice ─► Payment
            (cart)      (PDF)        (reserves)     (stock out)   (PDF)     (paid)
```

### Stage 1 -- Enquiry (what the customer asked for)
- **Start**: **Add to enquiry** on a catalogue result, a part page or a drawing. The part goes into **your enquiry cart**
  (only yours: "This enquiry cart belongs to another user.").
- **Cart** ("Parts collected for one customer request. Submit it to start a quotation."): columns Part number, Description,
  Vehicle, Qty; fields **Existing customer (optional)** or **Contact name** (one of them is needed: "Choose a customer or
  enter a contact name."), Phone, Email, **VIN / chassis number**, Notes; **Remove** an item; **Submit enquiry** (at least one
  part: "Add at least one part before submitting.").
- **Statuses**: `DRAFT` (the cart) → `SUBMITTED` → `QUOTED` (a quotation was made) / `CLOSED` / `CANCELLED`.
- **Permission**: `enquiries.write`. **Next**: open the enquiry, **Create quotation**.

### Stage 2 -- Quotation (the offer)
- **From an enquiry**: **Create quotation** (choose the customer if the enquiry has none: "Not listed? Add the customer first.").
  "Quotation lines are priced automatically from My Products when the part number matches a product you stock."
- **Directly**: *Quotations > New quotation* (Customer, lines; a free-text line for an item not in My Products) → **Save draft**.
- **Rules**: at least one line; every line needs a description and a price above zero; at most 200 lines; the valid-until date
  cannot be in the past (validity comes from Shop settings, "Quotation valid for (days)").
- **Statuses**: `DRAFT` → **Issue to customer** → `ISSUED` → **Customer accepted** → `ACCEPTED` or **Customer rejected** →
  `REJECTED`; `EXPIRED` -- set automatically when quotations are listed or opened after the valid-until date; `CANCELLED`. **Edit lines** only while draft.
- **PDF**: the quotation page has a PDF link (`/quotations/:id/pdf`); whether it is offered before issuing is NOT CONFIRMED.
- **Permission**: `quotations.write`. **Next**: **Create order**.

### Stage 3 -- Sales order
- **Create order** from an accepted quotation asks **"If there is not enough stock"**: *Do not create the order* or *Create it
  and back-order the shortfall*. The order **reserves** available stock.
- **Statuses**: `CONFIRMED` → `PARTIALLY_FULFILLED` → `FULFILLED` → `INVOICED`; `CANCELLED`.
- **Buttons**: **Reserve available stock** (try again for short lines), **Record delivery**, **Record return**, **Invoice delivered
  items**, **Cancel order** (releases reservations; a cancelled order cannot be invoiced).
- **Permission**: `orders.write`.

### Stage 4 -- Delivery
- **Record delivery**: "Enter the quantity delivered now for each line. Stock is deducted when you save." → **Save delivery**:
  a `SALE` movement; on hand and reserved go down. Nothing to deliver: "Nothing to fulfil."
- **Record return**: the quantity returned and where to put it (**Return to location**) → `RETURN_IN`.

### Stage 5 -- Invoice
- **Invoice delivered items** creates an invoice for what was delivered and not yet invoiced. Statuses: `ISSUED`,
  `PARTIALLY_PAID`, `PAID`, `VOID`. Due date from Shop settings ("Invoice due after (days)"). The invoice page has a PDF link (`/invoices/:id/pdf`).
- **Void** (with a **Reason**) cancels an invoice; a void invoice cannot take payments.
- **Permission**: `invoices.write`.

### Stage 6 -- Payment
- On the invoice, **Record payment**: **Amount** (the label shows the current balance), **Method** (Cash, Bank transfer, Card,
  Other), **Reference (receipt / transfer no.)**, **Notes**. The invoice becomes `PARTIALLY_PAID` or `PAID` ("This invoice is
  already paid in full." if you try again).
- "Payments are permanent records. To correct a mistake, contact an administrator."
- **Permission**: `payments.record`.

**Finding an old transaction:** each list (Enquiries, Quotations, Orders, Invoices & Payments, Purchase Orders) has a search box
and status filter; a customer's page lists their documents; *Invoices* can show **Unpaid only**.

---

## 10. Reports

*Insights > Reports* -- "Calculated live from your stock movements, invoices and payments." Choose a report and a period
(**From**, **To**). Each report needs its permission:

| Report | Permission |
|---|---|
| Stock on hand, Low stock | `reports.inventory` |
| Inventory valuation (cost) | `reports.financial` |
| Sales by month, Sales by product, Customer activity, Outstanding invoices, Quotation conversion | `reports.sales` |
| Supplier overview | `suppliers.read` |

---

## 11. Administration

- **Shop settings** (`settings.manage`): Shop name (required), Tax registration number, Phone, Email, Address, Currency, Default
  tax rate (%), Quotation valid for (days), Invoice due after (days), Standard quotation terms, Standard invoice notes →
  **Save settings**.
- **Users**: inside IntraForge, people, passwords and roles are **managed in IntraForge**. Adding or changing a user here is
  refused with: "People, passwords and roles are managed in IntraForge (Organization > Members and Roles)."
- **Audit log** (`audit.read`): who did what and when, with **Older / Newer** paging. The same events also appear in
  IntraForge's organization audit log (names starting with `spareparts.`).

---

## 12. Roles

Inside IntraForge, your Spare Parts permissions come from your IntraForge role (details: LEVEL1_ROLES.md):

| IntraForge role | Spare Parts role | In short |
|---|---|---|
| Organization Administrator / Spare Parts Manager | Admin (all) | Everything, including costs, reports, settings, audit |
| Spare Parts Sales | Sales | Catalogue, products (no cost), stock (look), customers, enquiries, quotations, orders, invoices, payments, sales reports |
| Spare Parts Inventory | Inventory | Catalogue, products incl. cost, stock changes, warehouses, suppliers (look), purchase orders, inventory reports |
| Spare Parts Viewer | Viewer | Look at catalogue, products and stock |

The server checks the permission for every action; hidden buttons are only a convenience.

---

## 13. Common messages

See LEVEL1_TROUBLESHOOTING.md for the full list of real messages and what to do.
