# Spare Parts Shop -- button and action reference (Level 1)

Every button / action found in the code, page by page, with what it does. Small controls (Save, Cancel, Close, paging, sorting arrows) are included.

## Page: Dashboard (Business overview) (`/`)

### Button: Load sample data (development only)

- **Application:** Spare Parts Shop
- **Location:** Dashboard (Business overview)
- **Purpose:** Load demonstration data (development installations only).
- **What happens:** Creates sample records (settings.manage). Not for a real shop.
- **Data affected:** Sample records
- **Confirmation:** No
- **Can it be undone:** No
- **Next step:** --
- **Server call:** `POST /dev/sample-data` -- permission `settings.manage`
- **Source evidence:** `app/(app)/page.tsx:223`

## Page: Audit log (Spare Parts) (`/admin/audit`)

### Button: Newer

- **Application:** Spare Parts Shop
- **Location:** Audit log (Spare Parts)
- **Purpose:** Show newer audit entries.
- **What happens:** Pages back towards the most recent.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** Older
- **Next step:** --
- **Source evidence:** `app/(app)/admin/audit/page.tsx:74`

### Button: Older

- **Application:** Spare Parts Shop
- **Location:** Audit log (Spare Parts)
- **Purpose:** Show older audit entries.
- **What happens:** Pages to earlier entries.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** Newer
- **Next step:** --
- **Source evidence:** `app/(app)/admin/audit/page.tsx:80`

## Page: Shop settings (`/admin/settings`)

### Button: Save settings

- **Application:** Spare Parts Shop
- **Location:** Shop settings
- **Purpose:** Save the shop settings.
- **What happens:** Settings are saved (settings.manage) and used on new documents.
- **Data affected:** Shop settings
- **Confirmation:** No
- **Can it be undone:** Change again
- **Next step:** --
- **Source evidence:** `app/(app)/admin/settings/page.tsx:146`

## Page: Users (`/admin/users`)

### Button: Add user

- **Application:** Spare Parts Shop
- **Location:** Users
- **Purpose:** Standalone mode: add a user. Inside IntraForge: refused -- people are managed in IntraForge.
- **What happens:** Inside IntraForge the server answers: "People, passwords and roles are managed in IntraForge (Organization > Members and Roles)."
- **Data affected:** None inside IntraForge
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** Use IntraForge > Organization > Members
- **Opens a dialog** first
- **Source evidence:** `app/(app)/admin/users/page.tsx:43`

### Button: Edit

- **Application:** Spare Parts Shop
- **Location:** Users
- **Purpose:** Open the edit form for this record.
- **What happens:** Opens a dialog with the current values.
- **Data affected:** None until saved
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** Save
- **Opens a dialog** first
- **Source evidence:** `app/(app)/admin/users/page.tsx:67`

### Button: Reset password

- **Application:** Spare Parts Shop
- **Location:** Users
- **Purpose:** Standalone mode only (see Add user).
- **What happens:** Inside IntraForge: refused, managed in IntraForge.
- **Data affected:** None inside IntraForge
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Opens a dialog** first
- **Source evidence:** `app/(app)/admin/users/page.tsx:70`

### Button: Disable

- **Application:** Spare Parts Shop
- **Location:** Users
- **Purpose:** Standalone mode only: disable a user.
- **What happens:** Inside IntraForge: refused, managed in IntraForge.
- **Data affected:** None inside IntraForge
- **Confirmation:** No
- **Can it be undone:** Enable
- **Next step:** --
- **Server call:** `PATCH /users/:id` -- permission `users.manage`
- **Shown as a danger (red) button**
- **Source evidence:** `app/(app)/admin/users/page.tsx:76`

### Button: Enable

- **Application:** Spare Parts Shop
- **Location:** Users
- **Purpose:** Standalone mode only: enable a user.
- **What happens:** Inside IntraForge: refused, managed in IntraForge.
- **Data affected:** None inside IntraForge
- **Confirmation:** No
- **Can it be undone:** Disable
- **Next step:** --
- **Server call:** `PATCH /users/:id` -- permission `users.manage`
- **Source evidence:** `app/(app)/admin/users/page.tsx:89`

## Page: Reference Catalogue (`/catalogue`)

### Button: Search

- **Application:** Spare Parts Shop
- **Location:** Reference Catalogue
- **Purpose:** Run the search with what you typed.
- **What happens:** Shows matching results.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** Open a result
- **Source evidence:** `app/(app)/catalogue/page.tsx:152`

### Button: Hide filters / Filters

- **Application:** Spare Parts Shop
- **Location:** Reference Catalogue
- **Purpose:** Show the catalogue filters.
- **What happens:** Opens the filter panel.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** Hide filters
- **Next step:** --
- **Source evidence:** `app/(app)/catalogue/page.tsx:153`

### Button: Add to enquiry

- **Application:** Spare Parts Shop
- **Location:** Reference Catalogue
- **Purpose:** Put this part into your enquiry cart.
- **What happens:** Adds the part (with the vehicle, if known) to your current draft enquiry (enquiries.write); a message confirms it.
- **Data affected:** Your draft enquiry
- **Confirmation:** No
- **Can it be undone:** Remove it in the cart
- **Next step:** Open the enquiry cart and submit
- **Source evidence:** `app/(app)/catalogue/page.tsx:304`

