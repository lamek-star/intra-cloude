# Spare Parts Shop -- table reference (Level 1)

Every table found in the code with every column. Formulas are stated only where the code implements them.

List pages (`ui/ListPage.tsx`) all work the same way: a search box, a status filter where the list has statuses, pages of results with **Older / Newer** style paging, and the newest items first. Clicking the name / number opens the record.

## Page: Dashboard (Business overview) (`/`)

### Table 1 on Dashboard (Business overview)

- **Columns:** Number | Contact | Received
- **Search / filter:** none on this page
- **Source evidence:** `app/(app)/page.tsx:148`

  - **Number:** Document number (for example ENQ-, QUO-, ORD-/SO-, INV-, PO-).
  - **Contact:** Contact person.
  - **Received:** Received date / quantity received.

### Table 2 on Dashboard (Business overview)

- **Columns:** Invoice | Customer | Overdue | Balance
- **Search / filter:** none on this page
- **Source evidence:** `app/(app)/page.tsx:196`

  - **Invoice:** Invoice number.
  - **Customer:** Customer of the document.
  - **Overdue:** How overdue an unpaid invoice is.
  - **Balance:** Amount still unpaid on the invoice.

## Page: Audit log (Spare Parts) (`/admin/audit`)

### Table 1 on Audit log (Spare Parts)

- **Columns:** When | Who | Action | What
- **Search / filter:** none on this page
- **Source evidence:** `app/(app)/admin/audit/page.tsx:67`

  - **When:** Date and time it happened.
  - **Who:** The user who did it.
  - **Action:** The action.
  - **What:** The action.

## Page: Users (`/admin/users`)

### Table 1 on Users

- **Columns:** Name | Email | Role | Status | Last sign-in
- **Search / filter:** none on this page
- **Source evidence:** `app/(app)/admin/users/page.tsx:55`

  - **Name:** Name.
  - **Email:** Email.
  - **Role:** The user's role.
  - **Status:** Current status (see the status list of the document).
  - **Last sign-in:** When the user last signed in.

## Page: Reference Catalogue (`/catalogue`)

### Table 1 on Reference Catalogue

- **Columns:** Part number | Description | Fits | Drawings | Status | My Products
- **Search / filter:** Part number (any format), description, vehicle or chassis…; e.g. AT151; Filter by number, name or callout; status filter: ACTIVE
- **Source evidence:** `app/(app)/catalogue/page.tsx:261`

  - **Part number:** Part number (OEM or other).
  - **Description:** Description text.
  - **Fits:** Vehicles the part fits.
  - **Drawings:** Drawings the part appears on.
  - **Status:** Current status (see the status list of the document).
  - **My Products:** Whether / which shop product is linked to this reference part.

### Table 2 on Reference Catalogue

- **Columns:** No. | Part number | Description | Qty | Status
- **Search / filter:** Part number (any format), description, vehicle or chassis…; e.g. AT151; Filter by number, name or callout; status filter: ACTIVE
- **Source evidence:** `ui/catalogue.tsx:240`

  - **No.:** Callout number on the drawing.
  - **Part number:** Part number (OEM or other).
  - **Description:** Description text.
  - **Qty:** Quantity.
  - **Status:** Current status (see the status list of the document).

## Page: Drawing (`/catalogue/drawings/[id]`)

### Table 1 on Drawing

- **Columns:** No. | Part number | Description | Qty | Status
- **Search / filter:** Filter by number, name or callout; status filter: ACTIVE
- **Source evidence:** `ui/catalogue.tsx:240`

  - **No.:** Callout number on the drawing.
  - **Part number:** Part number (OEM or other).
  - **Description:** Description text.
  - **Qty:** Quantity.
  - **Status:** Current status (see the status list of the document).

## Page: Import reference catalogue (`/catalogue/import`)

### Table 1 on Import reference catalogue

- **Columns:** Table | Rows | Valid | Invalid | Level | Where | Message
- **Search / filter:** none on this page
- **Source evidence:** `app/(app)/catalogue/import/page.tsx:372`

  - **Table:** Which data table (parts, drawings...) the counts are for.
  - **Rows:** Number of rows.
  - **Valid:** Rows that passed validation.
  - **Invalid:** Rows that failed validation.
  - **Level:** Severity (error / warning / info) of an import message, or reorder level.
  - **Where:** Row / column the message refers to.
  - **Message:** The message text.

### Table 2 on Import reference catalogue

