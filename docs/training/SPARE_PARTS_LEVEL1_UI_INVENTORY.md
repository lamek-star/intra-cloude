# Spare Parts Shop -- Level-1 UI inventory

Every page of the Spare Parts application as implemented on branch `intraforge/platform-integration` (commit `12d4d4b`), source `C:\Users\Hp\projects\spareparts-platform\src`. Inside IntraForge every route below is served under `https://localhost:8443/apps/spare-parts` (for example `/products` is `/apps/spare-parts/products`).

**How permissions work here.** Menu items are shown only with the permission named below (`ui/Shell.tsx`). Every server call is checked again on the server (`docs/generated/API_ROUTES.md` of the Spare Parts project). Inside IntraForge a person's permissions come from their IntraForge roles (`spare-parts-manager / -sales / -inventory / -viewer`, see LEVEL1_ROLES.md).

Generated from the code by an evidence extractor; counts are of controls found in the source. Marked **NOT CONFIRMED** where the code alone does not establish something.

## Dashboard (Business overview)

**ROUTE:** `/apps/spare-parts/`  
**PURPOSE:** Today's business at a glance, as your permissions allow: figures (Products, Low stock, Stock value at cost, Sales this month; Open enquiries, Open quotations, Open orders, Outstanding invoices) and panels New enquiries, Needs reordering and Unpaid invoices.  
**WHO USES IT:** Everyone  
**PERMISSION / CAPABILITY:** menu item shown with `settings.read`; controls shown with `catalogue.import`, `enquiries.read`, `reports.inventory`, `reports.sales`  
**SERVER CHECKS:** `GET /reports/dashboard` -> `settings.read`; `POST /dev/sample-data` -> `settings.manage`  
**HOW USER GETS THERE:** Menu > Overview > Dashboard (first page after Open)  
**BUTTONS:** Load sample data (development only)  
**TABLE 1:** columns Number | Contact | Received  (`app/(app)/page.tsx:148`)  
**TABLE 2:** columns Invoice | Customer | Overdue | Balance  (`app/(app)/page.tsx:196`)  
**ACTIONS:**  
- Load sample data (development only) -- Creates sample records (settings.manage). Not for a real shop.
**RELATED PAGES (links on the page):** `/inventory`, `/products`, `/catalogue/import`, `/enquiries`, `/enquiries/:id`, `/products/:id`, `/invoices`, `/invoices/:id`  
**NORMAL NEXT STEP:** Search the catalogue or open a list  
**EVIDENCE:** `app/(app)/page.tsx`

## Reference Catalogue

**ROUTE:** `/apps/spare-parts/catalogue`  
**PURPOSE:** Search the reference (OEM / supplier) parts catalogue by part number in any format, or browse with filters (manufacturer, model, engine, market, status...).  
**WHO USES IT:** Everyone with catalogue.read  
**PERMISSION / CAPABILITY:** menu item shown with `catalogue.read`; controls shown with `catalogue.import`, `enquiries.write`  
**SERVER CHECKS:** `GET /catalogue/stats` -> `catalogue.read`; `GET /catalogue/browse` -> `catalogue.read`; `POST /enquiries/items` -> `enquiries.write`  
**HOW USER GETS THERE:** Menu > Catalogue > Reference Catalogue  
**FIELDS:** Manufacturer (select); Model (text); Chassis / frame (select); Engine (select); Market (select); Part status (checkbox); Only parts that appear on a drawing (checkbox)  
**BUTTONS:** Search, Hide filters / Filters, Add to enquiry  
**TABLE 1:** columns Part number | Description | Fits | Drawings | Status | My Products  (`app/(app)/catalogue/page.tsx:261`)  
**TABLE 2:** columns No. | Part number | Description | Qty | Status  (`ui/catalogue.tsx:240`)  
**FILTERS / SEARCH:** search box "Part number (any format), description, vehicle or chassis…"; search box "e.g. AT151"; search box "Filter by number, name or callout"; filter Manufacturer; filter Model; filter Engine; filter Market; filter Part status; status filter (ACTIVE)  
**STATUSES:** ACTIVE  
**ACTIONS:**  
- Search -- Shows matching results.
- Hide filters / Filters -- Opens the filter panel.
- Add to enquiry -- Adds the part (with the vehicle, if known) to your current draft enquiry (enquiries.write); a message confirms it.
**RELATED PAGES (links on the page):** `/catalogue/import`, `/catalogue/parts/:id`, `/products/:id`  
**NORMAL NEXT STEP:** Open a part  
**EVIDENCE:** `app/(app)/catalogue/page.tsx`, `ui/catalogue.tsx`, `lib/basePath.ts`

## Reference part details

**ROUTE:** `/apps/spare-parts/catalogue/parts/[id]`  
**PURPOSE:** One reference part: description, numbers, fitment (vehicles), drawings, supersessions, source; whether it is already in My Products; import it to My Products; add it to an enquiry.  
**WHO USES IT:** Everyone with catalogue.read  
**PERMISSION / CAPABILITY:** controls shown with `catalogue.admin`, `enquiries.write`, `inventory.read`, `inventory.write`, `products.cost.read`, `products.read`, `products.write`, `suppliers.read`  
**SERVER CHECKS:** `GET /catalogue/parts/:id` -> `catalogue.read`; `PUT /catalogue/parts/:id/verification` -> `catalogue.admin`; `POST /catalogue/parts/:id/import-to-products` -> `products.write`; `POST /enquiries/items` -> `enquiries.write`; `POST /inventory/receive` -> `inventory.write`; `POST /inventory/adjust` -> `inventory.write`; `POST /inventory/transfer` -> `inventory.write`  
**HOW USER GETS THERE:** Catalogue > click a part number  
**FIELDS:** Your SKU (text, required, in dialog: Import … to My Products); Product name (text, required, in dialog: Import … to My Products); Selling price (money, in dialog: Import … to My Products); Cost price (money, in dialog: Import … to My Products); Reorder level (number, in dialog: Import … to My Products); Supplier (select, in dialog: Import … to My Products); Store in (select, in dialog: Import … to My Products); Quantity in stock now (number, in dialog: Import … to My Products); Verification (text); Location (select, in dialog: Receive stock — …); Quantity received (number, required, in dialog: Receive stock — …); Note (delivery note, source) (text, in dialog: Receive stock — …); Location (select, in dialog: Adjust stock — …); Change in quantity (number, required, in dialog: Adjust stock — …); Reason (textarea, required, in dialog: Adjust stock — …); From (select, in dialog: Transfer stock — …); To (select, in dialog: Transfer stock — …); Quantity (number, required, in dialog: Transfer stock — …); Note (text, in dialog: Transfer stock — …)  
**BUTTONS:** Add to enquiry, IMPORT TO MY PRODUCTS, Receive, Save adjustment, Transfer  
**TABLE 1:** columns Make | Model | Chassis | Engine | Production | Market | Catalogue / section | Notes | Source | Description | Status | Reference price (info only) | Recorded | Source record | External ID | Catalogue | Imported | Link  (`app/(app)/catalogue/parts/[id]/page.tsx:322`)  
**TABLE 2:** columns No. | Part number | Description | Qty | Status  (`ui/catalogue.tsx:240`)  
**FILTERS / SEARCH:** search box "Filter by number, name or callout"; status filter (ACTIVE)  
**DIALOGS:** Import … to My Products, Receive stock — …, Adjust stock — …, Transfer stock — …  
**STATUSES:** ACTIVE  
**ACTIONS:**  
- Add to enquiry -- Adds the part (with the vehicle, if known) to your current draft enquiry (enquiries.write); a message confirms it.
- IMPORT TO MY PRODUCTS -- Opens the import dialog (SKU, name, prices, reorder level, supplier, location, stock now); saving creates the product linked to the reference part (products.write).
- Receive -- Opens Receive stock: location, quantity received, note; saving adds a RECEIPT movement (inventory.write).
- Save adjustment -- Adds an ADJUSTMENT_IN / ADJUSTMENT_OUT movement; refused if it would drop below what is reserved.
- Transfer -- Opens Transfer stock: from, to (must differ), quantity (at most what is available there), note; saving adds TRANSFER_OUT and TRANSFER_IN.
**RELATED PAGES (links on the page):** `/products/:id`, `/catalogue/parts/:id`, `/catalogue/drawings/:id?part=:id`  
**NORMAL NEXT STEP:** IMPORT TO MY PRODUCTS or Add to enquiry  
**EVIDENCE:** `app/(app)/catalogue/parts/[id]/page.tsx`, `ui/catalogue.tsx`, `ui/stock.tsx`, `lib/basePath.ts`