## Page: Drawing (`/catalogue/drawings/[id]`)

### Button: Add to enquiry

- **Application:** Spare Parts Shop
- **Location:** Drawing
- **Purpose:** Put this part into your enquiry cart.
- **What happens:** Adds the part (with the vehicle, if known) to your current draft enquiry (enquiries.write); a message confirms it.
- **Data affected:** Your draft enquiry
- **Confirmation:** No
- **Can it be undone:** Remove it in the cart
- **Next step:** Open the enquiry cart and submit
- **Source evidence:** `ui/catalogue.tsx:306`

## Page: Import reference catalogue (`/catalogue/import`)

### Button: Choose a different file / Choose CSV file

- **Application:** Spare Parts Shop
- **Location:** Import reference catalogue
- **Purpose:** Pick the CSV file to import.
- **What happens:** Reads the file and suggests a column match.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** Choose a different file
- **Next step:** Validate and preview
- **Source evidence:** `app/(app)/catalogue/import/page.tsx:150`

### Button: Checking… / Validate and preview

- **Application:** Spare Parts Shop
- **Location:** Import reference catalogue
- **Purpose:** Check the mapped CSV before anything is stored.
- **What happens:** Every row is checked: new, already present, changed, duplicated or invalid; nothing is imported yet.
- **Data affected:** Staged import job
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** Start the import on the job page
- **Source evidence:** `app/(app)/catalogue/import/page.tsx:273`

### Button: Choose a different package / Choose package file

- **Application:** Spare Parts Shop
- **Location:** Import reference catalogue
- **Purpose:** Pick an offline catalogue package (zip).
- **What happens:** Reads the package and shows what it contains.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** Choose a different package
- **Next step:** Import package
- **Source evidence:** `app/(app)/catalogue/import/page.tsx:348`

### Button: Importing… / Import package

- **Application:** Spare Parts Shop
- **Location:** Import reference catalogue
- **Purpose:** Import the offline catalogue package.
- **What happens:** Imports parts, drawings (images only if licensed) (catalogue.import).
- **Data affected:** Reference catalogue
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** Search the catalogue
- **Source evidence:** `app/(app)/catalogue/import/page.tsx:415`

## Page: Import job (`/catalogue/import/[jobId]`)

### Button: Resume import

- **Application:** Spare Parts Shop
- **Location:** Import job
- **Purpose:** Continue an import that stopped.
- **What happens:** Imports the rows still to do (safe to repeat).
- **Data affected:** Reference catalogue
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Server call:** `POST /catalogue/import/jobs/:id/commit` -- permission `catalogue.import`
- **Source evidence:** `app/(app)/catalogue/import/[jobId]/page.tsx:114`

### Button: Include / Exclude

- **Application:** Spare Parts Shop
- **Location:** Import job
- **Purpose:** Leave this row out of the import.
- **What happens:** The row is marked EXCLUDED.
- **Data affected:** Import job row
- **Confirmation:** No
- **Can it be undone:** Include
- **Next step:** --
- **Server call:** `PATCH /catalogue/import/jobs/:id/rows/:id` -- permission `catalogue.import`
- **Source evidence:** `app/(app)/catalogue/import/[jobId]/page.tsx:264`

## Page: Reference part details (`/catalogue/parts/[id]`)

### Button: Add to enquiry

- **Application:** Spare Parts Shop
- **Location:** Reference part details
- **Purpose:** Put this part into your enquiry cart.
- **What happens:** Adds the part (with the vehicle, if known) to your current draft enquiry (enquiries.write); a message confirms it.
- **Data affected:** Your draft enquiry
- **Confirmation:** No
- **Can it be undone:** Remove it in the cart
- **Next step:** Open the enquiry cart and submit
- **Source evidence:** `app/(app)/catalogue/parts/[id]/page.tsx:200`

### Button: IMPORT TO MY PRODUCTS

- **Application:** Spare Parts Shop
- **Location:** Reference part details
- **Purpose:** Create a shop product from this reference part.
- **What happens:** Opens the import dialog (SKU, name, prices, reorder level, supplier, location, stock now); saving creates the product linked to the reference part (products.write).
- **Data affected:** New product linked to the reference part; optional opening stock
- **Confirmation:** No
- **Can it be undone:** Edit the product / set Inactive
- **Next step:** Complete the product (photos, supplier), receive stock
- **Opens a dialog** first
- **Source evidence:** `app/(app)/catalogue/parts/[id]/page.tsx:254`

### Button: IMPORT TO MY PRODUCTS

- **Application:** Spare Parts Shop
- **Location:** Reference part details -> dialog "Import … to My Products"
- **Purpose:** Create a shop product from this reference part.
- **What happens:** Opens the import dialog (SKU, name, prices, reorder level, supplier, location, stock now); saving creates the product linked to the reference part (products.write).
- **Data affected:** New product linked to the reference part; optional opening stock
- **Confirmation:** No
- **Can it be undone:** Edit the product / set Inactive
- **Next step:** Complete the product (photos, supplier), receive stock
- **Source evidence:** `app/(app)/catalogue/parts/[id]/page.tsx:432`