- **Columns:** When | Type | Source | Status | Rows | New | Updated | Errors
- **Search / filter:** none on this page
- **Source evidence:** `app/(app)/catalogue/import/page.tsx:442`

  - **When:** Date and time it happened.
  - **Type:** The kind of record (movement type such as RECEIPT, SALE, TRANSFER_IN, ADJUSTMENT_OUT...; or part-number type).
  - **Source:** Where the data came from.
  - **Status:** Current status (see the status list of the document).
  - **Rows:** Number of rows.
  - **New:** Rows that will be / were created.
  - **Updated:** When it was last changed.
  - **Errors:** Rows with errors.

## Page: Import job (`/catalogue/import/[jobId]`)

### Table 1 on Import job

- **Columns:** Table | New | Updated | Unchanged | Skipped | Level | Where | Message | Line | Part | Status | Will | Problems
- **Search / filter:** none on this page
- **Source evidence:** `app/(app)/catalogue/import/[jobId]/page.tsx:188`

  - **Table:** Which data table (parts, drawings...) the counts are for.
  - **New:** Rows that will be / were created.
  - **Updated:** When it was last changed.
  - **Unchanged:** Rows already present and identical.
  - **Skipped:** Rows not imported.
  - **Level:** Severity (error / warning / info) of an import message, or reorder level.
  - **Where:** Row / column the message refers to.
  - **Message:** The message text.
  - **Line:** Line number / line total.
  - **Part:** Reference part.
  - **Status:** Current status (see the status list of the document).
  - **Will:** What the import will do with the row (create, update, skip...).
  - **Problems:** Problems found on the row.

## Page: Reference part details (`/catalogue/parts/[id]`)

### Table 1 on Reference part details

- **Columns:** Make | Model | Chassis | Engine | Production | Market | Catalogue / section | Notes | Source | Description | Status | Reference price (info only) | Recorded | Source record | External ID | Catalogue | Imported | Link
- **Search / filter:** Filter by number, name or callout; status filter: ACTIVE
- **Source evidence:** `app/(app)/catalogue/parts/[id]/page.tsx:322`

  - **Make:** Vehicle make.
  - **Model:** Vehicle model.
  - **Chassis:** Chassis / frame code.
  - **Engine:** Engine code(s).
  - **Production:** Production period of the vehicle / part.
  - **Market:** Market (for example JP, EU).
  - **Catalogue / section:** Catalogue and section the fitment comes from.
  - **Notes:** Notes.
  - **Source:** Where the data came from.
  - **Description:** Description text.
  - **Status:** Current status (see the status list of the document).
  - **Reference price (info only):** Price from the source; NOT the shop's selling price.
  - **Recorded:** When the payment / record was recorded.
  - **Source record:** The source's own record.
  - **External ID:** The source's identifier.
  - **Catalogue:** Source catalogue.
  - **Imported:** When it was imported.
  - **Link:** Link to the source.

### Table 2 on Reference part details

- **Columns:** No. | Part number | Description | Qty | Status
- **Search / filter:** Filter by number, name or callout; status filter: ACTIVE
- **Source evidence:** `ui/catalogue.tsx:240`

  - **No.:** Callout number on the drawing.
  - **Part number:** Part number (OEM or other).
  - **Description:** Description text.
  - **Qty:** Quantity.
  - **Status:** Current status (see the status list of the document).

## Page: Customers (`/customers`)

### Table 1 on Customers

- **Columns:** Code | Name | Contact | Phone | Email | Status
- **Search / filter:** Search name, code, phone or email; status filter: ACTIVE, INACTIVE
- **Source evidence:** `app/(app)/customers/page.tsx:40`

  - **Code:** Customer / supplier code.
  - **Name:** Name.
  - **Contact:** Contact person.
  - **Phone:** Phone.
  - **Email:** Email.
  - **Status:** Current status (see the status list of the document).

## Page: Customer (`/customers/[id]`)

### Table 1 on Customer

- **Columns:** Number | Date | Status | Total | Balance
- **Search / filter:** none on this page
- **Source evidence:** `app/(app)/customers/[id]/page.tsx:78`

  - **Number:** Document number (for example ENQ-, QUO-, ORD-/SO-, INV-, PO-).
  - **Date:** Document date.
  - **Status:** Current status (see the status list of the document).
  - **Total:** Document total.
  - **Balance:** Amount still unpaid on the invoice.

## Page: Enquiries (`/enquiries`)

### Table 1 on Enquiries

- **Columns:** Number | Contact | Email | Items | Submitted | Status
- **Search / filter:** Search number, contact, part number; status filter: CANCELLED, CLOSED, QUOTED, SUBMITTED
- **Source evidence:** `app/(app)/enquiries/page.tsx:39`

  - **Number:** Document number (for example ENQ-, QUO-, ORD-/SO-, INV-, PO-).
  - **Contact:** Contact person.
  - **Email:** Email.
  - **Items:** Number of items.
  - **Submitted:** When the enquiry was submitted.
  - **Status:** Current status (see the status list of the document).