## Drawing

**ROUTE:** `/apps/spare-parts/catalogue/drawings/[id]`  
**PURPOSE:** An exploded-view drawing with its numbered callouts and the parts on it.  
**WHO USES IT:** Everyone with catalogue.read  
**PERMISSION / CAPABILITY:** controls shown with `enquiries.write`  
**SERVER CHECKS:** `GET /catalogue/drawings/:id` -> `catalogue.read`; `POST /enquiries/items` -> `enquiries.write`  
**HOW USER GETS THERE:** Part details > a drawing  
**BUTTONS:** Add to enquiry  
**TABLE 1:** columns No. | Part number | Description | Qty | Status  (`ui/catalogue.tsx:240`)  
**FILTERS / SEARCH:** search box "Filter by number, name or callout"; status filter (ACTIVE)  
**DIALOGS:** DrawingViewer  
**STATUSES:** ACTIVE  
**ACTIONS:**  
- Add to enquiry -- Adds the part (with the vehicle, if known) to your current draft enquiry (enquiries.write); a message confirms it.
**RELATED PAGES (links on the page):** `/catalogue`, `/products/:id`, `/catalogue/parts/:id`  
**NORMAL NEXT STEP:** Open a part or add it to an enquiry  
**EVIDENCE:** `app/(app)/catalogue/drawings/[id]/page.tsx`, `ui/catalogue.tsx`, `lib/basePath.ts`

## Import reference catalogue

**ROUTE:** `/apps/spare-parts/catalogue/import`  
**PURPOSE:** Upload a CSV (or an offline catalogue package): detect columns, match them to catalogue fields, confirm you may use the data, preview every row, then import.  
**WHO USES IT:** Administrators (catalogue.import)  
**PERMISSION / CAPABILITY:** menu item shown with `catalogue.import`  
**SERVER CHECKS:** `GET /catalogue/import/jobs` -> `catalogue.import`  
**HOW USER GETS THERE:** Menu > Catalogue > Import  
**TABS:** CSV import, Offline package, History  
**FIELDS:** I confirm that my organisation is allowed to use this data. (checkbox); I confirm we are licensed to store and display the … image(s) in this package. Without this, images are skipped and only their source links are kept. (checkbox); Default manufacturer (text); Default source name (text); Default market (text)  
**BUTTONS:** Choose a different file / Choose CSV file, Checking… / Validate and preview, Choose a different package / Choose package file, Importing… / Import package  
**TABLE 1:** columns Table | Rows | Valid | Invalid | Level | Where | Message  (`app/(app)/catalogue/import/page.tsx:372`)  
**TABLE 2:** columns When | Type | Source | Status | Rows | New | Updated | Errors  (`app/(app)/catalogue/import/page.tsx:442`)  
**FILTERS / SEARCH:** filter I confirm we are licensed to store and display the … image(s) in this package. Without this, images are skipped and only their source links are kept.  
**ACTIONS:**  
- Choose a different file / Choose CSV file -- Reads the file and suggests a column match.
- Checking… / Validate and preview -- Every row is checked: new, already present, changed, duplicated or invalid; nothing is imported yet.
- Choose a different package / Choose package file -- Reads the package and shows what it contains.
- Importing… / Import package -- Imports parts, drawings (images only if licensed) (catalogue.import).
**RELATED PAGES (links on the page):** `/catalogue/import/:id`  
**NORMAL NEXT STEP:** Review the job and import  
**EVIDENCE:** `app/(app)/catalogue/import/page.tsx`

## Import job

**ROUTE:** `/apps/spare-parts/catalogue/import/[jobId]`  
**PURPOSE:** One import job: row-by-row status (new, updated, unchanged, invalid, duplicate...), counts, and the button to import or continue.  
**WHO USES IT:** Administrators  
**PERMISSION / CAPABILITY:** no menu item of its own (reached from another page)  
**SERVER CHECKS:** `GET /catalogue/import/jobs/:id` -> `catalogue.import`; `POST /catalogue/import/jobs/:id/commit` -> `catalogue.import`; `POST /catalogue/import/jobs/:id/cancel` -> `catalogue.import`; `PATCH /catalogue/import/jobs/:id/rows/:rowId` -> `catalogue.import`  
**HOW USER GETS THERE:** Import > after preview  
**BUTTONS:** Resume import, Include / Exclude  
**TABLE 1:** columns Table | New | Updated | Unchanged | Skipped | Level | Where | Message | Line | Part | Status | Will | Problems  (`app/(app)/catalogue/import/[jobId]/page.tsx:188`)  
**ACTIONS:**  
- Resume import -- Imports the rows still to do (safe to repeat).
- Include / Exclude -- The row is marked EXCLUDED.
**NORMAL NEXT STEP:** Search the imported parts  
**EVIDENCE:** `app/(app)/catalogue/import/[jobId]/page.tsx`

## My Products