### Button: Receive

- **Application:** Spare Parts Shop
- **Location:** Reference part details -> dialog "Receive stock — …"
- **Purpose:** Receive stock without a purchase order.
- **What happens:** Opens Receive stock: location, quantity received, note; saving adds a RECEIPT movement (inventory.write).
- **Data affected:** Stock movement
- **Confirmation:** No
- **Can it be undone:** Adjust with a reason
- **Next step:** --
- **Source evidence:** `ui/stock.tsx:77`

### Button: Save adjustment

- **Application:** Spare Parts Shop
- **Location:** Reference part details -> dialog "Adjust stock — …"
- **Purpose:** Save the stock correction.
- **What happens:** Adds an ADJUSTMENT_IN / ADJUSTMENT_OUT movement; refused if it would drop below what is reserved.
- **Data affected:** Stock movement
- **Confirmation:** No
- **Can it be undone:** Another adjustment
- **Next step:** --
- **Source evidence:** `ui/stock.tsx:110`

### Button: Transfer

- **Application:** Spare Parts Shop
- **Location:** Reference part details -> dialog "Transfer stock — …"
- **Purpose:** Move stock between two locations.
- **What happens:** Opens Transfer stock: from, to (must differ), quantity (at most what is available there), note; saving adds TRANSFER_OUT and TRANSFER_IN.
- **Data affected:** Two stock movements
- **Confirmation:** No
- **Can it be undone:** Transfer back
- **Next step:** --
- **Source evidence:** `ui/stock.tsx:134`

## Page: Customers (`/customers`)

### Button: New customer

- **Application:** Spare Parts Shop
- **Location:** Customers
- **Purpose:** Create a customer.
- **What happens:** Opens the New customer form (customers.write).
- **Data affected:** New customer record
- **Confirmation:** No
- **Can it be undone:** Edit / set Inactive
- **Next step:** Create an enquiry or quotation for them
- **Opens a dialog** first
- **Source evidence:** `app/(app)/customers/page.tsx:33`

## Page: Customer (`/customers/[id]`)

### Button: Edit

- **Application:** Spare Parts Shop
- **Location:** Customer
- **Purpose:** Open the edit form for this record.
- **What happens:** Opens a dialog with the current values.
- **Data affected:** None until saved
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** Save
- **Opens a dialog** first
- **Source evidence:** `app/(app)/customers/[id]/page.tsx:114`

## Page: Enquiry (`/enquiries/[id]`)

### Button: Create quotation

- **Application:** Spare Parts Shop
- **Location:** Enquiry
- **Purpose:** Turn the enquiry into a quotation.
- **What happens:** Creates a DRAFT quotation; lines are priced automatically from My Products where the part number matches a product you stock; the enquiry becomes QUOTED.
- **Data affected:** New quotation; enquiry status
- **Confirmation:** No
- **Can it be undone:** Cancel the quotation
- **Next step:** Check prices, Issue to customer
- **Opens a dialog** first
- **Source evidence:** `app/(app)/enquiries/[id]/page.tsx:80`

### Button: Create quotation

- **Application:** Spare Parts Shop
- **Location:** Enquiry -> dialog "Create quotation"
- **Purpose:** Turn the enquiry into a quotation.
- **What happens:** Creates a DRAFT quotation; lines are priced automatically from My Products where the part number matches a product you stock; the enquiry becomes QUOTED.
- **Data affected:** New quotation; enquiry status
- **Confirmation:** No
- **Can it be undone:** Cancel the quotation
- **Next step:** Check prices, Issue to customer
- **Source evidence:** `app/(app)/enquiries/[id]/page.tsx:165`

## Page: Enquiry cart (`/enquiries/cart`)

### Button: Remove

- **Application:** Spare Parts Shop
- **Location:** Enquiry cart
- **Purpose:** Remove the part from the draft enquiry.
- **What happens:** The item is removed from your cart.
- **Data affected:** Draft enquiry
- **Confirmation:** No
- **Can it be undone:** Add to enquiry again
- **Next step:** --
- **Server call:** `DELETE /enquiries/:id/items/:id` -- permission `enquiries.write`
- **Source evidence:** `app/(app)/enquiries/cart/page.tsx:92`

### Button: Submit enquiry

- **Application:** Spare Parts Shop
- **Location:** Enquiry cart
- **Purpose:** Send the enquiry with its customer / contact.
- **What happens:** The draft enquiry becomes SUBMITTED; needs at least one part and a customer or contact name.
- **Data affected:** Enquiry
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** Create quotation
- **Source evidence:** `app/(app)/enquiries/cart/page.tsx:163`

## Page: Stock & Locations (`/inventory`)

### Button: New warehouse

- **Application:** Spare Parts Shop
- **Location:** Stock & Locations
- **Purpose:** Create a warehouse.
- **What happens:** Opens the New warehouse form (name, address) (warehouses.write).
- **Data affected:** Warehouse
- **Confirmation:** No
- **Can it be undone:** Edit
- **Next step:** Add rack / shelf / bin
- **Opens a dialog** first
- **Source evidence:** `app/(app)/inventory/page.tsx:169`

### Button: Add rack / shelf / bin