## Page: Enquiry (`/enquiries/[id]`)

### Table 1 on Enquiry

- **Columns:** Part number | Description | Vehicle | Qty
- **Search / filter:** none on this page
- **Source evidence:** `app/(app)/enquiries/[id]/page.tsx:126`

  - **Part number:** Part number (OEM or other).
  - **Description:** Description text.
  - **Vehicle:** The vehicle this applies to.
  - **Qty:** Quantity.

## Page: Enquiry cart (`/enquiries/cart`)

### Table 1 on Enquiry cart

- **Columns:** Part number | Description | Vehicle | Qty
- **Search / filter:** none on this page
- **Source evidence:** `app/(app)/enquiries/cart/page.tsx:76`

  - **Part number:** Part number (OEM or other).
  - **Description:** Description text.
  - **Vehicle:** The vehicle this applies to.
  - **Qty:** Quantity.

## Page: Stock & Locations (`/inventory`)

### Table 1 on Stock & Locations

- **Columns:** Product | SKU | Warehouse | Location | On hand | Reserved | Available
- **Search / filter:** Search product, SKU or location
- **Source evidence:** `app/(app)/inventory/page.tsx:129`

  - **Product:** The shop product (link to its details).
  - **SKU:** The shop's own product code.
  - **Warehouse:** The warehouse.
  - **Location:** The location (rack / shelf / bin) in the warehouse.
  - **On hand:** Units physically in stock at that location (sum of all stock movements).
  - **Reserved:** Units set aside for confirmed sales orders that are not delivered yet.
  - **Available:** Units free to sell or move. Implemented as: available = on_hand - reserved (inventory domain).

### Table 2 on Stock & Locations

- **Columns:** Location code | Rack | Shelf | Bin | Description
- **Search / filter:** Search product, SKU or location
- **Source evidence:** `app/(app)/inventory/page.tsx:213`

  - **Location code:** Code of the location built from rack / shelf / bin.
  - **Rack:** Rack identifier.
  - **Shelf:** Shelf identifier.
  - **Bin:** Bin identifier.
  - **Description:** Description text.

### Table 3 on Stock & Locations

- **Columns:** When | Product | Type | Location | Change | Note
- **Search / filter:** Search product, SKU or location
- **Source evidence:** `app/(app)/inventory/page.tsx:311`

  - **When:** Date and time it happened.
  - **Product:** The shop product (link to its details).
  - **Type:** The kind of record (movement type such as RECEIPT, SALE, TRANSFER_IN, ADJUSTMENT_OUT...; or part-number type).
  - **Location:** The location (rack / shelf / bin) in the warehouse.
  - **Change:** Quantity added (+) or removed (-) by the movement.
  - **Note:** Note recorded with it.

## Page: Invoices & Payments (`/invoices`)

### Table 1 on Invoices & Payments

- **Columns:** Number | Issued | Due | Status | Total | Balance
- **Search / filter:** Search invoice number; status filter: ISSUED, PAID, PARTIALLY_PAID, VOID
- **Source evidence:** `app/(app)/invoices/page.tsx:43`

  - **Number:** Document number (for example ENQ-, QUO-, ORD-/SO-, INV-, PO-).
  - **Issued:** When it was issued.
  - **Due:** Due date of the invoice.
  - **Status:** Current status (see the status list of the document).
  - **Total:** Document total.
  - **Balance:** Amount still unpaid on the invoice.

## Page: Invoice (`/invoices/[id]`)

### Table 1 on Invoice

- **Columns:** Date | Method | Reference | Amount
- **Search / filter:** none on this page
- **Source evidence:** `app/(app)/invoices/[id]/page.tsx:155`

  - **Date:** Document date.
  - **Method:** Payment method (Cash, Bank transfer, Card, Other).
  - **Reference:** Payment / document reference.
  - **Amount:** Payment amount.

### Table 2 on Invoice

- **Columns:** Item | Qty | Unit price | Disc. | Total
- **Search / filter:** none on this page
- **Source evidence:** `ui/doc.tsx:31`

  - **Item:** The product or free-text line.
  - **Qty:** Quantity.
  - **Unit price:** Price per unit.
  - **Disc.:** Discount on the line.
  - **Total:** Document total.

## Page: Orders (`/orders`)

### Table 1 on Orders