**ROUTE:** `/apps/spare-parts/products`  
**PURPOSE:** The shop's own products (SKU, name, brand, category, prices, stock) with search and filters; create a product; receive / adjust / transfer stock.  
**WHO USES IT:** Everyone with products.read; inventory staff to change  
**PERMISSION / CAPABILITY:** menu item shown with `products.read`; controls shown with `inventory.read`, `products.cost.read`, `products.write`, `suppliers.read`  
**SERVER CHECKS:** `GET /products/categories` -> `products.read`; `POST /products` -> `products.write`; `POST /inventory/receive` -> `inventory.write`; `POST /inventory/adjust` -> `inventory.write`; `POST /inventory/transfer` -> `inventory.write`; `GET /products` -> `products.read`  
**HOW USER GETS THERE:** Menu > Inventory > My Products  
**FIELDS:** Low stock only (checkbox); Location (select, in dialog: Receive stock — …); Quantity received (number, required, in dialog: Receive stock — …); Note (delivery note, source) (text, in dialog: Receive stock — …); Location (select, in dialog: Adjust stock — …); Change in quantity (number, required, in dialog: Adjust stock — …); Reason (textarea, required, in dialog: Adjust stock — …); From (select, in dialog: Transfer stock — …); To (select, in dialog: Transfer stock — …); Quantity (number, required, in dialog: Transfer stock — …); Note (text, in dialog: Transfer stock — …); SKU (your own code) (text, required, in dialog: New product); Name (text, required, in dialog: New product); Brand (text, in dialog: New product); Manufacturer (text, in dialog: New product); Category (text, in dialog: New product); Condition (select, in dialog: New product); Selling price (money, in dialog: New product); Cost price (money, in dialog: New product); Reorder level (number, in dialog: New product); Unit (text, in dialog: New product); Description (textarea, in dialog: New product); Status (select, in dialog: New product); Default supplier (select, in dialog: New product); Opening stock location (select, in dialog: New product); Opening stock quantity (number, in dialog: New product)  
**BUTTONS:** New product, Receive, Save adjustment, Transfer  
**TABLE 1:** columns Product | Category | Available | On hand | Price | Cost | Status  (`app/(app)/products/page.tsx:81`)  
**FILTERS / SEARCH:** search box "Search name, SKU, brand or part number"; filter Low stock only; status filter (ACTIVE, INACTIVE)  
**DIALOGS:** New product, Receive stock — …, Adjust stock — …, Transfer stock — …  
**STATUSES:** ACTIVE, INACTIVE  
**ACTIONS:**  
- New product -- Opens the New product form (products.write); optional opening stock is recorded as an opening-balance movement.
- Receive -- Opens Receive stock: location, quantity received, note; saving adds a RECEIPT movement (inventory.write).
- Save adjustment -- Adds an ADJUSTMENT_IN / ADJUSTMENT_OUT movement; refused if it would drop below what is reserved.
- Transfer -- Opens Transfer stock: from, to (must differ), quantity (at most what is available there), note; saving adds TRANSFER_OUT and TRANSFER_IN.
**RELATED PAGES (links on the page):** `/products/:id`  
**NORMAL NEXT STEP:** Open a product  
**EVIDENCE:** `app/(app)/products/page.tsx`, `ui/ListPage.tsx`, `ui/stock.tsx`, `ui/productForm.ts`

## Product details

**ROUTE:** `/apps/spare-parts/products/[id]`  
**PURPOSE:** One shop product: details, prices (cost only with products.cost.read), photos, part numbers, suppliers, stock by location, movements, labels (barcode / QR), the linked reference part, history.  
**WHO USES IT:** Everyone with products.read  
**PERMISSION / CAPABILITY:** controls shown with `audit.read`, `catalogue.read`, `inventory.read`, `inventory.write`, `invoices.read`, `products.cost.read`, `products.write`, `suppliers.read`  
**SERVER CHECKS:** `GET /products/:id` -> `products.read`; `PATCH /products/:id` -> `products.write`; `PUT /products/:id/images/order` -> `products.write`; `PUT /products/:id/images/:imageId/primary` -> `products.write`; `DELETE /products/:id/images/:imageId` -> `products.write`; `DELETE /products/:id/suppliers/:linkId` -> `products.write`; `PUT /products/:id/suppliers` -> `products.write`; `DELETE /products/:id/numbers/:numberId` -> `products.write`; `DELETE /products/:id/reference-links/:linkId` -> `products.write`; `POST /products/:id/reference-links` -> `products.write`; `POST /products/:id/numbers` -> `products.write`; `POST /inventory/receive` -> `inventory.write`; `POST /inventory/adjust` -> `inventory.write`; `POST /inventory/transfer` -> `inventory.write`  
**HOW USER GETS THERE:** My Products > a product  
**TABS:** Overview, Fitment, Stock, Supplier, OEM Reference, Sales, History  
**FIELDS:** Supplier (select, in dialog: Supplier for this product); Supplier's part number (text, in dialog: Supplier for this product); Cost from this supplier (money, in dialog: Supplier for this product); Preferred supplier (checkbox, in dialog: Supplier for this product); Number (text, required, in dialog: Add part number); Type (select, in dialog: Add part number); Brand (text, in dialog: Add part number); Notes (text, in dialog: Add part number); Link to a reference part (text); Location (select, in dialog: Receive stock — …); Quantity received (number, required, in dialog: Receive stock — …); Note (delivery note, source) (text, in dialog: Receive stock — …); Location (select, in dialog: Adjust stock — …); Change in quantity (number, required, in dialog: Adjust stock — …); Reason (textarea, required, in dialog: Adjust stock — …); From (select, in dialog: Transfer stock — …); To (select, in dialog: Transfer stock — …); Quantity (number, required, in dialog: Transfer stock — …); Note (text, in dialog: Transfer stock — …); SKU (your own code) (text, required, in dialog: Edit product); Name (text, required, in dialog: Edit product); Brand (text, in dialog: Edit product); Manufacturer (text, in dialog: Edit product); Category (text, in dialog: Edit product); Condition (select, in dialog: Edit product); Selling price (money, in dialog: Edit product); Cost price (money, in dialog: Edit product); Reorder level (number, in dialog: Edit product); Unit (text, in dialog: Edit product); Description (textarea, in dialog: Edit product); Status (select, in dialog: Edit product); Default supplier (select, in dialog: Edit product); Opening stock location (select, in dialog: Edit product); Opening stock quantity (number, in dialog: Edit product)  
**BUTTONS:** Edit product, Uploading… / Add photos, Make primary, ← Earlier, Later →, Barcode label, QR label, Open to print, Receive, Transfer, Adjust, Add / update supplier, Add number, Save adjustment  
**TABLE 1:** columns Make | Model | Chassis | Engine | Production | Market | Section  (`app/(app)/products/[id]/page.tsx:497`)  
**TABLE 2:** columns Warehouse | Location | On hand | Reserved | Available | When | Type | Change | Note  (`app/(app)/products/[id]/page.tsx:583`)  
**TABLE 3:** columns Supplier | Their part number | Cost | Preferred  (`app/(app)/products/[id]/page.tsx:673`)  
**TABLE 4:** columns Number | Type | Brand | Source | Notes | Reference part | Linked  (`app/(app)/products/[id]/page.tsx:764`)  
**TABLE 5:** columns Invoice | Date | Customer | Qty | Unit price | Total  (`app/(app)/products/[id]/page.tsx:958`)  
**TABLE 6:** columns When | Who | What | Type | Change | Note  (`app/(app)/products/[id]/page.tsx:1020`)  
**FILTERS / SEARCH:** search box "Search by part number or description"; status filter (ACTIVE, LOW)  
**DIALOGS:** Edit product, Supplier for this product, Add part number, Receive stock — …, Adjust stock — …, Transfer stock — …  
**STATUSES:** ACTIVE, LOW  
**ACTIONS:**  
- Edit product -- Opens the product form (products.write; cost only with products.cost.read).
- Uploading… / Add photos -- PNG, JPEG, GIF or WebP; stored in IntraForge file storage (products.write).
- Make primary -- The photo becomes the first / primary one.
- ← Earlier -- Reorders the photos.
- Later → -- Reorders the photos.
- Barcode label -- Shows the barcode label for the product.
- QR label -- Shows the QR label for the product.
- Open to print -- Opens the label image; scanning it in Scan / Lookup opens this product.
- Receive -- Opens Receive stock: location, quantity received, note; saving adds a RECEIPT movement (inventory.write).
- Transfer -- Opens Transfer stock: from, to (must differ), quantity (at most what is available there), note; saving adds TRANSFER_OUT and TRANSFER_IN.
- Adjust -- Opens Adjust stock: location, change in quantity (+/-, non-zero), reason (required).
- Add / update supplier -- Opens Supplier for this product: supplier, their part number, cost from them, preferred.
- Add number -- Opens Add part number (number, type such as OEM, aftermarket, cross reference...). A number already on the product is refused.
- Save adjustment -- Adds an ADJUSTMENT_IN / ADJUSTMENT_OUT movement; refused if it would drop below what is reserved.
**RELATED PAGES (links on the page):** `/catalogue/parts/:id`, `/catalogue/drawings/:id?part=:id`, `/suppliers/:id`, `/invoices/:id`  
**NORMAL NEXT STEP:** Receive stock or add to a quotation  
**EVIDENCE:** `app/(app)/products/[id]/page.tsx`, `ui/stock.tsx`, `ui/productForm.ts`, `lib/basePath.ts`