- **Application:** Spare Parts Shop
- **Location:** Stock & Locations
- **Purpose:** Create a storage location in a warehouse.
- **What happens:** Opens the form: rack, shelf, bin, description; the location code must be unique in the warehouse.
- **Data affected:** Location
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** Receive into it
- **Opens a dialog** first
- **Source evidence:** `app/(app)/inventory/page.tsx:195`

### Button: Edit

- **Application:** Spare Parts Shop
- **Location:** Stock & Locations
- **Purpose:** Open the edit form for this record.
- **What happens:** Opens a dialog with the current values.
- **Data affected:** None until saved
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** Save
- **Opens a dialog** first
- **Source evidence:** `app/(app)/inventory/page.tsx:200`

### Button: Receive

- **Application:** Spare Parts Shop
- **Location:** Stock & Locations -> dialog "Receive stock — …"
- **Purpose:** Receive stock without a purchase order.
- **What happens:** Opens Receive stock: location, quantity received, note; saving adds a RECEIPT movement (inventory.write).
- **Data affected:** Stock movement
- **Confirmation:** No
- **Can it be undone:** Adjust with a reason
- **Next step:** --
- **Source evidence:** `ui/stock.tsx:77`

### Button: Save adjustment

- **Application:** Spare Parts Shop
- **Location:** Stock & Locations -> dialog "Adjust stock — …"
- **Purpose:** Save the stock correction.
- **What happens:** Adds an ADJUSTMENT_IN / ADJUSTMENT_OUT movement; refused if it would drop below what is reserved.
- **Data affected:** Stock movement
- **Confirmation:** No
- **Can it be undone:** Another adjustment
- **Next step:** --
- **Source evidence:** `ui/stock.tsx:110`

### Button: Transfer

- **Application:** Spare Parts Shop
- **Location:** Stock & Locations -> dialog "Transfer stock — …"
- **Purpose:** Move stock between two locations.
- **What happens:** Opens Transfer stock: from, to (must differ), quantity (at most what is available there), note; saving adds TRANSFER_OUT and TRANSFER_IN.
- **Data affected:** Two stock movements
- **Confirmation:** No
- **Can it be undone:** Transfer back
- **Next step:** --
- **Source evidence:** `ui/stock.tsx:134`

## Page: Invoice (`/invoices/[id]`)

### Button: Record payment

- **Application:** Spare Parts Shop
- **Location:** Invoice
- **Purpose:** Record money received for this invoice.
- **What happens:** Opens the payment form (Amount -- the label shows the current balance --, Method Cash / Bank transfer / Card / Other, Reference, Notes); saving adds the payment: invoice becomes PARTIALLY_PAID or PAID (payments.record).
- **Data affected:** Payment, invoice status
- **Confirmation:** No
- **Can it be undone:** Payments are permanent; contact an administrator
- **Next step:** --
- **Opens a dialog** first
- **Source evidence:** `app/(app)/invoices/[id]/page.tsx:93`

### Button: Void

- **Application:** Spare Parts Shop
- **Location:** Invoice
- **Purpose:** Start voiding the invoice.
- **What happens:** Opens the Void invoice dialog.
- **Data affected:** --
- **Confirmation:** Yes (dialog)
- **Can it be undone:** --
- **Next step:** Void invoice
- **Opens a dialog** first
- **Shown as a danger (red) button**
- **Source evidence:** `app/(app)/invoices/[id]/page.tsx:100`

### Button: Record payment

- **Application:** Spare Parts Shop
- **Location:** Invoice -> dialog "Record payment"
- **Purpose:** Record money received for this invoice.
- **What happens:** Opens the payment form (Amount -- the label shows the current balance --, Method Cash / Bank transfer / Card / Other, Reference, Notes); saving adds the payment: invoice becomes PARTIALLY_PAID or PAID (payments.record).
- **Data affected:** Payment, invoice status
- **Confirmation:** No
- **Can it be undone:** Payments are permanent; contact an administrator
- **Next step:** --
- **Source evidence:** `app/(app)/invoices/[id]/page.tsx:175`

### Button: Void invoice

- **Application:** Spare Parts Shop
- **Location:** Invoice -> dialog "Void invoice"
- **Purpose:** Void (cancel) the invoice.
- **What happens:** Asks for a Reason; status -> VOID; a void invoice cannot take payments.
- **Data affected:** Invoice status
- **Confirmation:** Yes
- **Can it be undone:** No
- **Next step:** --
- **Source evidence:** `app/(app)/invoices/[id]/page.tsx:210`

## Page: Sales order (`/orders/[id]`)

### Button: Record delivery

- **Application:** Spare Parts Shop
- **Location:** Sales order
- **Purpose:** Record goods leaving the shop for this order.
- **What happens:** Opens a dialog with the quantity delivered now per line (pre-filled with what remains).
- **Data affected:** --
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** Save delivery
- **Source evidence:** `app/(app)/orders/[id]/page.tsx:107`

### Button: Invoice delivered items