- **Columns:** Number | Created | Status | Total
- **Search / filter:** Search order number; status filter: CANCELLED, CONFIRMED, FULFILLED, INVOICED, PARTIALLY_FULFILLED
- **Source evidence:** `app/(app)/orders/page.tsx:35`

  - **Number:** Document number (for example ENQ-, QUO-, ORD-/SO-, INV-, PO-).
  - **Created:** When it was created.
  - **Status:** Current status (see the status list of the document).
  - **Total:** Document total.

## Page: Sales order (`/orders/[id]`)

### Table 1 on Sales order

- **Columns:** Delivered | Returned | Invoiced
- **Search / filter:** none on this page
- **Source evidence:** `app/(app)/orders/[id]/page.tsx:202`

  - **Delivered:** Quantity delivered so far.
  - **Returned:** Quantity returned.
  - **Invoiced:** Quantity invoiced so far.

### Table 2 on Sales order

- **Columns:** Item | Qty | Unit price | Disc. | Total
- **Search / filter:** none on this page
- **Source evidence:** `ui/doc.tsx:31`

  - **Item:** The product or free-text line.
  - **Qty:** Quantity.
  - **Unit price:** Price per unit.
  - **Disc.:** Discount on the line.
  - **Total:** Document total.

## Page: My Products (`/products`)

### Table 1 on My Products

- **Columns:** Product | Category | Available | On hand | Price | Cost | Status
- **Search / filter:** Search name, SKU, brand or part number; status filter: ACTIVE, INACTIVE
- **Source evidence:** `app/(app)/products/page.tsx:81`

  - **Product:** The shop product (link to its details).
  - **Category:** Product category.
  - **Available:** Units free to sell or move. Implemented as: available = on_hand - reserved (inventory domain).
  - **On hand:** Units physically in stock at that location (sum of all stock movements).
  - **Price:** Selling price.
  - **Cost:** Cost price (shown only with the cost permission).
  - **Status:** Current status (see the status list of the document).

## Page: Product details (`/products/[id]`)

### Table 1 on Product details

- **Columns:** Make | Model | Chassis | Engine | Production | Market | Section
- **Search / filter:** Search by part number or description; status filter: ACTIVE, LOW
- **Source evidence:** `app/(app)/products/[id]/page.tsx:497`

  - **Make:** Vehicle make.
  - **Model:** Vehicle model.
  - **Chassis:** Chassis / frame code.
  - **Engine:** Engine code(s).
  - **Production:** Production period of the vehicle / part.
  - **Market:** Market (for example JP, EU).
  - **Section:** Catalogue section.

### Table 2 on Product details

- **Columns:** Warehouse | Location | On hand | Reserved | Available | When | Type | Change | Note
- **Search / filter:** Search by part number or description; status filter: ACTIVE, LOW
- **Source evidence:** `app/(app)/products/[id]/page.tsx:583`

  - **Warehouse:** The warehouse.
  - **Location:** The location (rack / shelf / bin) in the warehouse.
  - **On hand:** Units physically in stock at that location (sum of all stock movements).
  - **Reserved:** Units set aside for confirmed sales orders that are not delivered yet.
  - **Available:** Units free to sell or move. Implemented as: available = on_hand - reserved (inventory domain).
  - **When:** Date and time it happened.
  - **Type:** The kind of record (movement type such as RECEIPT, SALE, TRANSFER_IN, ADJUSTMENT_OUT...; or part-number type).
  - **Change:** Quantity added (+) or removed (-) by the movement.
  - **Note:** Note recorded with it.

### Table 3 on Product details

- **Columns:** Supplier | Their part number | Cost | Preferred
- **Search / filter:** Search by part number or description; status filter: ACTIVE, LOW
- **Source evidence:** `app/(app)/products/[id]/page.tsx:673`

  - **Supplier:** Supplier.
  - **Their part number:** The supplier's code for the product.
  - **Cost:** Cost price (shown only with the cost permission).
  - **Preferred:** The usual supplier for the product.

### Table 4 on Product details

- **Columns:** Number | Type | Brand | Source | Notes | Reference part | Linked
- **Search / filter:** Search by part number or description; status filter: ACTIVE, LOW
- **Source evidence:** `app/(app)/products/[id]/page.tsx:764`

  - **Number:** Document number (for example ENQ-, QUO-, ORD-/SO-, INV-, PO-).
  - **Type:** The kind of record (movement type such as RECEIPT, SALE, TRANSFER_IN, ADJUSTMENT_OUT...; or part-number type).
  - **Brand:** Brand.
  - **Source:** Where the data came from.
  - **Notes:** Notes.
  - **Reference part:** Linked reference catalogue part.
  - **Linked:** Whether it is linked.

### Table 5 on Product details