## Stock & Locations

**ROUTE:** `/apps/spare-parts/inventory`  
**PURPOSE:** Stock levels per product and location; warehouses and their racks / shelves / bins; receive, adjust and transfer stock; movements.  
**WHO USES IT:** Inventory staff (inventory.read / write)  
**PERMISSION / CAPABILITY:** menu item shown with `inventory.read`; controls shown with `inventory.write`, `warehouses.write`  
**SERVER CHECKS:** `POST /warehouses` -> `warehouses.write`; `PATCH /warehouses/:id` -> `warehouses.write`; `POST /warehouses/:id/locations` -> `warehouses.write`; `GET /inventory/integrity` -> `inventory.read`; `POST /inventory/receive` -> `inventory.write`; `POST /inventory/adjust` -> `inventory.write`; `POST /inventory/transfer` -> `inventory.write`; `GET /inventory/movements` -> `inventory.read`  
**HOW USER GETS THERE:** Menu > Inventory > Stock & Locations  
**TABS:** Stock, Warehouses & locations, Movements, Integrity check  
**FIELDS:** Name (text, required, in dialog: New warehouse); Address (textarea, in dialog: New warehouse); Name (text, required, in dialog: Edit warehouse); Address (textarea, in dialog: Edit warehouse); Status (select, in dialog: Edit warehouse); Rack (text, in dialog: Add rack / shelf / bin); Shelf (text, in dialog: Add rack / shelf / bin); Bin (text, in dialog: Add rack / shelf / bin); Description (text, in dialog: Add rack / shelf / bin); Location (select, in dialog: Receive stock — …); Quantity received (number, required, in dialog: Receive stock — …); Note (delivery note, source) (text, in dialog: Receive stock — …); Location (select, in dialog: Adjust stock — …); Change in quantity (number, required, in dialog: Adjust stock — …); Reason (textarea, required, in dialog: Adjust stock — …); From (select, in dialog: Transfer stock — …); To (select, in dialog: Transfer stock — …); Quantity (number, required, in dialog: Transfer stock — …); Note (text, in dialog: Transfer stock — …)  
**BUTTONS:** New warehouse, Add rack / shelf / bin, Edit, Receive, Save adjustment, Transfer  
**TABLE 1:** columns Product | SKU | Warehouse | Location | On hand | Reserved | Available  (`app/(app)/inventory/page.tsx:129`)  
**TABLE 2:** columns Location code | Rack | Shelf | Bin | Description  (`app/(app)/inventory/page.tsx:213`)  
**TABLE 3:** columns When | Product | Type | Location | Change | Note  (`app/(app)/inventory/page.tsx:311`)  
**FILTERS / SEARCH:** search box "Search product, SKU or location"  
**DIALOGS:** New warehouse, Edit warehouse, Add rack / shelf / bin, Receive stock — …, Adjust stock — …, Transfer stock — …  
**ACTIONS:**  
- New warehouse -- Opens the New warehouse form (name, address) (warehouses.write).
- Add rack / shelf / bin -- Opens the form: rack, shelf, bin, description; the location code must be unique in the warehouse.
- Edit -- Opens a dialog with the current values.
- Receive -- Opens Receive stock: location, quantity received, note; saving adds a RECEIPT movement (inventory.write).
- Save adjustment -- Adds an ADJUSTMENT_IN / ADJUSTMENT_OUT movement; refused if it would drop below what is reserved.
- Transfer -- Opens Transfer stock: from, to (must differ), quantity (at most what is available there), note; saving adds TRANSFER_OUT and TRANSFER_IN.
**RELATED PAGES (links on the page):** `/products/:id`  
**NORMAL NEXT STEP:** Receive stock  
**EVIDENCE:** `app/(app)/inventory/page.tsx`, `ui/ListPage.tsx`, `ui/stock.tsx`

## Scan / Lookup

**ROUTE:** `/apps/spare-parts/scan`  
**PURPOSE:** Scan a barcode or QR label, or type a SKU or any part number and press Enter, to open the product.  
**WHO USES IT:** Everyone with products.read  
**PERMISSION / CAPABILITY:** menu item shown with `products.read`  
**SERVER CHECKS:** `GET /products/:id` -> `products.read`  
**HOW USER GETS THERE:** Menu > Inventory > Scan / Lookup (or the search box in the top bar)  
**FILTERS / SEARCH:** search box "Scan or type a code…"  
**RELATED PAGES (links on the page):** `/catalogue?q=:id`, `/products/:id`  
**NORMAL NEXT STEP:** The product opens  
**EVIDENCE:** `app/(app)/scan/page.tsx`

## Purchase Orders

**ROUTE:** `/apps/spare-parts/purchasing`  
**PURPOSE:** List of purchase orders to suppliers with their status; create a new one.  
**WHO USES IT:** Inventory / purchasing staff  
**PERMISSION / CAPABILITY:** menu item shown with `purchasing.read`; controls shown with `purchasing.write`  
**SERVER CHECKS:** `GET /purchase-orders` -> `purchasing.read`  
**HOW USER GETS THERE:** Menu > Inventory > Purchase Orders  
**TABLE 1:** columns Number | Created | Expected | Status | Total  (`app/(app)/purchasing/page.tsx:46`)  
**FILTERS / SEARCH:** search box "Search PO number"; status filter (CANCELLED, CLOSED, CONFIRMED, DRAFT, PARTIALLY_RECEIVED, RECEIVED)  
**STATUSES:** CANCELLED, CLOSED, CONFIRMED, DRAFT, PARTIALLY_RECEIVED, RECEIVED  
**RELATED PAGES (links on the page):** `/purchasing/new`, `/purchasing/:id`  
**NORMAL NEXT STEP:** New purchase order  
**EVIDENCE:** `app/(app)/purchasing/page.tsx`, `ui/ListPage.tsx`