- **Application:** Spare Parts Shop
- **Location:** Sales order
- **Purpose:** Invoice what was delivered.
- **What happens:** Creates an ISSUED invoice for the delivered, not yet invoiced quantities; order becomes INVOICED when all is invoiced.
- **Data affected:** New invoice, order status
- **Confirmation:** No
- **Can it be undone:** Void invoice
- **Next step:** Record payment
- **Source evidence:** `app/(app)/orders/[id]/page.tsx:124`

### Button: Record return

- **Application:** Spare Parts Shop
- **Location:** Sales order
- **Purpose:** Record goods the customer brought back.
- **What happens:** Opens / saves the return: quantity returned and the location to put it back (RETURN_IN movement).
- **Data affected:** Stock movement
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Opens a dialog** first
- **Source evidence:** `app/(app)/orders/[id]/page.tsx:133`

### Button: Reserve available stock

- **Application:** Spare Parts Shop
- **Location:** Sales order
- **Purpose:** Try again to reserve stock for lines that are short.
- **What happens:** Reserves what is now available for the order.
- **Data affected:** Reservations
- **Confirmation:** No
- **Can it be undone:** Cancel order releases them
- **Next step:** Record delivery
- **Server call:** `POST /orders/:id/reserve` -- permission `orders.write`
- **Source evidence:** `app/(app)/orders/[id]/page.tsx:136`

### Button: Cancel order

- **Application:** Spare Parts Shop
- **Location:** Sales order
- **Purpose:** Cancel the order.
- **What happens:** Status -> CANCELLED; reservations are released. A cancelled order cannot be invoiced.
- **Data affected:** Order status, reservations
- **Confirmation:** No
- **Can it be undone:** No
- **Next step:** --
- **Server call:** `POST /orders/:id/cancel` -- permission `orders.write`
- **Shown as a danger (red) button**
- **Source evidence:** `app/(app)/orders/[id]/page.tsx:150`

### Button: Save delivery

- **Application:** Spare Parts Shop
- **Location:** Sales order -> dialog "Record delivery"
- **Purpose:** Save the delivery.
- **What happens:** Stock on hand and reserved go down (SALE movement); order becomes PARTIALLY_FULFILLED or FULFILLED.
- **Data affected:** Stock movements, order status
- **Confirmation:** No
- **Can it be undone:** Record return
- **Next step:** Invoice delivered items
- **Source evidence:** `app/(app)/orders/[id]/page.tsx:250`

### Button: Record return

- **Application:** Spare Parts Shop
- **Location:** Sales order -> dialog "Record return"
- **Purpose:** Record goods the customer brought back.
- **What happens:** Opens / saves the return: quantity returned and the location to put it back (RETURN_IN movement).
- **Data affected:** Stock movement
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Source evidence:** `app/(app)/orders/[id]/page.tsx:263`

## Page: My Products (`/products`)

### Button: New product

- **Application:** Spare Parts Shop
- **Location:** My Products
- **Purpose:** Create a shop product directly (without a catalogue part).
- **What happens:** Opens the New product form (products.write); optional opening stock is recorded as an opening-balance movement.
- **Data affected:** Product (+ opening stock movement)
- **Confirmation:** No
- **Can it be undone:** Edit / set Inactive
- **Next step:** Receive stock, add photos
- **Opens a dialog** first
- **Source evidence:** `app/(app)/products/page.tsx:71`

### Button: Receive

- **Application:** Spare Parts Shop
- **Location:** My Products -> dialog "Receive stock — …"
- **Purpose:** Receive stock without a purchase order.
- **What happens:** Opens Receive stock: location, quantity received, note; saving adds a RECEIPT movement (inventory.write).
- **Data affected:** Stock movement
- **Confirmation:** No
- **Can it be undone:** Adjust with a reason
- **Next step:** --
- **Source evidence:** `ui/stock.tsx:77`

### Button: Save adjustment

- **Application:** Spare Parts Shop
- **Location:** My Products -> dialog "Adjust stock — …"
- **Purpose:** Save the stock correction.
- **What happens:** Adds an ADJUSTMENT_IN / ADJUSTMENT_OUT movement; refused if it would drop below what is reserved.
- **Data affected:** Stock movement
- **Confirmation:** No
- **Can it be undone:** Another adjustment
- **Next step:** --
- **Source evidence:** `ui/stock.tsx:110`

### Button: Transfer

- **Application:** Spare Parts Shop
- **Location:** My Products -> dialog "Transfer stock — …"
- **Purpose:** Move stock between two locations.
- **What happens:** Opens Transfer stock: from, to (must differ), quantity (at most what is available there), note; saving adds TRANSFER_OUT and TRANSFER_IN.
- **Data affected:** Two stock movements
- **Confirmation:** No
- **Can it be undone:** Transfer back
- **Next step:** --
- **Source evidence:** `ui/stock.tsx:134`

## Page: Product details (`/products/[id]`)

### Button: Edit product

- **Application:** Spare Parts Shop
- **Location:** Product details
- **Purpose:** Change the product's details.
- **What happens:** Opens the product form (products.write; cost only with products.cost.read).
- **Data affected:** Product
- **Confirmation:** No
- **Can it be undone:** Edit again
- **Next step:** Save
- **Opens a dialog** first
- **Source evidence:** `app/(app)/products/[id]/page.tsx:153`

### Button: Uploading… / Add photos