- **Columns:** Invoice | Date | Customer | Qty | Unit price | Total
- **Search / filter:** Search by part number or description; status filter: ACTIVE, LOW
- **Source evidence:** `app/(app)/products/[id]/page.tsx:958`

  - **Invoice:** Invoice number.
  - **Date:** Document date.
  - **Customer:** Customer of the document.
  - **Qty:** Quantity.
  - **Unit price:** Price per unit.
  - **Total:** Document total.

### Table 6 on Product details

- **Columns:** When | Who | What | Type | Change | Note
- **Search / filter:** Search by part number or description; status filter: ACTIVE, LOW
- **Source evidence:** `app/(app)/products/[id]/page.tsx:1020`

  - **When:** Date and time it happened.
  - **Who:** The user who did it.
  - **What:** The action.
  - **Type:** The kind of record (movement type such as RECEIPT, SALE, TRANSFER_IN, ADJUSTMENT_OUT...; or part-number type).
  - **Change:** Quantity added (+) or removed (-) by the movement.
  - **Note:** Note recorded with it.

## Page: Purchase Orders (`/purchasing`)

### Table 1 on Purchase Orders

- **Columns:** Number | Created | Expected | Status | Total
- **Search / filter:** Search PO number; status filter: CANCELLED, CLOSED, CONFIRMED, DRAFT, PARTIALLY_RECEIVED, RECEIVED
- **Source evidence:** `app/(app)/purchasing/page.tsx:46`

  - **Number:** Document number (for example ENQ-, QUO-, ORD-/SO-, INV-, PO-).
  - **Created:** When it was created.
  - **Expected:** Expected delivery date.
  - **Status:** Current status (see the status list of the document).
  - **Total:** Document total.

## Page: Purchase order (`/purchasing/[id]`)

### Table 1 on Purchase order

- **Columns:** Product | Ordered | Received | Unit cost | Total
- **Search / filter:** none on this page
- **Source evidence:** `app/(app)/purchasing/[id]/page.tsx:173`

  - **Product:** The shop product (link to its details).
  - **Ordered:** Quantity ordered.
  - **Received:** Received date / quantity received.
  - **Unit cost:** Cost per unit.
  - **Total:** Document total.

### Table 2 on Purchase order

- **Columns:** Item | Qty | Unit price | Disc. | Total
- **Search / filter:** none on this page
- **Source evidence:** `ui/doc.tsx:31`

  - **Item:** The product or free-text line.
  - **Qty:** Quantity.
  - **Unit price:** Price per unit.
  - **Disc.:** Discount on the line.
  - **Total:** Document total.

## Page: Quotations (`/quotations`)

### Table 1 on Quotations

- **Columns:** Number | Created | Valid until | Status | Total
- **Search / filter:** Search quotation number; status filter: ACCEPTED, CANCELLED, DRAFT, EXPIRED, ISSUED, REJECTED
- **Source evidence:** `app/(app)/quotations/page.tsx:46`

  - **Number:** Document number (for example ENQ-, QUO-, ORD-/SO-, INV-, PO-).
  - **Created:** When it was created.
  - **Valid until:** Last day the quotation is valid.
  - **Status:** Current status (see the status list of the document).
  - **Total:** Document total.

## Page: Quotation (`/quotations/[id]`)

### Table 1 on Quotation

- **Columns:** Item | Qty | Unit price | Disc. | Total
- **Search / filter:** Description (item not in My Products)
- **Source evidence:** `ui/doc.tsx:31`

  - **Item:** The product or free-text line.
  - **Qty:** Quantity.
  - **Unit price:** Price per unit.
  - **Disc.:** Discount on the line.
  - **Total:** Document total.

## Page: Suppliers (`/suppliers`)

### Table 1 on Suppliers

- **Columns:** Code | Name | Contact | Phone | Email | Status
- **Search / filter:** Search name, code, phone or email; status filter: ACTIVE, INACTIVE
- **Source evidence:** `app/(app)/suppliers/page.tsx:40`

  - **Code:** Customer / supplier code.
  - **Name:** Name.
  - **Contact:** Contact person.
  - **Phone:** Phone.
  - **Email:** Email.
  - **Status:** Current status (see the status list of the document).

## Page: Supplier (`/suppliers/[id]`)

### Table 1 on Supplier

- **Columns:** Number | Date | Status | Total
- **Search / filter:** none on this page
- **Source evidence:** `app/(app)/suppliers/[id]/page.tsx:101`

  - **Number:** Document number (for example ENQ-, QUO-, ORD-/SO-, INV-, PO-).
  - **Date:** Document date.
  - **Status:** Current status (see the status list of the document).
  - **Total:** Document total.