## New purchase order

**ROUTE:** `/apps/spare-parts/purchasing/new`  
**PURPOSE:** Create a draft purchase order: supplier, expected date, lines.  
**WHO USES IT:** purchasing.write  
**PERMISSION / CAPABILITY:** no menu item of its own (reached from another page)  
**SERVER CHECKS:** `GET /suppliers` -> `suppliers.read`; `GET /warehouses` -> `inventory.read`; `POST /purchase-orders` -> `purchasing.write`  
**HOW USER GETS THERE:** Purchase Orders > New  
**FIELDS:** Supplier (select); Receive into (select); Expected date (date); Notes (text)  
**BUTTONS:** Save draft, Remove line, Add a free-text line  
**FILTERS / SEARCH:** search box "Description (item not in My Products)"  
**ACTIONS:**  
- Save draft -- Creates a DRAFT quotation / purchase order (at least one line; every line needs a description and a price above zero).
- Remove line -- The line is removed from the draft.
- Add a free-text line -- Adds an empty line to fill in.
**NORMAL NEXT STEP:** Confirm it  
**EVIDENCE:** `app/(app)/purchasing/new/page.tsx`, `ui/lines.tsx`

## Purchase order

**ROUTE:** `/apps/spare-parts/purchasing/[id]`  
**PURPOSE:** One purchase order: confirm it, receive the goods that arrived (stock increases), see what is outstanding.  
**WHO USES IT:** Inventory / purchasing staff  
**PERMISSION / CAPABILITY:** controls shown with `inventory.write`, `purchasing.write`  
**SERVER CHECKS:** `GET /purchase-orders/:id` -> `purchasing.read`; `POST /purchase-orders/:id/receive` -> `purchasing.write`  
**HOW USER GETS THERE:** Purchase Orders > a PO  
**BUTTONS:** Confirm, Receive goods, Receive into stock  
**TABLE 1:** columns Product | Ordered | Received | Unit cost | Total  (`app/(app)/purchasing/[id]/page.tsx:173`)  
**TABLE 2:** columns Item | Qty | Unit price | Disc. | Total  (`ui/doc.tsx:31`)  
**DIALOGS:** Receive goods  
**ACTIONS:**  
- Confirm -- Status DRAFT -> CONFIRMED (purchasing.write).
- Receive goods -- Opens a dialog with the quantity received per line (pre-filled with what is outstanding).
- Receive into stock -- Stock on hand increases (RECEIPT movements); PO becomes PARTIALLY_RECEIVED or RECEIVED.
**RELATED PAGES (links on the page):** `/suppliers/:id`, `/products/:id`  
**NORMAL NEXT STEP:** Receive goods  
**EVIDENCE:** `app/(app)/purchasing/[id]/page.tsx`, `ui/doc.tsx`

## Enquiries

**ROUTE:** `/apps/spare-parts/enquiries`  
**PURPOSE:** Customer enquiries (what a customer asked for) with status; open one to quote it.  
**WHO USES IT:** Sales staff  
**PERMISSION / CAPABILITY:** menu item shown with `enquiries.read`; controls shown with `enquiries.write`  
**SERVER CHECKS:** `GET /enquiries` -> `enquiries.read`  
**HOW USER GETS THERE:** Menu > Sales > Enquiries  
**TABLE 1:** columns Number | Contact | Email | Items | Submitted | Status  (`app/(app)/enquiries/page.tsx:39`)  
**FILTERS / SEARCH:** search box "Search number, contact, part number"; status filter (CANCELLED, CLOSED, QUOTED, SUBMITTED)  
**STATUSES:** CANCELLED, CLOSED, QUOTED, SUBMITTED  
**RELATED PAGES (links on the page):** `/enquiries/cart`, `/enquiries/:id`  
**NORMAL NEXT STEP:** Open an enquiry  
**EVIDENCE:** `app/(app)/enquiries/page.tsx`, `ui/ListPage.tsx`

## Enquiry cart

**ROUTE:** `/apps/spare-parts/enquiries/cart`  
**PURPOSE:** Your current, not yet submitted enquiry: the parts you added from the catalogue or products; choose the customer / contact and submit.  
**WHO USES IT:** Sales staff  
**PERMISSION / CAPABILITY:** no menu item of its own (reached from another page)  
**SERVER CHECKS:** `GET /enquiries/current` -> `enquiries.read`; `GET /customers` -> `customers.read`; `DELETE /enquiries/:id/items/:itemId` -> `enquiries.write`; `POST /enquiries/:id/submit` -> `enquiries.write`  
**HOW USER GETS THERE:** Add to enquiry (catalogue, part, drawing) > the cart  
**FIELDS:** Existing customer (optional) (select); Contact name (text, required); Email (email); Phone (text); VIN / chassis number (text); Notes (textarea)  
**BUTTONS:** Remove, Submit enquiry  
**TABLE 1:** columns Part number | Description | Vehicle | Qty  (`app/(app)/enquiries/cart/page.tsx:76`)  
**ACTIONS:**  
- Remove -- The item is removed from your cart.
- Submit enquiry -- The draft enquiry becomes SUBMITTED; needs at least one part and a customer or contact name.
**RELATED PAGES (links on the page):** `/catalogue/parts/:id`  
**NORMAL NEXT STEP:** Submit enquiry  
**EVIDENCE:** `app/(app)/enquiries/cart/page.tsx`

## Enquiry

**ROUTE:** `/apps/spare-parts/enquiries/[id]`  
**PURPOSE:** One submitted enquiry: its items and customer; create a quotation from it (lines are priced from My Products when the part number matches).  
**WHO USES IT:** Sales staff  
**PERMISSION / CAPABILITY:** controls shown with `customers.read`, `enquiries.write`, `quotations.write`  
**SERVER CHECKS:** `GET /enquiries/:id` -> `enquiries.read`; `POST /enquiries/:id/quotation` -> `quotations.write`; `POST /enquiries/:id/cancel` -> `enquiries.write`  
**HOW USER GETS THERE:** Enquiries > an enquiry  
**FIELDS:** Customer (select, in dialog: Create quotation)  
**BUTTONS:** Create quotation  
**TABLE 1:** columns Part number | Description | Vehicle | Qty  (`app/(app)/enquiries/[id]/page.tsx:126`)  
**DIALOGS:** Create quotation  
**ACTIONS:**  
- Create quotation -- Creates a DRAFT quotation; lines are priced automatically from My Products where the part number matches a product you stock; the enquiry becomes QUOTED.
**RELATED PAGES (links on the page):** `/catalogue/parts/:id`, `/customers`  
**NORMAL NEXT STEP:** Create quotation  
**EVIDENCE:** `app/(app)/enquiries/[id]/page.tsx`

## Quotations