- **Application:** Spare Parts Shop
- **Location:** Product details
- **Purpose:** Upload product photos.
- **What happens:** PNG, JPEG, GIF or WebP; stored in IntraForge file storage (products.write).
- **Data affected:** Product photos
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** Make primary
- **Source evidence:** `app/(app)/products/[id]/page.tsx:275`

### Button: Make primary

- **Application:** Spare Parts Shop
- **Location:** Product details
- **Purpose:** Make this photo the main product photo.
- **What happens:** The photo becomes the first / primary one.
- **Data affected:** Photo order
- **Confirmation:** No
- **Can it be undone:** Make another primary
- **Next step:** --
- **Server call:** `PUT /products/:id/images/:id/primary` -- permission `products.write`
- **Source evidence:** `app/(app)/products/[id]/page.tsx:336`

### Button: ← Earlier

- **Application:** Spare Parts Shop
- **Location:** Product details
- **Purpose:** Move the photo earlier in the order.
- **What happens:** Reorders the photos.
- **Data affected:** Photo order
- **Confirmation:** No
- **Can it be undone:** Later →
- **Next step:** --
- **Source evidence:** `app/(app)/products/[id]/page.tsx:348`

### Button: Later →

- **Application:** Spare Parts Shop
- **Location:** Product details
- **Purpose:** Move the photo later in the order.
- **What happens:** Reorders the photos.
- **Data affected:** Photo order
- **Confirmation:** No
- **Can it be undone:** ← Earlier
- **Next step:** --
- **Source evidence:** `app/(app)/products/[id]/page.tsx:354`

### Button: Barcode label

- **Application:** Spare Parts Shop
- **Location:** Product details
- **Purpose:** Choose a barcode (Code 128) label.
- **What happens:** Shows the barcode label for the product.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** Open to print
- **Source evidence:** `app/(app)/products/[id]/page.tsx:400`

### Button: QR label

- **Application:** Spare Parts Shop
- **Location:** Product details
- **Purpose:** Choose a QR label.
- **What happens:** Shows the QR label for the product.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** Open to print
- **Opens a dialog** first
- **Source evidence:** `app/(app)/products/[id]/page.tsx:401`

### Button: Open to print

- **Application:** Spare Parts Shop
- **Location:** Product details
- **Purpose:** Open the label in a new tab to print it.
- **What happens:** Opens the label image; scanning it in Scan / Lookup opens this product.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** Print
- **Source evidence:** `app/(app)/products/[id]/page.tsx:420`

### Button: Receive

- **Application:** Spare Parts Shop
- **Location:** Product details
- **Purpose:** Receive stock without a purchase order.
- **What happens:** Opens Receive stock: location, quantity received, note; saving adds a RECEIPT movement (inventory.write).
- **Data affected:** Stock movement
- **Confirmation:** No
- **Can it be undone:** Adjust with a reason
- **Next step:** --
- **Opens a dialog** first
- **Source evidence:** `app/(app)/products/[id]/page.tsx:571`

### Button: Transfer

- **Application:** Spare Parts Shop
- **Location:** Product details
- **Purpose:** Move stock between two locations.
- **What happens:** Opens Transfer stock: from, to (must differ), quantity (at most what is available there), note; saving adds TRANSFER_OUT and TRANSFER_IN.
- **Data affected:** Two stock movements
- **Confirmation:** No
- **Can it be undone:** Transfer back
- **Next step:** --
- **Opens a dialog** first
- **Source evidence:** `app/(app)/products/[id]/page.tsx:572`

### Button: Adjust

- **Application:** Spare Parts Shop
- **Location:** Product details
- **Purpose:** Correct the stock count.
- **What happens:** Opens Adjust stock: location, change in quantity (+/-, non-zero), reason (required).
- **Data affected:** --
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** Save adjustment
- **Opens a dialog** first
- **Source evidence:** `app/(app)/products/[id]/page.tsx:573`

### Button: Add / update supplier

- **Application:** Spare Parts Shop
- **Location:** Product details
- **Purpose:** Link a supplier to this product.
- **What happens:** Opens Supplier for this product: supplier, their part number, cost from them, preferred.
- **Data affected:** Product-supplier link
- **Confirmation:** No
- **Can it be undone:** Change it
- **Next step:** --
- **Opens a dialog** first
- **Source evidence:** `app/(app)/products/[id]/page.tsx:660`

### Button: Add number

- **Application:** Spare Parts Shop
- **Location:** Product details
- **Purpose:** Add another part number to this product.
- **What happens:** Opens Add part number (number, type such as OEM, aftermarket, cross reference...). A number already on the product is refused.
- **Data affected:** Part number
- **Confirmation:** No
- **Can it be undone:** Remove (the shop SKU cannot be removed)
- **Next step:** --
- **Opens a dialog** first
- **Source evidence:** `app/(app)/products/[id]/page.tsx:756`

### Button: Receive

- **Application:** Spare Parts Shop
- **Location:** Product details -> dialog "Receive stock — …"
- **Purpose:** Receive stock without a purchase order.
- **What happens:** Opens Receive stock: location, quantity received, note; saving adds a RECEIPT movement (inventory.write).
- **Data affected:** Stock movement
- **Confirmation:** No
- **Can it be undone:** Adjust with a reason
- **Next step:** --
- **Source evidence:** `ui/stock.tsx:77`