**ROUTE:** `/apps/spare-parts/quotations`  
**PURPOSE:** Quotations with status (draft, issued, accepted, rejected, expired, cancelled); create one.  
**WHO USES IT:** Sales staff  
**PERMISSION / CAPABILITY:** menu item shown with `quotations.read`; controls shown with `quotations.write`  
**SERVER CHECKS:** `GET /quotations` -> `quotations.read`  
**HOW USER GETS THERE:** Menu > Sales > Quotations  
**TABLE 1:** columns Number | Created | Valid until | Status | Total  (`app/(app)/quotations/page.tsx:46`)  
**FILTERS / SEARCH:** search box "Search quotation number"; status filter (ACCEPTED, CANCELLED, DRAFT, EXPIRED, ISSUED, REJECTED)  
**STATUSES:** ACCEPTED, CANCELLED, DRAFT, EXPIRED, ISSUED, REJECTED  
**RELATED PAGES (links on the page):** `/quotations/new`, `/quotations/:id`  
**NORMAL NEXT STEP:** Open a quotation  
**EVIDENCE:** `app/(app)/quotations/page.tsx`, `ui/ListPage.tsx`

## New quotation

**ROUTE:** `/apps/spare-parts/quotations/new`  
**PURPOSE:** Create a draft quotation directly (customer, lines, validity).  
**WHO USES IT:** Sales staff  
**PERMISSION / CAPABILITY:** no menu item of its own (reached from another page)  
**SERVER CHECKS:** `GET /customers` -> `customers.read`; `POST /quotations` -> `quotations.write`  
**HOW USER GETS THERE:** Quotations > New  
**FIELDS:** Customer (select)  
**BUTTONS:** Save draft, Remove line, Add a free-text line  
**FILTERS / SEARCH:** search box "Description (item not in My Products)"  
**ACTIONS:**  
- Save draft -- Creates a DRAFT quotation / purchase order (at least one line; every line needs a description and a price above zero).
- Remove line -- The line is removed from the draft.
- Add a free-text line -- Adds an empty line to fill in.
**NORMAL NEXT STEP:** Issue it  
**EVIDENCE:** `app/(app)/quotations/new/page.tsx`, `ui/lines.tsx`

## Quotation

**ROUTE:** `/apps/spare-parts/quotations/[id]`  
**PURPOSE:** One quotation: edit lines while draft, issue it to the customer (PDF), mark accepted or rejected, cancel, create the order.  
**WHO USES IT:** Sales staff  
**PERMISSION / CAPABILITY:** controls shown with `orders.write`, `quotations.write`  
**SERVER CHECKS:** `GET /quotations/:id` -> `quotations.read`; `PATCH /quotations/:id` -> `quotations.write`; `POST /quotations/:id/order` -> `orders.write`  
**HOW USER GETS THERE:** Quotations > a quotation  
**FIELDS:** If there is not enough stock (select, in dialog: Create order)  
**BUTTONS:** Edit lines, Issue to customer, Customer accepted, Customer rejected, Create order, Cancel, Save, Remove line, Add a free-text line  
**TABLE 1:** columns Item | Qty | Unit price | Disc. | Total  (`ui/doc.tsx:31`)  
**FILTERS / SEARCH:** search box "Description (item not in My Products)"  
**DIALOGS:** Edit …, Create order  
**ACTIONS:**  
- Edit lines -- Opens the line editor.
- Issue to customer -- Status DRAFT -> ISSUED (valid-until date must not be in the past); the PDF can be printed / sent.
- Customer accepted -- Status ISSUED -> ACCEPTED.
- Customer rejected -- Status ISSUED -> REJECTED.
- Create order -- Opens a dialog asking what to do if stock is short (Do not create the order / Create it and back-order the shortfall); creating the order reserves available stock.
- Cancel -- Nothing is saved.
- Save -- The values are sent to the server and validated; on success the dialog closes and the list refreshes; on a validation error the message is shown and nothing is saved.
- Remove line -- The line is removed from the draft.
- Add a free-text line -- Adds an empty line to fill in.
**RELATED PAGES (links on the page):** `/customers/:id`, `/enquiries/:id`, `/products/:id`  
**NORMAL NEXT STEP:** Customer accepted > Create order  
**EVIDENCE:** `app/(app)/quotations/[id]/page.tsx`, `ui/doc.tsx`, `ui/lines.tsx`, `lib/basePath.ts`

## Orders

**ROUTE:** `/apps/spare-parts/orders`  
**PURPOSE:** Sales orders with status (confirmed, partially fulfilled, fulfilled, invoiced, cancelled).  
**WHO USES IT:** Sales staff  
**PERMISSION / CAPABILITY:** menu item shown with `orders.read`  
**SERVER CHECKS:** `GET /orders` -> `orders.read`  
**HOW USER GETS THERE:** Menu > Sales > Orders  
**TABLE 1:** columns Number | Created | Status | Total  (`app/(app)/orders/page.tsx:35`)  
**FILTERS / SEARCH:** search box "Search order number"; status filter (CANCELLED, CONFIRMED, FULFILLED, INVOICED, PARTIALLY_FULFILLED)  
**STATUSES:** CANCELLED, CONFIRMED, FULFILLED, INVOICED, PARTIALLY_FULFILLED  
**RELATED PAGES (links on the page):** `/orders/:id`  
**NORMAL NEXT STEP:** Open an order  
**EVIDENCE:** `app/(app)/orders/page.tsx`, `ui/ListPage.tsx`

## Sales order

**ROUTE:** `/apps/spare-parts/orders/[id]`  
**PURPOSE:** One order: reserve available stock, record delivery (stock goes out), record returns, invoice the delivered items, cancel.  
**WHO USES IT:** Sales staff  
**PERMISSION / CAPABILITY:** controls shown with `inventory.read`, `invoices.write`, `orders.write`  
**SERVER CHECKS:** `GET /orders/:id` -> `orders.read`; `POST /orders/:id/fulfil` -> `orders.write`; `POST /orders/:id/invoice` -> `invoices.write`; `POST /orders/:id/reserve` -> `orders.write`; `POST /orders/:id/cancel` -> `orders.write`; `POST /orders/:id/return` -> `orders.write`  
**HOW USER GETS THERE:** Orders > an order  
**FIELDS:** Item (select, in dialog: Record return); Quantity returned (number, required, in dialog: Record return); Return to location (select, in dialog: Record return); Reason (textarea, required, in dialog: Record return)  
**BUTTONS:** Record delivery, Invoice delivered items, Record return, Reserve available stock, Cancel order, Save delivery  
**TABLE 1:** columns Delivered | Returned | Invoiced  (`app/(app)/orders/[id]/page.tsx:202`)  
**TABLE 2:** columns Item | Qty | Unit price | Disc. | Total  (`ui/doc.tsx:31`)  
**DIALOGS:** Record delivery, Record return  
**ACTIONS:**  
- Record delivery -- Opens a dialog with the quantity delivered now per line (pre-filled with what remains).
- Invoice delivered items -- Creates an ISSUED invoice for the delivered, not yet invoiced quantities; order becomes INVOICED when all is invoiced.
- Record return -- Opens / saves the return: quantity returned and the location to put it back (RETURN_IN movement).
- Reserve available stock -- Reserves what is now available for the order.
- Cancel order -- Status -> CANCELLED; reservations are released. A cancelled order cannot be invoiced.
- Save delivery -- Stock on hand and reserved go down (SALE movement); order becomes PARTIALLY_FULFILLED or FULFILLED.
**RELATED PAGES (links on the page):** `/customers/:id`, `/quotations/:id`, `/products/:id`  
**NORMAL NEXT STEP:** Record delivery > Invoice delivered items  
**EVIDENCE:** `app/(app)/orders/[id]/page.tsx`, `ui/doc.tsx`

## Invoices & Payments

**ROUTE:** `/apps/spare-parts/invoices`  
**PURPOSE:** Invoices with status (issued, partially paid, paid, void) and outstanding balance.  
**WHO USES IT:** Sales staff  
**PERMISSION / CAPABILITY:** menu item shown with `invoices.read`  
**SERVER CHECKS:** `GET /invoices` -> `invoices.read`  
**HOW USER GETS THERE:** Menu > Sales > Invoices & Payments  
**FIELDS:** Unpaid only (checkbox)  
**TABLE 1:** columns Number | Issued | Due | Status | Total | Balance  (`app/(app)/invoices/page.tsx:43`)  
**FILTERS / SEARCH:** search box "Search invoice number"; filter Unpaid only; status filter (ISSUED, PAID, PARTIALLY_PAID, VOID)  
**STATUSES:** ISSUED, PAID, PARTIALLY_PAID, VOID  
**RELATED PAGES (links on the page):** `/invoices/:id`  
**NORMAL NEXT STEP:** Open an invoice  
**EVIDENCE:** `app/(app)/invoices/page.tsx`, `ui/ListPage.tsx`

## Invoice

**ROUTE:** `/apps/spare-parts/invoices/[id]`  
**PURPOSE:** One invoice: lines, totals, payments; record a payment, print / PDF, void.  
**WHO USES IT:** Sales staff (payments.record to pay)  
**PERMISSION / CAPABILITY:** controls shown with `invoices.write`, `payments.record`  
**SERVER CHECKS:** `GET /invoices/:id` -> `invoices.read`; `POST /invoices/:id/payments` -> `payments.record`; `POST /invoices/:id/void` -> `invoices.write`  
**HOW USER GETS THERE:** Invoices > an invoice  
**FIELDS:** Method (select, in dialog: Record payment); Reference (receipt / transfer no.) (text, in dialog: Record payment); Notes (textarea, in dialog: Record payment); Reason (textarea, required, in dialog: Void invoice)  
**BUTTONS:** Record payment, Void, Void invoice  
**TABLE 1:** columns Date | Method | Reference | Amount  (`app/(app)/invoices/[id]/page.tsx:155`)  
**TABLE 2:** columns Item | Qty | Unit price | Disc. | Total  (`ui/doc.tsx:31`)  
**DIALOGS:** Record payment, Void invoice  
**ACTIONS:**  
- Record payment -- Opens the payment form (Amount -- the label shows the current balance --, Method Cash / Bank transfer / Card / Other, Reference, Notes); saving adds the payment: invoice becomes PARTIALLY_PAID or PAID (payments.record).
- Void -- Opens the Void invoice dialog.
- Void invoice -- Asks for a Reason; status -> VOID; a void invoice cannot take payments.
**RELATED PAGES (links on the page):** `/customers/:id`, `/orders/:id`, `/products/:id`  
**NORMAL NEXT STEP:** Record payment  
**EVIDENCE:** `app/(app)/invoices/[id]/page.tsx`, `ui/doc.tsx`, `lib/basePath.ts`

## Customers

**ROUTE:** `/apps/spare-parts/customers`  
**PURPOSE:** Customer list with search and status; create a customer.  
**WHO USES IT:** Sales staff  
**PERMISSION / CAPABILITY:** menu item shown with `customers.read`; controls shown with `customers.write`  
**SERVER CHECKS:** `POST /customers` -> `customers.write`; `GET /customers` -> `customers.read`  
**HOW USER GETS THERE:** Menu > Contacts > Customers  
**FIELDS:** Status (select, in dialog: New customer); Name (text, required, in dialog: New customer); Contact person (text, in dialog: New customer); Phone (text, in dialog: New customer); Email (email, in dialog: New customer); Country (text, in dialog: New customer); Tax number (text, in dialog: New customer); Currency (text, in dialog: New customer); Payment terms (text, in dialog: New customer); Notes (textarea, in dialog: New customer); Billing address (textarea, in dialog: New customer); Shipping address (textarea, in dialog: New customer); Credit limit (money, in dialog: New customer)  
**BUTTONS:** New customer  
**TABLE 1:** columns Code | Name | Contact | Phone | Email | Status  (`app/(app)/customers/page.tsx:40`)  
**FILTERS / SEARCH:** search box "Search name, code, phone or email"; status filter (ACTIVE, INACTIVE)  
**DIALOGS:** New customer  
**STATUSES:** ACTIVE, INACTIVE  
**ACTIONS:**  
- New customer -- Opens the New customer form (customers.write).
**RELATED PAGES (links on the page):** `/customers/:id`  
**NORMAL NEXT STEP:** Open a customer  
**EVIDENCE:** `app/(app)/customers/page.tsx`, `ui/ListPage.tsx`, `ui/parties.ts`

## Customer

**ROUTE:** `/apps/spare-parts/customers/[id]`  
**PURPOSE:** One customer: details and their quotations, orders and invoices; edit.  
**WHO USES IT:** Sales staff  
**PERMISSION / CAPABILITY:** controls shown with `customers.write`, `invoices.read`, `orders.read`, `quotations.read`  
**SERVER CHECKS:** `GET /customers/:id` -> `customers.read`; `PATCH /customers/:id` -> `customers.write`  
**HOW USER GETS THERE:** Customers > a customer  
**FIELDS:** Status (select, in dialog: Edit customer); Name (text, required, in dialog: Edit customer); Contact person (text, in dialog: Edit customer); Phone (text, in dialog: Edit customer); Email (email, in dialog: Edit customer); Country (text, in dialog: Edit customer); Tax number (text, in dialog: Edit customer); Currency (text, in dialog: Edit customer); Payment terms (text, in dialog: Edit customer); Notes (textarea, in dialog: Edit customer); Billing address (textarea, in dialog: Edit customer); Shipping address (textarea, in dialog: Edit customer); Credit limit (money, in dialog: Edit customer)  
**BUTTONS:** Edit  
**TABLE 1:** columns Number | Date | Status | Total | Balance  (`app/(app)/customers/[id]/page.tsx:78`)  
**DIALOGS:** Edit customer  
**ACTIONS:**  
- Edit -- Opens a dialog with the current values.
**NORMAL NEXT STEP:** Create a quotation  
**EVIDENCE:** `app/(app)/customers/[id]/page.tsx`, `ui/parties.ts`

## Suppliers