### Button: Save adjustment

- **Application:** Spare Parts Shop
- **Location:** Product details -> dialog "Adjust stock — …"
- **Purpose:** Save the stock correction.
- **What happens:** Adds an ADJUSTMENT_IN / ADJUSTMENT_OUT movement; refused if it would drop below what is reserved.
- **Data affected:** Stock movement
- **Confirmation:** No
- **Can it be undone:** Another adjustment
- **Next step:** --
- **Source evidence:** `ui/stock.tsx:110`

### Button: Transfer

- **Application:** Spare Parts Shop
- **Location:** Product details -> dialog "Transfer stock — …"
- **Purpose:** Move stock between two locations.
- **What happens:** Opens Transfer stock: from, to (must differ), quantity (at most what is available there), note; saving adds TRANSFER_OUT and TRANSFER_IN.
- **Data affected:** Two stock movements
- **Confirmation:** No
- **Can it be undone:** Transfer back
- **Next step:** --
- **Source evidence:** `ui/stock.tsx:134`

## Page: Purchase order (`/purchasing/[id]`)

### Button: Confirm

- **Application:** Spare Parts Shop
- **Location:** Purchase order
- **Purpose:** Confirm the purchase order.
- **What happens:** Status DRAFT -> CONFIRMED (purchasing.write).
- **Data affected:** PO status
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** Receive goods
- **Source evidence:** `app/(app)/purchasing/[id]/page.tsx:98`

### Button: Receive goods

- **Application:** Spare Parts Shop
- **Location:** Purchase order
- **Purpose:** Record goods that arrived for this purchase order.
- **What happens:** Opens a dialog with the quantity received per line (pre-filled with what is outstanding).
- **Data affected:** --
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** Receive into stock
- **Source evidence:** `app/(app)/purchasing/[id]/page.tsx:109`

### Button: Receive into stock

- **Application:** Spare Parts Shop
- **Location:** Purchase order -> dialog "Receive goods"
- **Purpose:** Save the receipt.
- **What happens:** Stock on hand increases (RECEIPT movements); PO becomes PARTIALLY_RECEIVED or RECEIVED.
- **Data affected:** Stock, PO status
- **Confirmation:** No
- **Can it be undone:** Adjust stock with a reason
- **Next step:** --
- **Source evidence:** `app/(app)/purchasing/[id]/page.tsx:233`

## Page: New purchase order (`/purchasing/new`)

### Button: Save draft

- **Application:** Spare Parts Shop
- **Location:** New purchase order
- **Purpose:** Save the new document as a draft.
- **What happens:** Creates a DRAFT quotation / purchase order (at least one line; every line needs a description and a price above zero).
- **Data affected:** New draft document
- **Confirmation:** No
- **Can it be undone:** Edit lines while draft / cancel
- **Next step:** Issue (quotation) or Confirm (PO)
- **Source evidence:** `app/(app)/purchasing/new/page.tsx:109`

### Button: Remove line

- **Application:** Spare Parts Shop
- **Location:** New purchase order
- **Purpose:** Remove a line from the draft.
- **What happens:** The line is removed from the draft.
- **Data affected:** Draft only
- **Confirmation:** No
- **Can it be undone:** Add it again
- **Next step:** --
- **Source evidence:** `ui/lines.tsx:274`

### Button: Add a free-text line

- **Application:** Spare Parts Shop
- **Location:** New purchase order
- **Purpose:** Add a line that is not a stocked product.
- **What happens:** Adds an empty line to fill in.
- **Data affected:** Draft only
- **Confirmation:** No
- **Can it be undone:** Remove line
- **Next step:** --
- **Source evidence:** `ui/lines.tsx:285`

## Page: Quotation (`/quotations/[id]`)

### Button: Edit lines

- **Application:** Spare Parts Shop
- **Location:** Quotation
- **Purpose:** Change the lines of a draft quotation.
- **What happens:** Opens the line editor.
- **Data affected:** Quotation lines
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** Save
- **Source evidence:** `app/(app)/quotations/[id]/page.tsx:114`

### Button: Issue to customer

- **Application:** Spare Parts Shop
- **Location:** Quotation
- **Purpose:** Issue the quotation to the customer.
- **What happens:** Status DRAFT -> ISSUED (valid-until date must not be in the past); the PDF can be printed / sent.
- **Data affected:** Quotation status
- **Confirmation:** No
- **Can it be undone:** Cancel the quotation
- **Next step:** Customer accepted / rejected
- **Source evidence:** `app/(app)/quotations/[id]/page.tsx:119`

### Button: Customer accepted

- **Application:** Spare Parts Shop
- **Location:** Quotation
- **Purpose:** Record that the customer accepted.
- **What happens:** Status ISSUED -> ACCEPTED.
- **Data affected:** Quotation status
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** Create order
- **Source evidence:** `app/(app)/quotations/[id]/page.tsx:128`

### Button: Customer rejected

- **Application:** Spare Parts Shop
- **Location:** Quotation
- **Purpose:** Record that the customer rejected.
- **What happens:** Status ISSUED -> REJECTED.
- **Data affected:** Quotation status
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Source evidence:** `app/(app)/quotations/[id]/page.tsx:134`