**ROUTE:** `/apps/spare-parts/suppliers`  
**PURPOSE:** Supplier list with search and status; create a supplier.  
**WHO USES IT:** Inventory / purchasing staff  
**PERMISSION / CAPABILITY:** menu item shown with `suppliers.read`; controls shown with `suppliers.write`  
**SERVER CHECKS:** `POST /suppliers` -> `suppliers.write`; `GET /suppliers` -> `suppliers.read`  
**HOW USER GETS THERE:** Menu > Contacts > Suppliers  
**FIELDS:** Status (select, in dialog: New supplier); Name (text, required, in dialog: New supplier); Contact person (text, in dialog: New supplier); Phone (text, in dialog: New supplier); Email (email, in dialog: New supplier); Country (text, in dialog: New supplier); Tax number (text, in dialog: New supplier); Currency (text, in dialog: New supplier); Payment terms (text, in dialog: New supplier); Notes (textarea, in dialog: New supplier); Billing address (textarea, in dialog: New supplier); Shipping address (textarea, in dialog: New supplier); Credit limit (money, in dialog: New supplier)  
**BUTTONS:** New supplier  
**TABLE 1:** columns Code | Name | Contact | Phone | Email | Status  (`app/(app)/suppliers/page.tsx:40`)  
**FILTERS / SEARCH:** search box "Search name, code, phone or email"; status filter (ACTIVE, INACTIVE)  
**DIALOGS:** New supplier  
**STATUSES:** ACTIVE, INACTIVE  
**ACTIONS:**  
- New supplier -- Opens the New supplier form (suppliers.write).
**RELATED PAGES (links on the page):** `/suppliers/:id`  
**NORMAL NEXT STEP:** Open a supplier  
**EVIDENCE:** `app/(app)/suppliers/page.tsx`, `ui/ListPage.tsx`, `ui/parties.ts`

## Supplier

**ROUTE:** `/apps/spare-parts/suppliers/[id]`  
**PURPOSE:** One supplier: details and purchase orders; edit.  
**WHO USES IT:** Inventory / purchasing staff  
**PERMISSION / CAPABILITY:** controls shown with `purchasing.read`, `suppliers.write`  
**SERVER CHECKS:** `GET /suppliers/:id` -> `suppliers.read`; `PATCH /suppliers/:id` -> `suppliers.write`  
**HOW USER GETS THERE:** Suppliers > a supplier  
**FIELDS:** Status (select, in dialog: Edit supplier); Name (text, required, in dialog: Edit supplier); Contact person (text, in dialog: Edit supplier); Phone (text, in dialog: Edit supplier); Email (email, in dialog: Edit supplier); Country (text, in dialog: Edit supplier); Tax number (text, in dialog: Edit supplier); Currency (text, in dialog: Edit supplier); Payment terms (text, in dialog: Edit supplier); Notes (textarea, in dialog: Edit supplier); Billing address (textarea, in dialog: Edit supplier); Shipping address (textarea, in dialog: Edit supplier); Credit limit (money, in dialog: Edit supplier)  
**BUTTONS:** Edit  
**TABLE 1:** columns Number | Date | Status | Total  (`app/(app)/suppliers/[id]/page.tsx:101`)  
**DIALOGS:** Edit supplier  
**ACTIONS:**  
- Edit -- Opens a dialog with the current values.
**RELATED PAGES (links on the page):** `/purchasing/:id`  
**NORMAL NEXT STEP:** New purchase order  
**EVIDENCE:** `app/(app)/suppliers/[id]/page.tsx`, `ui/parties.ts`

## Reports

**ROUTE:** `/apps/spare-parts/reports`  
**PURPOSE:** Nine live reports, each shown only with its permission: Stock on hand, Low stock, Inventory valuation (cost), Sales by month, Sales by product, Customer activity, Outstanding invoices, Quotation conversion, Supplier overview; a From / To period.  
**WHO USES IT:** Managers; sales / inventory staff for their reports  
**PERMISSION / CAPABILITY:** menu item shown with `settings.read`  
**HOW USER GETS THERE:** Menu > Insights > Reports  
**FIELDS:** From (date); To (text)  
**NORMAL NEXT STEP:** --  
**EVIDENCE:** `app/(app)/reports/page.tsx`, `lib/basePath.ts`

## Users

**ROUTE:** `/apps/spare-parts/admin/users`  
**PURPOSE:** Who has access. Inside IntraForge, people, passwords and roles are managed in IntraForge (Organization > Members and Roles); adding or changing users here is refused with that message.  
**WHO USES IT:** Managers (users.manage)  
**PERMISSION / CAPABILITY:** menu item shown with `users.manage`  
**SERVER CHECKS:** `GET /users` -> `users.manage`; `PATCH /users/:id` -> `users.manage`; `POST /users` -> `users.manage`  
**HOW USER GETS THERE:** Menu > Administration > Users  
**FIELDS:** Name (text, required, in dialog: Add user); Email (used to sign in) (email, required, in dialog: Add user); Role (select, in dialog: Add user); Temporary password (password, required, in dialog: Add user); Name (text, required, in dialog: Edit …); Role (select, in dialog: Edit …); New temporary password (password, required, in dialog: Reset password — …)  
**BUTTONS:** Add user, Edit, Reset password, Disable, Enable  
**TABLE 1:** columns Name | Email | Role | Status | Last sign-in  (`app/(app)/admin/users/page.tsx:55`)  
**DIALOGS:** Add user, Edit …, Reset password — …  
**ACTIONS:**  
- Add user -- Inside IntraForge the server answers: "People, passwords and roles are managed in IntraForge (Organization > Members and Roles)."
- Edit -- Opens a dialog with the current values.
- Reset password -- Inside IntraForge: refused, managed in IntraForge.
- Disable -- Inside IntraForge: refused, managed in IntraForge.
- Enable -- Inside IntraForge: refused, managed in IntraForge.
**NORMAL NEXT STEP:** Manage people in IntraForge  
**EVIDENCE:** `app/(app)/admin/users/page.tsx`

## Shop settings

**ROUTE:** `/apps/spare-parts/admin/settings`  
**PURPOSE:** Shop name, tax registration number, phone, email, address, currency, default tax rate, how many days a quotation is valid, after how many days an invoice is due, and the standard quotation terms and invoice notes printed on documents.  
**WHO USES IT:** Managers (settings.manage)  
**PERMISSION / CAPABILITY:** menu item shown with `settings.manage`  
**SERVER CHECKS:** `GET /settings` -> `settings.read`; `PUT /settings` -> `settings.manage`  
**HOW USER GETS THERE:** Menu > Administration > Shop settings  
**FIELDS:** Shop name (text, required); Tax registration number (text); Phone (text); Email (email); Address (textarea); Currency (text); Default tax rate (%) (text); Quotation valid for (days) (text); Invoice due after (days) (text); Standard quotation terms (textarea); Standard invoice notes (textarea)  
**BUTTONS:** Save settings  
**ACTIONS:**  
- Save settings -- Settings are saved (settings.manage) and used on new documents.
**NORMAL NEXT STEP:** --  
**EVIDENCE:** `app/(app)/admin/settings/page.tsx`

## Audit log (Spare Parts)

**ROUTE:** `/apps/spare-parts/admin/audit`  
**PURPOSE:** The application's own history: who did what and when (also relayed to IntraForge's audit log).  
**WHO USES IT:** Managers (audit.read)  
**PERMISSION / CAPABILITY:** menu item shown with `audit.read`  
**HOW USER GETS THERE:** Menu > Administration > Audit log  
**BUTTONS:** Newer, Older  
**TABLE 1:** columns When | Who | Action | What  (`app/(app)/admin/audit/page.tsx:67`)  
**ACTIONS:**  
- Newer -- Pages back towards the most recent.
- Older -- Pages to earlier entries.
**NORMAL NEXT STEP:** --  
**EVIDENCE:** `app/(app)/admin/audit/page.tsx`