### Button: Create order

- **Application:** Spare Parts Shop
- **Location:** Quotation
- **Purpose:** Create the sales order from the accepted quotation.
- **What happens:** Opens a dialog asking what to do if stock is short (Do not create the order / Create it and back-order the shortfall); creating the order reserves available stock.
- **Data affected:** New sales order (CONFIRMED); stock reserved
- **Confirmation:** Yes (dialog)
- **Can it be undone:** Cancel order (releases the reservation)
- **Next step:** Record delivery
- **Opens a dialog** first
- **Source evidence:** `app/(app)/quotations/[id]/page.tsx:142`

### Button: Cancel

- **Application:** Spare Parts Shop
- **Location:** Quotation -> dialog "Edit …"
- **Purpose:** Close the dialog or form without saving.
- **What happens:** Nothing is saved.
- **Data affected:** None
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** --
- **Source evidence:** `app/(app)/quotations/[id]/page.tsx:219`

### Button: Save

- **Application:** Spare Parts Shop
- **Location:** Quotation -> dialog "Edit …"
- **Purpose:** Save the form.
- **What happens:** The values are sent to the server and validated; on success the dialog closes and the list refreshes; on a validation error the message is shown and nothing is saved.
- **Data affected:** The record being edited
- **Confirmation:** No
- **Can it be undone:** Edit again
- **Next step:** --
- **Source evidence:** `app/(app)/quotations/[id]/page.tsx:220`

### Button: Create order

- **Application:** Spare Parts Shop
- **Location:** Quotation -> dialog "Create order"
- **Purpose:** Create the sales order from the accepted quotation.
- **What happens:** Opens a dialog asking what to do if stock is short (Do not create the order / Create it and back-order the shortfall); creating the order reserves available stock.
- **Data affected:** New sales order (CONFIRMED); stock reserved
- **Confirmation:** Yes (dialog)
- **Can it be undone:** Cancel order (releases the reservation)
- **Next step:** Record delivery
- **Source evidence:** `app/(app)/quotations/[id]/page.tsx:246`

### Button: Remove line

- **Application:** Spare Parts Shop
- **Location:** Quotation
- **Purpose:** Remove a line from the draft.
- **What happens:** The line is removed from the draft.
- **Data affected:** Draft only
- **Confirmation:** No
- **Can it be undone:** Add it again
- **Next step:** --
- **Source evidence:** `ui/lines.tsx:274`

### Button: Add a free-text line

- **Application:** Spare Parts Shop
- **Location:** Quotation
- **Purpose:** Add a line that is not a stocked product.
- **What happens:** Adds an empty line to fill in.
- **Data affected:** Draft only
- **Confirmation:** No
- **Can it be undone:** Remove line
- **Next step:** --
- **Source evidence:** `ui/lines.tsx:285`

## Page: New quotation (`/quotations/new`)

### Button: Save draft

- **Application:** Spare Parts Shop
- **Location:** New quotation
- **Purpose:** Save the new document as a draft.
- **What happens:** Creates a DRAFT quotation / purchase order (at least one line; every line needs a description and a price above zero).
- **Data affected:** New draft document
- **Confirmation:** No
- **Can it be undone:** Edit lines while draft / cancel
- **Next step:** Issue (quotation) or Confirm (PO)
- **Source evidence:** `app/(app)/quotations/new/page.tsx:79`

### Button: Remove line

- **Application:** Spare Parts Shop
- **Location:** New quotation
- **Purpose:** Remove a line from the draft.
- **What happens:** The line is removed from the draft.
- **Data affected:** Draft only
- **Confirmation:** No
- **Can it be undone:** Add it again
- **Next step:** --
- **Source evidence:** `ui/lines.tsx:274`

### Button: Add a free-text line

- **Application:** Spare Parts Shop
- **Location:** New quotation
- **Purpose:** Add a line that is not a stocked product.
- **What happens:** Adds an empty line to fill in.
- **Data affected:** Draft only
- **Confirmation:** No
- **Can it be undone:** Remove line
- **Next step:** --
- **Source evidence:** `ui/lines.tsx:285`

## Page: Suppliers (`/suppliers`)

### Button: New supplier

- **Application:** Spare Parts Shop
- **Location:** Suppliers
- **Purpose:** Create a supplier.
- **What happens:** Opens the New supplier form (suppliers.write).
- **Data affected:** New supplier record
- **Confirmation:** No
- **Can it be undone:** Edit / set Inactive
- **Next step:** Create a purchase order
- **Opens a dialog** first
- **Source evidence:** `app/(app)/suppliers/page.tsx:33`

## Page: Supplier (`/suppliers/[id]`)

### Button: Edit

- **Application:** Spare Parts Shop
- **Location:** Supplier
- **Purpose:** Open the edit form for this record.
- **What happens:** Opens a dialog with the current values.
- **Data affected:** None until saved
- **Confirmation:** No
- **Can it be undone:** --
- **Next step:** Save
- **Opens a dialog** first
- **Source evidence:** `app/(app)/suppliers/[id]/page.tsx:69`
