# Spare Parts Shop -- field reference (Level 1)

Every user-visible form field found in the code, page by page. *Required* is what the form itself enforces; the server checks again. Purposes marked NOT CONFIRMED are fields whose meaning the code does not make clear enough to state.

Server-side rules for every Spare Parts text input (`src/server/domain/validate.ts`): empty required text -> "<field> is required."; longer than the limit (default 500) -> "<field> must be at most N characters."; control characters -> "<field> contains invalid characters."; email -> "<field> is not a valid email address."; currency -> "Currency must be a 3-letter code such as AED."; whole numbers -> "<field> must be a whole number." / "must be at least N"; dates -> "must be a date (YYYY-MM-DD)". Money is stored as whole minor units (cents/fils).

## Page: Shop settings (`/admin/settings`)

### Field: Shop name

- **Application:** Spare Parts Shop
- **Page:** Shop settings
- **Type:** text
- **Purpose:** The name of the shop, shown in the app and printed on quotations and invoices.
- **What user enters:** Text.
- **Required:** Yes
- **Validation:** required by the form; server rules: see top of this document
- **Permission:** `settings.manage` (every save on this page needs it: `PUT /settings`)
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** Tax registration number, Phone, Email, Address, Currency, Default tax rate (%), Quotation valid for (days), Invoice due after (days)
- **Source evidence:** `app/(app)/admin/settings/page.tsx:77`

### Field: Tax registration number

- **Application:** Spare Parts Shop
- **Page:** Shop settings
- **Type:** text
- **Purpose:** The shop's tax / VAT registration number, printed on documents.
- **What user enters:** Text.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `settings.manage` (every save on this page needs it: `PUT /settings`)
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** Shop name, Phone, Email, Address, Currency, Default tax rate (%), Quotation valid for (days), Invoice due after (days)
- **Source evidence:** `app/(app)/admin/settings/page.tsx:80`

### Field: Phone

- **Application:** Spare Parts Shop
- **Page:** Shop settings
- **Type:** text
- **Purpose:** Telephone number of the person or company.
- **What user enters:** Text.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `settings.manage` (every save on this page needs it: `PUT /settings`)
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** Shop name, Tax registration number, Email, Address, Currency, Default tax rate (%), Quotation valid for (days), Invoice due after (days)
- **Source evidence:** `app/(app)/admin/settings/page.tsx:86`

### Field: Email

- **Application:** Spare Parts Shop
- **Page:** Shop settings
- **Type:** email
- **Purpose:** Email address of the person or company.
- **What user enters:** An email address.
- **Required:** No (form does not require it)
- **Validation:** must be an email address; server rules: see top of this document
- **Permission:** `settings.manage` (every save on this page needs it: `PUT /settings`)
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** Shop name, Tax registration number, Phone, Address, Currency, Default tax rate (%), Quotation valid for (days), Invoice due after (days)
- **Source evidence:** `app/(app)/admin/settings/page.tsx:89`

### Field: Address

- **Application:** Spare Parts Shop
- **Page:** Shop settings
- **Type:** textarea
- **Purpose:** Postal / street address.
- **What user enters:** Free text (several lines allowed).
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `settings.manage` (every save on this page needs it: `PUT /settings`)
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** Shop name, Tax registration number, Phone, Email, Currency, Default tax rate (%), Quotation valid for (days), Invoice due after (days)
- **Source evidence:** `app/(app)/admin/settings/page.tsx:92`

### Field: Currency

- **Application:** Spare Parts Shop
- **Page:** Shop settings
- **Type:** text
- **Purpose:** 3-letter currency code (for example AED) used for prices and documents.
- **What user enters:** Text. Hint shown: "3-letter code. Existing documents keep the currency they were issued in.".
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `settings.manage` (every save on this page needs it: `PUT /settings`)
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** Shop name, Tax registration number, Phone, Email, Address, Default tax rate (%), Quotation valid for (days), Invoice due after (days)
- **Source evidence:** `app/(app)/admin/settings/page.tsx:99`

### Field: Default tax rate (%)

- **Application:** Spare Parts Shop
- **Page:** Shop settings
- **Type:** text
- **Purpose:** Tax percentage applied to new document lines unless changed.
- **What user enters:** Text.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `settings.manage` (every save on this page needs it: `PUT /settings`)
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** Shop name, Tax registration number, Phone, Email, Address, Currency, Quotation valid for (days), Invoice due after (days)
- **Source evidence:** `app/(app)/admin/settings/page.tsx:109`

### Field: Quotation valid for (days)

- **Application:** Spare Parts Shop
- **Page:** Shop settings
- **Type:** text
- **Purpose:** How many days a new quotation stays valid; used to set its valid-until date.
- **What user enters:** Text.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `settings.manage` (every save on this page needs it: `PUT /settings`)
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** Shop name, Tax registration number, Phone, Email, Address, Currency, Default tax rate (%), Invoice due after (days)
- **Source evidence:** `app/(app)/admin/settings/page.tsx:116`

### Field: Invoice due after (days)

- **Application:** Spare Parts Shop
- **Page:** Shop settings
- **Type:** text
- **Purpose:** How many days after issue a new invoice is due; used for overdue tracking.
- **What user enters:** Text.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `settings.manage` (every save on this page needs it: `PUT /settings`)
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** Shop name, Tax registration number, Phone, Email, Address, Currency, Default tax rate (%), Quotation valid for (days)
- **Source evidence:** `app/(app)/admin/settings/page.tsx:123`

### Field: Standard quotation terms

- **Application:** Spare Parts Shop
- **Page:** Shop settings
- **Type:** textarea
- **Purpose:** Terms text printed on every quotation.
- **What user enters:** Free text (several lines allowed).
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `settings.manage` (every save on this page needs it: `PUT /settings`)
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** Shop name, Tax registration number, Phone, Email, Address, Currency, Default tax rate (%), Quotation valid for (days)
- **Source evidence:** `app/(app)/admin/settings/page.tsx:130`

### Field: Standard invoice notes

- **Application:** Spare Parts Shop
- **Page:** Shop settings
- **Type:** textarea
- **Purpose:** Notes text printed on every invoice.
- **What user enters:** Free text (several lines allowed).
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `settings.manage` (every save on this page needs it: `PUT /settings`)
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** Shop name, Tax registration number, Phone, Email, Address, Currency, Default tax rate (%), Quotation valid for (days)
- **Source evidence:** `app/(app)/admin/settings/page.tsx:137`

## Page: Users (`/admin/users`)

### Field: Name

- **Application:** Spare Parts Shop
- **Page:** Users -> dialog "Add user"
- **Type:** text
- **Purpose:** The name of the record (customer, supplier, warehouse, product...).
- **What user enters:** Text.
- **Required:** Yes
- **Validation:** required by the form; server rules: see top of this document
- **Permission:** `users.manage` (the dialog saves with `POST /users`)
- **What happens after Save:** the "Add user" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Email (used to sign in), Role, Temporary password
- **Source evidence:** `app/(app)/admin/users/page.tsx:111`

### Field: Email (used to sign in)

- **Application:** Spare Parts Shop
- **Page:** Users -> dialog "Add user"
- **Type:** email
- **Purpose:** Standalone mode only: the user's sign-in email.
- **What user enters:** An email address.
- **Required:** Yes
- **Validation:** required by the form; must be an email address; server rules: see top of this document
- **Permission:** `users.manage` (the dialog saves with `POST /users`)
- **What happens after Save:** the "Add user" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Name, Role, Temporary password
- **Source evidence:** `app/(app)/admin/users/page.tsx:112`

### Field: Role

- **Application:** Spare Parts Shop
- **Page:** Users -> dialog "Add user"
- **Type:** select
- **Purpose:** The person's role (standalone mode only; inside IntraForge roles are set in IntraForge).
- **What user enters:** Choose one option.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `users.manage` (the dialog saves with `POST /users`)
- **What happens after Save:** the "Add user" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Name, Email (used to sign in), Temporary password
- **Source evidence:** `app/(app)/admin/users/page.tsx:118`

### Field: Temporary password

- **Application:** Spare Parts Shop
- **Page:** Users -> dialog "Add user"
- **Type:** password
- **Purpose:** Standalone mode only: a first password the user must change.
- **What user enters:** A password. Hint shown: "At least 10 characters. They must change it at first sign-in.".
- **Required:** Yes
- **Validation:** required by the form; server rules: see top of this document
- **Permission:** `users.manage` (the dialog saves with `POST /users`)
- **What happens after Save:** the "Add user" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Name, Email (used to sign in), Role
- **Source evidence:** `app/(app)/admin/users/page.tsx:119`

### Field: Name

- **Application:** Spare Parts Shop
- **Page:** Users -> dialog "Edit …"
- **Type:** text
- **Purpose:** The name of the record (customer, supplier, warehouse, product...).
- **What user enters:** Text.
- **Required:** Yes
- **Validation:** required by the form; server rules: see top of this document
- **Permission:** `users.manage` (every save on this page needs it: `PATCH /users/:id`, `POST /users`)
- **What happens after Save:** the "Edit …" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Role
- **Source evidence:** `app/(app)/admin/users/page.tsx:136`

### Field: Role

- **Application:** Spare Parts Shop
- **Page:** Users -> dialog "Edit …"
- **Type:** select
- **Purpose:** The person's role (standalone mode only; inside IntraForge roles are set in IntraForge).
- **What user enters:** Choose one option.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `users.manage` (every save on this page needs it: `PATCH /users/:id`, `POST /users`)
- **What happens after Save:** the "Edit …" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Name
- **Source evidence:** `app/(app)/admin/users/page.tsx:137`

### Field: New temporary password

- **Application:** Spare Parts Shop
- **Page:** Users -> dialog "Reset password — …"
- **Type:** password
- **Purpose:** Standalone mode only: reset a user's password.
- **What user enters:** A password. Hint shown: "Their existing sessions end immediately.".
- **Required:** Yes
- **Validation:** required by the form; server rules: see top of this document
- **Permission:** `users.manage` (the dialog saves with `POST /users`)
- **What happens after Save:** the "Reset password — …" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Source evidence:** `app/(app)/admin/users/page.tsx:151`

## Page: Reference Catalogue (`/catalogue`)

### Field: Manufacturer

- **Application:** Spare Parts Shop
- **Page:** Reference Catalogue
- **Type:** select (options: Any)
- **Purpose:** Manufacturer of the part.
- **What user enters:** Choose one option: Any.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `enquiries.write` (every save on this page needs it: `POST /enquiries/items`)
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** Model, Chassis / frame, Engine, Market, Part status, Only parts that appear on a drawing
- **Source evidence:** `app/(app)/catalogue/page.tsx:160`

### Field: Model

- **Application:** Spare Parts Shop
- **Page:** Reference Catalogue
- **Type:** text
- **Purpose:** Catalogue filter: vehicle model.
- **What user enters:** Text.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `enquiries.write` (every save on this page needs it: `POST /enquiries/items`)
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** Manufacturer, Chassis / frame, Engine, Market, Part status, Only parts that appear on a drawing
- **Source evidence:** `app/(app)/catalogue/page.tsx:174`

### Field: Chassis / frame

- **Application:** Spare Parts Shop
- **Page:** Reference Catalogue
- **Type:** select (options: Any, Any)
- **Purpose:** Catalogue filter: chassis / frame code.
- **What user enters:** Choose one option: Any, Any.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `enquiries.write` (every save on this page needs it: `POST /enquiries/items`)
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** Manufacturer, Model, Engine, Market, Part status, Only parts that appear on a drawing
- **Source evidence:** `app/(app)/catalogue/page.tsx:188`

### Field: Engine

- **Application:** Spare Parts Shop
- **Page:** Reference Catalogue
- **Type:** select (options: Any, Any, Active, Ended / discontinued, Superseded)
- **Purpose:** Catalogue filter: engine code.
- **What user enters:** Choose one option: Any, Any, Active, Ended / discontinued, Superseded.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `enquiries.write` (every save on this page needs it: `POST /enquiries/items`)
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** Manufacturer, Model, Chassis / frame, Market, Part status, Only parts that appear on a drawing
- **Source evidence:** `app/(app)/catalogue/page.tsx:196`

### Field: Market

- **Application:** Spare Parts Shop
- **Page:** Reference Catalogue
- **Type:** select (options: Any, Active, Ended / discontinued, Superseded)
- **Purpose:** Catalogue filter: market.
- **What user enters:** Choose one option: Any, Active, Ended / discontinued, Superseded.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `enquiries.write` (every save on this page needs it: `POST /enquiries/items`)
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** Manufacturer, Model, Chassis / frame, Engine, Part status, Only parts that appear on a drawing
- **Source evidence:** `app/(app)/catalogue/page.tsx:208`

### Field: Part status

- **Application:** Spare Parts Shop
- **Page:** Reference Catalogue
- **Type:** checkbox
- **Purpose:** Catalogue filter: part status.
- **What user enters:** Tick to switch on.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `enquiries.write` (every save on this page needs it: `POST /enquiries/items`)
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** Manufacturer, Model, Chassis / frame, Engine, Market, Only parts that appear on a drawing
- **Source evidence:** `app/(app)/catalogue/page.tsx:220`

### Field: Only parts that appear on a drawing

- **Application:** Spare Parts Shop
- **Page:** Reference Catalogue
- **Type:** checkbox
- **Purpose:** Catalogue filter: show only parts that are on a drawing.
- **What user enters:** Tick to switch on.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `enquiries.write` (every save on this page needs it: `POST /enquiries/items`)
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** Manufacturer, Model, Chassis / frame, Engine, Market, Part status
- **Source evidence:** `app/(app)/catalogue/page.tsx:233`

## Page: Import reference catalogue (`/catalogue/import`)

### Field: I confirm that my organisation is allowed to use this data.

- **Application:** Spare Parts Shop
- **Page:** Import reference catalogue
- **Type:** checkbox
- **Purpose:** Required confirmation before importing: you must be permitted to use the data (licence / ownership).
- **What user enters:** Tick to switch on.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `catalogue.import` (the page's own permission; its save call is not visible to the extractor -- NOT CONFIRMED beyond the page)
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** I confirm we are licensed to store and display the … image(s) in this package. Without this, images are skipped and only their source links are kept., Default manufacturer, Default source name, Default market
- **Source evidence:** `app/(app)/catalogue/import/page.tsx:260`

### Field: I confirm we are licensed to store and display the … image(s) in this package. Without this, images are skipped and only their source links are kept.

- **Application:** Spare Parts Shop
- **Page:** Import reference catalogue
- **Type:** checkbox
- **Purpose:** Required to import a package's drawing images: confirm the shop is licensed to store and show them; without it images are skipped and only their source links kept.
- **What user enters:** Tick to switch on.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `catalogue.import` (the page's own permission; its save call is not visible to the extractor -- NOT CONFIRMED beyond the page)
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** I confirm that my organisation is allowed to use this data., Default manufacturer, Default source name, Default market
- **Source evidence:** `app/(app)/catalogue/import/page.tsx:403`

### Field: Default manufacturer

- **Application:** Spare Parts Shop
- **Page:** Import reference catalogue
- **Type:** text
- **Purpose:** Used for imported rows whose manufacturer column is empty.
- **What user enters:** Text. Hint shown: "Used for rows where the manufacturer column is empty or not mapped.".
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `catalogue.import` (the page's own permission; its save call is not visible to the extractor -- NOT CONFIRMED beyond the page)
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** I confirm that my organisation is allowed to use this data., I confirm we are licensed to store and display the … image(s) in this package. Without this, images are skipped and only their source links are kept., Default source name, Default market
- **Source evidence:** `app/(app)/catalogue/import/page.tsx:193`

### Field: Default source name

- **Application:** Spare Parts Shop
- **Page:** Import reference catalogue
- **Type:** text
- **Purpose:** Name of the source recorded on every imported row (for example the supplier or catalogue).
- **What user enters:** Text. Hint shown: "Recorded as the origin of these rows.".
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `catalogue.import` (the page's own permission; its save call is not visible to the extractor -- NOT CONFIRMED beyond the page)
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** I confirm that my organisation is allowed to use this data., I confirm we are licensed to store and display the … image(s) in this package. Without this, images are skipped and only their source links are kept., Default manufacturer, Default market
- **Source evidence:** `app/(app)/catalogue/import/page.tsx:207`

### Field: Default market

- **Application:** Spare Parts Shop
- **Page:** Import reference catalogue
- **Type:** text
- **Purpose:** Market recorded on imported rows that have none (for example JP, EU).
- **What user enters:** Text.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `catalogue.import` (the page's own permission; its save call is not visible to the extractor -- NOT CONFIRMED beyond the page)
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** I confirm that my organisation is allowed to use this data., I confirm we are licensed to store and display the … image(s) in this package. Without this, images are skipped and only their source links are kept., Default manufacturer, Default source name
- **Source evidence:** `app/(app)/catalogue/import/page.tsx:218`

## Page: Reference part details (`/catalogue/parts/[id]`)

### Field: Your SKU

- **Application:** Spare Parts Shop
- **Page:** Reference part details -> dialog "Import … to My Products"
- **Type:** text
- **Purpose:** The shop's own unique code for the product created from this reference part.
- **What user enters:** Text. Hint shown: "Your own stock code for this item.".
- **Required:** Yes
- **Validation:** required by the form; server rules: see top of this document
- **Permission:** `products.write` (the dialog saves with `POST /catalogue/parts/:id/import-to-products`)
- **What happens after Save:** the "Import … to My Products" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Product name, Selling price, Cost price, Reorder level, Supplier, Store in, Quantity in stock now
- **Source evidence:** `app/(app)/catalogue/parts/[id]/page.tsx:117`

### Field: Product name

- **Application:** Spare Parts Shop
- **Page:** Reference part details -> dialog "Import … to My Products"
- **Type:** text
- **Purpose:** The name of the shop product created from this reference part.
- **What user enters:** Text.
- **Required:** Yes
- **Validation:** required by the form; server rules: see top of this document
- **Permission:** `products.write` (the dialog saves with `POST /catalogue/parts/:id/import-to-products`)
- **What happens after Save:** the "Import … to My Products" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Your SKU, Selling price, Cost price, Reorder level, Supplier, Store in, Quantity in stock now
- **Source evidence:** `app/(app)/catalogue/parts/[id]/page.tsx:123`

### Field: Selling price

- **Application:** Spare Parts Shop
- **Page:** Reference part details -> dialog "Import … to My Products"
- **Type:** money
- **Purpose:** The price the shop charges the customer. Used to price quotation lines automatically.
- **What user enters:** An amount, for example 125.00.
- **Required:** No (left out when empty)
- **Validation:** amount (money); server rules: see top of this document
- **Permission:** `products.write` (the dialog saves with `POST /catalogue/parts/:id/import-to-products`)
- **What happens after Save:** the "Import … to My Products" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Your SKU, Product name, Cost price, Reorder level, Supplier, Store in, Quantity in stock now
- **Source evidence:** `app/(app)/catalogue/parts/[id]/page.tsx:124`

### Field: Cost price

- **Application:** Spare Parts Shop
- **Page:** Reference part details -> dialog "Import … to My Products"
- **Type:** money
- **Purpose:** What the shop pays for the part. Only visible and editable with the cost permission (products.cost.read); used for stock value.
- **What user enters:** An amount, for example 125.00.
- **Required:** No (left out when empty)
- **Validation:** amount (money); server rules: see top of this document
- **Permission:** `products.write` (the dialog saves with `POST /catalogue/parts/:id/import-to-products`)
- **What happens after Save:** the "Import … to My Products" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Your SKU, Product name, Selling price, Reorder level, Supplier, Store in, Quantity in stock now
- **Source evidence:** `app/(app)/catalogue/parts/[id]/page.tsx:132`

### Field: Reorder level

- **Application:** Spare Parts Shop
- **Page:** Reference part details -> dialog "Import … to My Products"
- **Type:** number
- **Purpose:** When available stock falls to this number, the product shows as low stock / needs reordering.
- **What user enters:** A whole number.
- **Required:** No (left out when empty)
- **Validation:** number; server rules: see top of this document
- **Permission:** `products.write` (the dialog saves with `POST /catalogue/parts/:id/import-to-products`)
- **What happens after Save:** the "Import … to My Products" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Your SKU, Product name, Selling price, Cost price, Supplier, Store in, Quantity in stock now
- **Source evidence:** `app/(app)/catalogue/parts/[id]/page.tsx:140`

### Field: Supplier

- **Application:** Spare Parts Shop
- **Page:** Reference part details -> dialog "Import … to My Products"
- **Type:** select (options: — none —)
- **Purpose:** The supplier (company you buy from).
- **What user enters:** Choose one option: — none —.
- **Required:** No (left out when empty)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `products.write` (the dialog saves with `POST /catalogue/parts/:id/import-to-products`)
- **What happens after Save:** the "Import … to My Products" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Your SKU, Product name, Selling price, Cost price, Reorder level, Store in, Quantity in stock now
- **Source evidence:** `app/(app)/catalogue/parts/[id]/page.tsx:148`

### Field: Store in

- **Application:** Spare Parts Shop
- **Page:** Reference part details -> dialog "Import … to My Products"
- **Type:** select (options: — no stock yet —)
- **Purpose:** Location where stock of the new product is stored.
- **What user enters:** Choose one option: — no stock yet —.
- **Required:** No (left out when empty)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `products.write` (the dialog saves with `POST /catalogue/parts/:id/import-to-products`)
- **What happens after Save:** the "Import … to My Products" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Your SKU, Product name, Selling price, Cost price, Reorder level, Supplier, Quantity in stock now
- **Source evidence:** `app/(app)/catalogue/parts/[id]/page.tsx:165`

### Field: Quantity in stock now

- **Application:** Spare Parts Shop
- **Page:** Reference part details -> dialog "Import … to My Products"
- **Type:** number
- **Purpose:** Stock already on the shelf, recorded as an opening balance when the product is created.
- **What user enters:** A whole number.
- **Required:** No (left out when empty)
- **Validation:** number; server rules: see top of this document
- **Permission:** `products.write` (the dialog saves with `POST /catalogue/parts/:id/import-to-products`)
- **What happens after Save:** the "Import … to My Products" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Your SKU, Product name, Selling price, Cost price, Reorder level, Supplier, Store in
- **Source evidence:** `app/(app)/catalogue/parts/[id]/page.tsx:175`

### Field: Verification

- **Application:** Spare Parts Shop
- **Page:** Reference part details
- **Type:** text
- **Purpose:** Whether the reference part's data has been verified (catalogue administrators).
- **What user enters:** Text.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** NOT CONFIRMED for this field; the page's write calls are `PUT /catalogue/parts/:id/verification` -> `catalogue.admin`, `POST /catalogue/parts/:id/import-to-products` -> `products.write`, `POST /enquiries/items` -> `enquiries.write`, `POST /inventory/receive` -> `inventory.write`, `POST /inventory/adjust` -> `inventory.write`, `POST /inventory/transfer` -> `inventory.write`
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Source evidence:** `app/(app)/catalogue/parts/[id]/page.tsx:399`

### Field: Location

- **Application:** Spare Parts Shop
- **Page:** Reference part details -> dialog "Receive stock — …"
- **Type:** select
- **Purpose:** A place in a warehouse (rack / shelf / bin) where stock is kept.
- **What user enters:** Choose one option.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `inventory.write` (the dialog saves with `POST /inventory/receive`)
- **What happens after Save:** the "Receive stock — …" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Quantity received, Note (delivery note, source)
- **Source evidence:** `ui/stock.tsx:59`

### Field: Quantity received

- **Application:** Spare Parts Shop
- **Page:** Reference part details -> dialog "Receive stock — …"
- **Type:** number
- **Purpose:** How many units arrived. Stock on hand increases by this amount.
- **What user enters:** A whole number.
- **Required:** Yes
- **Validation:** required by the form; number; server rules: see top of this document
- **Permission:** `inventory.write` (the dialog saves with `POST /inventory/receive`)
- **What happens after Save:** the "Receive stock — …" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Location, Note (delivery note, source)
- **Source evidence:** `ui/stock.tsx:65`

### Field: Note (delivery note, source)

- **Application:** Spare Parts Shop
- **Page:** Reference part details -> dialog "Receive stock — …"
- **Type:** text
- **Purpose:** Reference for the receipt, for example the supplier's delivery note number.
- **What user enters:** Text.
- **Required:** No (left out when empty)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `inventory.write` (the dialog saves with `POST /inventory/receive`)
- **What happens after Save:** the "Receive stock — …" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Location, Quantity received
- **Source evidence:** `ui/stock.tsx:71`

### Field: Location

- **Application:** Spare Parts Shop
- **Page:** Reference part details -> dialog "Adjust stock — …"
- **Type:** select
- **Purpose:** A place in a warehouse (rack / shelf / bin) where stock is kept.
- **What user enters:** Choose one option.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `inventory.write` (the dialog saves with `POST /inventory/adjust`)
- **What happens after Save:** the "Adjust stock — …" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Change in quantity, Reason
- **Source evidence:** `ui/stock.tsx:91`

### Field: Change in quantity

- **Application:** Spare Parts Shop
- **Page:** Reference part details -> dialog "Adjust stock — …"
- **Type:** number
- **Purpose:** How much to add (positive) or remove (negative). Must be a non-zero whole number.
- **What user enters:** A whole number. Hint shown: "Use a negative number to remove stock, e.g. -2 for damaged goods.".
- **Required:** Yes
- **Validation:** required by the form; number; server rules: see top of this document
- **Permission:** `inventory.write` (the dialog saves with `POST /inventory/adjust`)
- **What happens after Save:** the "Adjust stock — …" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Location, Reason
- **Source evidence:** `ui/stock.tsx:97`

### Field: Reason

- **Application:** Spare Parts Shop
- **Page:** Reference part details -> dialog "Adjust stock — …"
- **Type:** textarea
- **Purpose:** Why stock is adjusted. Required -- every adjustment must be explained.
- **What user enters:** Free text (several lines allowed).
- **Required:** Yes
- **Validation:** required by the form; server rules: see top of this document
- **Permission:** `inventory.write` (the dialog saves with `POST /inventory/adjust`)
- **What happens after Save:** the "Adjust stock — …" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Location, Change in quantity
- **Source evidence:** `ui/stock.tsx:104`

### Field: From

- **Application:** Spare Parts Shop
- **Page:** Reference part details -> dialog "Transfer stock — …"
- **Type:** select
- **Purpose:** Where stock moves from (transfer) / start of a period (reports).
- **What user enters:** Choose one option.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `inventory.write` (the dialog saves with `POST /inventory/transfer`)
- **What happens after Save:** the "Transfer stock — …" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** To, Quantity, Note
- **Source evidence:** `ui/stock.tsx:125`

### Field: To

- **Application:** Spare Parts Shop
- **Page:** Reference part details -> dialog "Transfer stock — …"
- **Type:** select
- **Purpose:** Where stock moves to (transfer) / end of a period (reports).
- **What user enters:** Choose one option.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `inventory.write` (the dialog saves with `POST /inventory/transfer`)
- **What happens after Save:** the "Transfer stock — …" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** From, Quantity, Note
- **Source evidence:** `ui/stock.tsx:126`

### Field: Quantity

- **Application:** Spare Parts Shop
- **Page:** Reference part details -> dialog "Transfer stock — …"
- **Type:** number
- **Purpose:** Number of units.
- **What user enters:** A whole number.
- **Required:** Yes
- **Validation:** required by the form; number; server rules: see top of this document
- **Permission:** `inventory.write` (the dialog saves with `POST /inventory/transfer`)
- **What happens after Save:** the "Transfer stock — …" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** From, To, Note
- **Source evidence:** `ui/stock.tsx:127`

### Field: Note

- **Application:** Spare Parts Shop
- **Page:** Reference part details -> dialog "Transfer stock — …"
- **Type:** text
- **Purpose:** Free note recorded with the movement or document.
- **What user enters:** Text.
- **Required:** No (left out when empty)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `inventory.write` (the dialog saves with `POST /inventory/transfer`)
- **What happens after Save:** the "Transfer stock — …" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** From, To, Quantity
- **Source evidence:** `ui/stock.tsx:128`

## Page: Customers (`/customers`)

### Field: Status

- **Application:** Spare Parts Shop
- **Page:** Customers -> dialog "New customer"
- **Type:** select (options: Active, Inactive)
- **Purpose:** Active or Inactive. Inactive records stay in history but are not offered for new documents.
- **What user enters:** Choose one option: Active, Inactive.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `customers.write` (the dialog saves with `POST /customers`)
- **What happens after Save:** the "New customer" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Name, Contact person, Phone, Email, Country, Tax number, Currency, Payment terms
- **Source evidence:** `ui/parties.ts:3`

### Field: Name

- **Application:** Spare Parts Shop
- **Page:** Customers -> dialog "New customer"
- **Type:** text
- **Purpose:** The name of the record (customer, supplier, warehouse, product...).
- **What user enters:** Text.
- **Required:** Yes
- **Validation:** required by the form; server rules: see top of this document
- **Permission:** `customers.write` (the dialog saves with `POST /customers`)
- **What happens after Save:** the "New customer" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Status, Contact person, Phone, Email, Country, Tax number, Currency, Payment terms
- **Source evidence:** `ui/parties.ts:13`

### Field: Contact person

- **Application:** Spare Parts Shop
- **Page:** Customers -> dialog "New customer"
- **Type:** text
- **Purpose:** The person to talk to at this customer or supplier.
- **What user enters:** Text.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `customers.write` (the dialog saves with `POST /customers`)
- **What happens after Save:** the "New customer" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Status, Name, Phone, Email, Country, Tax number, Currency, Payment terms
- **Source evidence:** `ui/parties.ts:14`

### Field: Phone

- **Application:** Spare Parts Shop
- **Page:** Customers -> dialog "New customer"
- **Type:** text
- **Purpose:** Telephone number of the person or company.
- **What user enters:** Text.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `customers.write` (the dialog saves with `POST /customers`)
- **What happens after Save:** the "New customer" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Status, Name, Contact person, Email, Country, Tax number, Currency, Payment terms
- **Source evidence:** `ui/parties.ts:15`

### Field: Email

- **Application:** Spare Parts Shop
- **Page:** Customers -> dialog "New customer"
- **Type:** email
- **Purpose:** Email address of the person or company.
- **What user enters:** An email address.
- **Required:** No (form does not require it)
- **Validation:** must be an email address; server rules: see top of this document
- **Permission:** `customers.write` (the dialog saves with `POST /customers`)
- **What happens after Save:** the "New customer" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Status, Name, Contact person, Phone, Country, Tax number, Currency, Payment terms
- **Source evidence:** `ui/parties.ts:16`

### Field: Country

- **Application:** Spare Parts Shop
- **Page:** Customers -> dialog "New customer"
- **Type:** text
- **Purpose:** Country of the customer or supplier.
- **What user enters:** Text.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `customers.write` (the dialog saves with `POST /customers`)
- **What happens after Save:** the "New customer" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Status, Name, Contact person, Phone, Email, Tax number, Currency, Payment terms
- **Source evidence:** `ui/parties.ts:17`

### Field: Tax number

- **Application:** Spare Parts Shop
- **Page:** Customers -> dialog "New customer"
- **Type:** text
- **Purpose:** Tax / VAT number of the customer or supplier.
- **What user enters:** Text.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `customers.write` (the dialog saves with `POST /customers`)
- **What happens after Save:** the "New customer" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Status, Name, Contact person, Phone, Email, Country, Currency, Payment terms
- **Source evidence:** `ui/parties.ts:18`

### Field: Currency

- **Application:** Spare Parts Shop
- **Page:** Customers -> dialog "New customer"
- **Type:** text
- **Purpose:** 3-letter currency code (for example AED) used for prices and documents.
- **What user enters:** Text. Hint shown: "3-letter code, e.g. AED".
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `customers.write` (the dialog saves with `POST /customers`)
- **What happens after Save:** the "New customer" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Status, Name, Contact person, Phone, Email, Country, Tax number, Payment terms
- **Source evidence:** `ui/parties.ts:19`

### Field: Payment terms

- **Application:** Spare Parts Shop
- **Page:** Customers -> dialog "New customer"
- **Type:** text
- **Purpose:** Agreed payment terms text (for example '30 days').
- **What user enters:** Text.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `customers.write` (the dialog saves with `POST /customers`)
- **What happens after Save:** the "New customer" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Status, Name, Contact person, Phone, Email, Country, Tax number, Currency
- **Source evidence:** `ui/parties.ts:20`

### Field: Notes

- **Application:** Spare Parts Shop
- **Page:** Customers -> dialog "New customer"
- **Type:** textarea
- **Purpose:** Free notes about the record.
- **What user enters:** Free text (several lines allowed).
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `customers.write` (the dialog saves with `POST /customers`)
- **What happens after Save:** the "New customer" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Status, Name, Contact person, Phone, Email, Country, Tax number, Currency
- **Source evidence:** `ui/parties.ts:22`

### Field: Billing address

- **Application:** Spare Parts Shop
- **Page:** Customers -> dialog "New customer"
- **Type:** textarea
- **Purpose:** Address printed on invoices to this customer.
- **What user enters:** Free text (several lines allowed).
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `customers.write` (the dialog saves with `POST /customers`)
- **What happens after Save:** the "New customer" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Status, Name, Contact person, Phone, Email, Country, Tax number, Currency
- **Source evidence:** `ui/parties.ts:26`

### Field: Shipping address

- **Application:** Spare Parts Shop
- **Page:** Customers -> dialog "New customer"
- **Type:** textarea
- **Purpose:** Address goods are delivered to.
- **What user enters:** Free text (several lines allowed).
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `customers.write` (the dialog saves with `POST /customers`)
- **What happens after Save:** the "New customer" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Status, Name, Contact person, Phone, Email, Country, Tax number, Currency
- **Source evidence:** `ui/parties.ts:27`

### Field: Credit limit

- **Application:** Spare Parts Shop
- **Page:** Customers -> dialog "New customer"
- **Type:** money
- **Purpose:** Maximum amount this customer may owe (stored with the customer; optional).
- **What user enters:** An amount, for example 125.00.
- **Required:** No (left out when empty)
- **Validation:** amount (money); server rules: see top of this document
- **Permission:** `customers.write` (the dialog saves with `POST /customers`)
- **What happens after Save:** the "New customer" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Status, Name, Contact person, Phone, Email, Country, Tax number, Currency
- **Source evidence:** `ui/parties.ts:28`

## Page: Customer (`/customers/[id]`)

### Field: Status

- **Application:** Spare Parts Shop
- **Page:** Customer -> dialog "Edit customer"
- **Type:** select (options: Active, Inactive)
- **Purpose:** Active or Inactive. Inactive records stay in history but are not offered for new documents.
- **What user enters:** Choose one option: Active, Inactive.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `customers.write` (the dialog saves with `PATCH /customers/:id`)
- **What happens after Save:** the "Edit customer" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Name, Contact person, Phone, Email, Country, Tax number, Currency, Payment terms
- **Source evidence:** `ui/parties.ts:3`

### Field: Name

- **Application:** Spare Parts Shop
- **Page:** Customer -> dialog "Edit customer"
- **Type:** text
- **Purpose:** The name of the record (customer, supplier, warehouse, product...).
- **What user enters:** Text.
- **Required:** Yes
- **Validation:** required by the form; server rules: see top of this document
- **Permission:** `customers.write` (the dialog saves with `PATCH /customers/:id`)
- **What happens after Save:** the "Edit customer" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Status, Contact person, Phone, Email, Country, Tax number, Currency, Payment terms
- **Source evidence:** `ui/parties.ts:13`

### Field: Contact person

- **Application:** Spare Parts Shop
- **Page:** Customer -> dialog "Edit customer"
- **Type:** text
- **Purpose:** The person to talk to at this customer or supplier.
- **What user enters:** Text.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `customers.write` (the dialog saves with `PATCH /customers/:id`)
- **What happens after Save:** the "Edit customer" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Status, Name, Phone, Email, Country, Tax number, Currency, Payment terms
- **Source evidence:** `ui/parties.ts:14`

### Field: Phone

- **Application:** Spare Parts Shop
- **Page:** Customer -> dialog "Edit customer"
- **Type:** text
- **Purpose:** Telephone number of the person or company.
- **What user enters:** Text.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `customers.write` (the dialog saves with `PATCH /customers/:id`)
- **What happens after Save:** the "Edit customer" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Status, Name, Contact person, Email, Country, Tax number, Currency, Payment terms
- **Source evidence:** `ui/parties.ts:15`

### Field: Email

- **Application:** Spare Parts Shop
- **Page:** Customer -> dialog "Edit customer"
- **Type:** email
- **Purpose:** Email address of the person or company.
- **What user enters:** An email address.
- **Required:** No (form does not require it)
- **Validation:** must be an email address; server rules: see top of this document
- **Permission:** `customers.write` (the dialog saves with `PATCH /customers/:id`)
- **What happens after Save:** the "Edit customer" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Status, Name, Contact person, Phone, Country, Tax number, Currency, Payment terms
- **Source evidence:** `ui/parties.ts:16`

### Field: Country

- **Application:** Spare Parts Shop
- **Page:** Customer -> dialog "Edit customer"
- **Type:** text
- **Purpose:** Country of the customer or supplier.
- **What user enters:** Text.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `customers.write` (the dialog saves with `PATCH /customers/:id`)
- **What happens after Save:** the "Edit customer" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Status, Name, Contact person, Phone, Email, Tax number, Currency, Payment terms
- **Source evidence:** `ui/parties.ts:17`

### Field: Tax number

- **Application:** Spare Parts Shop
- **Page:** Customer -> dialog "Edit customer"
- **Type:** text
- **Purpose:** Tax / VAT number of the customer or supplier.
- **What user enters:** Text.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `customers.write` (the dialog saves with `PATCH /customers/:id`)
- **What happens after Save:** the "Edit customer" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Status, Name, Contact person, Phone, Email, Country, Currency, Payment terms
- **Source evidence:** `ui/parties.ts:18`

### Field: Currency

- **Application:** Spare Parts Shop
- **Page:** Customer -> dialog "Edit customer"
- **Type:** text
- **Purpose:** 3-letter currency code (for example AED) used for prices and documents.
- **What user enters:** Text. Hint shown: "3-letter code, e.g. AED".
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `customers.write` (the dialog saves with `PATCH /customers/:id`)
- **What happens after Save:** the "Edit customer" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Status, Name, Contact person, Phone, Email, Country, Tax number, Payment terms
- **Source evidence:** `ui/parties.ts:19`

### Field: Payment terms

- **Application:** Spare Parts Shop
- **Page:** Customer -> dialog "Edit customer"
- **Type:** text
- **Purpose:** Agreed payment terms text (for example '30 days').
- **What user enters:** Text.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `customers.write` (the dialog saves with `PATCH /customers/:id`)
- **What happens after Save:** the "Edit customer" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Status, Name, Contact person, Phone, Email, Country, Tax number, Currency
- **Source evidence:** `ui/parties.ts:20`

### Field: Notes

- **Application:** Spare Parts Shop
- **Page:** Customer -> dialog "Edit customer"
- **Type:** textarea
- **Purpose:** Free notes about the record.
- **What user enters:** Free text (several lines allowed).
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `customers.write` (the dialog saves with `PATCH /customers/:id`)
- **What happens after Save:** the "Edit customer" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Status, Name, Contact person, Phone, Email, Country, Tax number, Currency
- **Source evidence:** `ui/parties.ts:22`

### Field: Billing address

- **Application:** Spare Parts Shop
- **Page:** Customer -> dialog "Edit customer"
- **Type:** textarea
- **Purpose:** Address printed on invoices to this customer.
- **What user enters:** Free text (several lines allowed).
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `customers.write` (the dialog saves with `PATCH /customers/:id`)
- **What happens after Save:** the "Edit customer" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Status, Name, Contact person, Phone, Email, Country, Tax number, Currency
- **Source evidence:** `ui/parties.ts:26`

### Field: Shipping address

- **Application:** Spare Parts Shop
- **Page:** Customer -> dialog "Edit customer"
- **Type:** textarea
- **Purpose:** Address goods are delivered to.
- **What user enters:** Free text (several lines allowed).
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `customers.write` (the dialog saves with `PATCH /customers/:id`)
- **What happens after Save:** the "Edit customer" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Status, Name, Contact person, Phone, Email, Country, Tax number, Currency
- **Source evidence:** `ui/parties.ts:27`

### Field: Credit limit

- **Application:** Spare Parts Shop
- **Page:** Customer -> dialog "Edit customer"
- **Type:** money
- **Purpose:** Maximum amount this customer may owe (stored with the customer; optional).
- **What user enters:** An amount, for example 125.00.
- **Required:** No (left out when empty)
- **Validation:** amount (money); server rules: see top of this document
- **Permission:** `customers.write` (the dialog saves with `PATCH /customers/:id`)
- **What happens after Save:** the "Edit customer" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Status, Name, Contact person, Phone, Email, Country, Tax number, Currency
- **Source evidence:** `ui/parties.ts:28`

## Page: Enquiry (`/enquiries/[id]`)

### Field: Customer

- **Application:** Spare Parts Shop
- **Page:** Enquiry -> dialog "Create quotation"
- **Type:** select (options: Choose a customer…)
- **Purpose:** The customer the document is for.
- **What user enters:** Choose one option: Choose a customer….
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `quotations.write` (the dialog saves with `POST /enquiries/:id/quotation`)
- **What happens after Save:** the "Create quotation" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Source evidence:** `app/(app)/enquiries/[id]/page.tsx:148`

## Page: Enquiry cart (`/enquiries/cart`)

### Field: Existing customer (optional)

- **Application:** Spare Parts Shop
- **Page:** Enquiry cart
- **Type:** select (options: — not linked to a customer —)
- **Purpose:** Link the enquiry to a customer already in the system; otherwise enter a contact name.
- **What user enters:** Choose one option: — not linked to a customer —.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `enquiries.write` (every save on this page needs it: `DELETE /enquiries/:id/items/:itemId`, `POST /enquiries/:id/submit`)
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** Contact name, Email, Phone, VIN / chassis number, Notes
- **Source evidence:** `app/(app)/enquiries/cart/page.tsx:125`

### Field: Contact name

- **Application:** Spare Parts Shop
- **Page:** Enquiry cart
- **Type:** text
- **Purpose:** Name of the person asking, when no existing customer is chosen.
- **What user enters:** Text.
- **Required:** Yes
- **Validation:** required by the form; server rules: see top of this document
- **Permission:** `enquiries.write` (every save on this page needs it: `DELETE /enquiries/:id/items/:itemId`, `POST /enquiries/:id/submit`)
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** Existing customer (optional), Email, Phone, VIN / chassis number, Notes
- **Source evidence:** `app/(app)/enquiries/cart/page.tsx:135`

### Field: Email

- **Application:** Spare Parts Shop
- **Page:** Enquiry cart
- **Type:** email
- **Purpose:** Email address of the person or company.
- **What user enters:** An email address.
- **Required:** No (form does not require it)
- **Validation:** must be an email address; server rules: see top of this document
- **Permission:** `enquiries.write` (every save on this page needs it: `DELETE /enquiries/:id/items/:itemId`, `POST /enquiries/:id/submit`)
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** Existing customer (optional), Contact name, Phone, VIN / chassis number, Notes
- **Source evidence:** `app/(app)/enquiries/cart/page.tsx:142`

### Field: Phone

- **Application:** Spare Parts Shop
- **Page:** Enquiry cart
- **Type:** text
- **Purpose:** Telephone number of the person or company.
- **What user enters:** Text.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `enquiries.write` (every save on this page needs it: `DELETE /enquiries/:id/items/:itemId`, `POST /enquiries/:id/submit`)
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** Existing customer (optional), Contact name, Email, VIN / chassis number, Notes
- **Source evidence:** `app/(app)/enquiries/cart/page.tsx:149`

### Field: VIN / chassis number

- **Application:** Spare Parts Shop
- **Page:** Enquiry cart
- **Type:** text
- **Purpose:** Vehicle identification / chassis number the parts are for (helps fitment).
- **What user enters:** Text.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `enquiries.write` (every save on this page needs it: `DELETE /enquiries/:id/items/:itemId`, `POST /enquiries/:id/submit`)
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** Existing customer (optional), Contact name, Email, Phone, Notes
- **Source evidence:** `app/(app)/enquiries/cart/page.tsx:155`

### Field: Notes

- **Application:** Spare Parts Shop
- **Page:** Enquiry cart
- **Type:** textarea
- **Purpose:** Free notes about the record.
- **What user enters:** Free text (several lines allowed).
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `enquiries.write` (every save on this page needs it: `DELETE /enquiries/:id/items/:itemId`, `POST /enquiries/:id/submit`)
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** Existing customer (optional), Contact name, Email, Phone, VIN / chassis number
- **Source evidence:** `app/(app)/enquiries/cart/page.tsx:158`

## Page: Stock & Locations (`/inventory`)

### Field: Name

- **Application:** Spare Parts Shop
- **Page:** Stock & Locations -> dialog "New warehouse"
- **Type:** text
- **Purpose:** The name of the record (customer, supplier, warehouse, product...).
- **What user enters:** Text.
- **Required:** Yes
- **Validation:** required by the form; server rules: see top of this document
- **Permission:** `warehouses.write` (the dialog saves with `POST /warehouses`)
- **What happens after Save:** the "New warehouse" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Address
- **Source evidence:** `app/(app)/inventory/page.tsx:230`

### Field: Address

- **Application:** Spare Parts Shop
- **Page:** Stock & Locations -> dialog "New warehouse"
- **Type:** textarea
- **Purpose:** Postal / street address.
- **What user enters:** Free text (several lines allowed).
- **Required:** No (left out when empty)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `warehouses.write` (the dialog saves with `POST /warehouses`)
- **What happens after Save:** the "New warehouse" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Name
- **Source evidence:** `app/(app)/inventory/page.tsx:231`

### Field: Name

- **Application:** Spare Parts Shop
- **Page:** Stock & Locations -> dialog "Edit warehouse"
- **Type:** text
- **Purpose:** The name of the record (customer, supplier, warehouse, product...).
- **What user enters:** Text.
- **Required:** Yes
- **Validation:** required by the form; server rules: see top of this document
- **Permission:** `warehouses.write` (the dialog saves with `PATCH /warehouses/:id`)
- **What happens after Save:** the "Edit warehouse" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Address, Status
- **Source evidence:** `app/(app)/inventory/page.tsx:247`

### Field: Address

- **Application:** Spare Parts Shop
- **Page:** Stock & Locations -> dialog "Edit warehouse"
- **Type:** textarea
- **Purpose:** Postal / street address.
- **What user enters:** Free text (several lines allowed).
- **Required:** No (left out when empty)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `warehouses.write` (the dialog saves with `PATCH /warehouses/:id`)
- **What happens after Save:** the "Edit warehouse" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Name, Status
- **Source evidence:** `app/(app)/inventory/page.tsx:248`

### Field: Status

- **Application:** Spare Parts Shop
- **Page:** Stock & Locations -> dialog "Edit warehouse"
- **Type:** select (options: Active, Inactive)
- **Purpose:** Active or Inactive. Inactive records stay in history but are not offered for new documents.
- **What user enters:** Choose one option: Active, Inactive.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `warehouses.write` (the dialog saves with `PATCH /warehouses/:id`)
- **What happens after Save:** the "Edit warehouse" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Name, Address
- **Source evidence:** `app/(app)/inventory/page.tsx:254`

### Field: Rack

- **Application:** Spare Parts Shop
- **Page:** Stock & Locations -> dialog "Add rack / shelf / bin"
- **Type:** text
- **Purpose:** Rack identifier inside a warehouse.
- **What user enters:** Text.
- **Required:** No (left out when empty)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `warehouses.write` (the dialog saves with `POST /warehouses/:id/locations`)
- **What happens after Save:** the "Add rack / shelf / bin" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Shelf, Bin, Description
- **Source evidence:** `app/(app)/inventory/page.tsx:275`

### Field: Shelf

- **Application:** Spare Parts Shop
- **Page:** Stock & Locations -> dialog "Add rack / shelf / bin"
- **Type:** text
- **Purpose:** Shelf on the rack.
- **What user enters:** Text.
- **Required:** No (left out when empty)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `warehouses.write` (the dialog saves with `POST /warehouses/:id/locations`)
- **What happens after Save:** the "Add rack / shelf / bin" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Rack, Bin, Description
- **Source evidence:** `app/(app)/inventory/page.tsx:276`

### Field: Bin

- **Application:** Spare Parts Shop
- **Page:** Stock & Locations -> dialog "Add rack / shelf / bin"
- **Type:** text
- **Purpose:** Bin / box on the shelf.
- **What user enters:** Text.
- **Required:** No (left out when empty)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `warehouses.write` (the dialog saves with `POST /warehouses/:id/locations`)
- **What happens after Save:** the "Add rack / shelf / bin" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Rack, Shelf, Description
- **Source evidence:** `app/(app)/inventory/page.tsx:277`

### Field: Description

- **Application:** Spare Parts Shop
- **Page:** Stock & Locations -> dialog "Add rack / shelf / bin"
- **Type:** text
- **Purpose:** Longer description.
- **What user enters:** Text.
- **Required:** No (left out when empty)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `warehouses.write` (the dialog saves with `POST /warehouses/:id/locations`)
- **What happens after Save:** the "Add rack / shelf / bin" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Rack, Shelf, Bin
- **Source evidence:** `app/(app)/inventory/page.tsx:278`

### Field: Location

- **Application:** Spare Parts Shop
- **Page:** Stock & Locations -> dialog "Receive stock — …"
- **Type:** select
- **Purpose:** A place in a warehouse (rack / shelf / bin) where stock is kept.
- **What user enters:** Choose one option.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `inventory.write` (the dialog saves with `POST /inventory/receive`)
- **What happens after Save:** the "Receive stock — …" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Quantity received, Note (delivery note, source)
- **Source evidence:** `ui/stock.tsx:59`

### Field: Quantity received

- **Application:** Spare Parts Shop
- **Page:** Stock & Locations -> dialog "Receive stock — …"
- **Type:** number
- **Purpose:** How many units arrived. Stock on hand increases by this amount.
- **What user enters:** A whole number.
- **Required:** Yes
- **Validation:** required by the form; number; server rules: see top of this document
- **Permission:** `inventory.write` (the dialog saves with `POST /inventory/receive`)
- **What happens after Save:** the "Receive stock — …" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Location, Note (delivery note, source)
- **Source evidence:** `ui/stock.tsx:65`

### Field: Note (delivery note, source)

- **Application:** Spare Parts Shop
- **Page:** Stock & Locations -> dialog "Receive stock — …"
- **Type:** text
- **Purpose:** Reference for the receipt, for example the supplier's delivery note number.
- **What user enters:** Text.
- **Required:** No (left out when empty)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `inventory.write` (the dialog saves with `POST /inventory/receive`)
- **What happens after Save:** the "Receive stock — …" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Location, Quantity received
- **Source evidence:** `ui/stock.tsx:71`

### Field: Location

- **Application:** Spare Parts Shop
- **Page:** Stock & Locations -> dialog "Adjust stock — …"
- **Type:** select
- **Purpose:** A place in a warehouse (rack / shelf / bin) where stock is kept.
- **What user enters:** Choose one option.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `inventory.write` (the dialog saves with `POST /inventory/adjust`)
- **What happens after Save:** the "Adjust stock — …" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Change in quantity, Reason
- **Source evidence:** `ui/stock.tsx:91`

### Field: Change in quantity

- **Application:** Spare Parts Shop
- **Page:** Stock & Locations -> dialog "Adjust stock — …"
- **Type:** number
- **Purpose:** How much to add (positive) or remove (negative). Must be a non-zero whole number.
- **What user enters:** A whole number. Hint shown: "Use a negative number to remove stock, e.g. -2 for damaged goods.".
- **Required:** Yes
- **Validation:** required by the form; number; server rules: see top of this document
- **Permission:** `inventory.write` (the dialog saves with `POST /inventory/adjust`)
- **What happens after Save:** the "Adjust stock — …" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Location, Reason
- **Source evidence:** `ui/stock.tsx:97`

### Field: Reason

- **Application:** Spare Parts Shop
- **Page:** Stock & Locations -> dialog "Adjust stock — …"
- **Type:** textarea
- **Purpose:** Why stock is adjusted. Required -- every adjustment must be explained.
- **What user enters:** Free text (several lines allowed).
- **Required:** Yes
- **Validation:** required by the form; server rules: see top of this document
- **Permission:** `inventory.write` (the dialog saves with `POST /inventory/adjust`)
- **What happens after Save:** the "Adjust stock — …" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Location, Change in quantity
- **Source evidence:** `ui/stock.tsx:104`

### Field: From

- **Application:** Spare Parts Shop
- **Page:** Stock & Locations -> dialog "Transfer stock — …"
- **Type:** select
- **Purpose:** Where stock moves from (transfer) / start of a period (reports).
- **What user enters:** Choose one option.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `inventory.write` (the dialog saves with `POST /inventory/transfer`)
- **What happens after Save:** the "Transfer stock — …" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** To, Quantity, Note
- **Source evidence:** `ui/stock.tsx:125`

### Field: To

- **Application:** Spare Parts Shop
- **Page:** Stock & Locations -> dialog "Transfer stock — …"
- **Type:** select
- **Purpose:** Where stock moves to (transfer) / end of a period (reports).
- **What user enters:** Choose one option.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `inventory.write` (the dialog saves with `POST /inventory/transfer`)
- **What happens after Save:** the "Transfer stock — …" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** From, Quantity, Note
- **Source evidence:** `ui/stock.tsx:126`

### Field: Quantity

- **Application:** Spare Parts Shop
- **Page:** Stock & Locations -> dialog "Transfer stock — …"
- **Type:** number
- **Purpose:** Number of units.
- **What user enters:** A whole number.
- **Required:** Yes
- **Validation:** required by the form; number; server rules: see top of this document
- **Permission:** `inventory.write` (the dialog saves with `POST /inventory/transfer`)
- **What happens after Save:** the "Transfer stock — …" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** From, To, Note
- **Source evidence:** `ui/stock.tsx:127`

### Field: Note

- **Application:** Spare Parts Shop
- **Page:** Stock & Locations -> dialog "Transfer stock — …"
- **Type:** text
- **Purpose:** Free note recorded with the movement or document.
- **What user enters:** Text.
- **Required:** No (left out when empty)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `inventory.write` (the dialog saves with `POST /inventory/transfer`)
- **What happens after Save:** the "Transfer stock — …" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** From, To, Quantity
- **Source evidence:** `ui/stock.tsx:128`

## Page: Invoices & Payments (`/invoices`)

### Field: Unpaid only

- **Application:** Spare Parts Shop
- **Page:** Invoices & Payments
- **Type:** checkbox
- **Purpose:** Invoice filter: show only invoices with a balance.
- **What user enters:** Tick to switch on.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** NOT CONFIRMED for this field; the page's write calls are none (this control only filters or looks up; nothing is saved)
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Source evidence:** `app/(app)/invoices/page.tsx:30`

## Page: Invoice (`/invoices/[id]`)

### Field: Method

- **Application:** Spare Parts Shop
- **Page:** Invoice -> dialog "Record payment"
- **Type:** select (options: Cash, Bank transfer, Card, Other)
- **Purpose:** How the payment was made (for example cash, card, bank transfer).
- **What user enters:** Choose one option: Cash, Bank transfer, Card, Other.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `payments.record` (the dialog saves with `POST /invoices/:id/payments`)
- **What happens after Save:** the "Record payment" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Reference (receipt / transfer no.), Notes
- **Source evidence:** `app/(app)/invoices/[id]/page.tsx:184`

### Field: Reference (receipt / transfer no.)

- **Application:** Spare Parts Shop
- **Page:** Invoice -> dialog "Record payment"
- **Type:** text
- **Purpose:** Your reference number for the receipt or transfer.
- **What user enters:** Text.
- **Required:** No (left out when empty)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `payments.record` (the dialog saves with `POST /invoices/:id/payments`)
- **What happens after Save:** the "Record payment" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Method, Notes
- **Source evidence:** `app/(app)/invoices/[id]/page.tsx:193`

### Field: Notes

- **Application:** Spare Parts Shop
- **Page:** Invoice -> dialog "Record payment"
- **Type:** textarea
- **Purpose:** Free notes about the record.
- **What user enters:** Free text (several lines allowed).
- **Required:** No (left out when empty)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `payments.record` (the dialog saves with `POST /invoices/:id/payments`)
- **What happens after Save:** the "Record payment" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Method, Reference (receipt / transfer no.)
- **Source evidence:** `app/(app)/invoices/[id]/page.tsx:198`

### Field: Reason

- **Application:** Spare Parts Shop
- **Page:** Invoice -> dialog "Void invoice"
- **Type:** textarea
- **Purpose:** Why stock is adjusted. Required -- every adjustment must be explained.
- **What user enters:** Free text (several lines allowed). Hint shown: "The delivered goods become billable again on the order.".
- **Required:** Yes
- **Validation:** required by the form; server rules: see top of this document
- **Permission:** `invoices.write` (the dialog saves with `POST /invoices/:id/void`)
- **What happens after Save:** the "Void invoice" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Source evidence:** `app/(app)/invoices/[id]/page.tsx:212`

## Page: Sales order (`/orders/[id]`)

### Field: Item

- **Application:** Spare Parts Shop
- **Page:** Sales order -> dialog "Record return"
- **Type:** select
- **Purpose:** A line of the document: a product or a free-text line.
- **What user enters:** Choose one option.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `orders.write` (the dialog saves with `POST /orders/:id/return`)
- **What happens after Save:** the "Record return" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Quantity returned, Return to location, Reason
- **Source evidence:** `app/(app)/orders/[id]/page.tsx:265`

### Field: Quantity returned

- **Application:** Spare Parts Shop
- **Page:** Sales order -> dialog "Record return"
- **Type:** number
- **Purpose:** How many units the customer returned.
- **What user enters:** A whole number.
- **Required:** Yes
- **Validation:** required by the form; number; server rules: see top of this document
- **Permission:** `orders.write` (the dialog saves with `POST /orders/:id/return`)
- **What happens after Save:** the "Record return" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Item, Return to location, Reason
- **Source evidence:** `app/(app)/orders/[id]/page.tsx:279`

### Field: Return to location

- **Application:** Spare Parts Shop
- **Page:** Sales order -> dialog "Record return"
- **Type:** select
- **Purpose:** Where returned goods are put back into stock.
- **What user enters:** Choose one option.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `orders.write` (the dialog saves with `POST /orders/:id/return`)
- **What happens after Save:** the "Record return" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Item, Quantity returned, Reason
- **Source evidence:** `app/(app)/orders/[id]/page.tsx:285`

### Field: Reason

- **Application:** Spare Parts Shop
- **Page:** Sales order -> dialog "Record return"
- **Type:** textarea
- **Purpose:** Why stock is adjusted. Required -- every adjustment must be explained.
- **What user enters:** Free text (several lines allowed).
- **Required:** Yes
- **Validation:** required by the form; server rules: see top of this document
- **Permission:** `orders.write` (the dialog saves with `POST /orders/:id/return`)
- **What happens after Save:** the "Record return" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Item, Quantity returned, Return to location
- **Source evidence:** `app/(app)/orders/[id]/page.tsx:291`

## Page: My Products (`/products`)

### Field: Low stock only

- **Application:** Spare Parts Shop
- **Page:** My Products
- **Type:** checkbox
- **Purpose:** Filter: show only products at or below their reorder level.
- **What user enters:** Tick to switch on.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** NOT CONFIRMED for this field; the page's write calls are `POST /products` -> `products.write`, `POST /inventory/receive` -> `inventory.write`, `POST /inventory/adjust` -> `inventory.write`, `POST /inventory/transfer` -> `inventory.write`
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Source evidence:** `app/(app)/products/page.tsx:62`

### Field: Location

- **Application:** Spare Parts Shop
- **Page:** My Products -> dialog "Receive stock — …"
- **Type:** select
- **Purpose:** A place in a warehouse (rack / shelf / bin) where stock is kept.
- **What user enters:** Choose one option.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `inventory.write` (the dialog saves with `POST /inventory/receive`)
- **What happens after Save:** the "Receive stock — …" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Quantity received, Note (delivery note, source)
- **Source evidence:** `ui/stock.tsx:59`

### Field: Quantity received

- **Application:** Spare Parts Shop
- **Page:** My Products -> dialog "Receive stock — …"
- **Type:** number
- **Purpose:** How many units arrived. Stock on hand increases by this amount.
- **What user enters:** A whole number.
- **Required:** Yes
- **Validation:** required by the form; number; server rules: see top of this document
- **Permission:** `inventory.write` (the dialog saves with `POST /inventory/receive`)
- **What happens after Save:** the "Receive stock — …" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Location, Note (delivery note, source)
- **Source evidence:** `ui/stock.tsx:65`

### Field: Note (delivery note, source)

- **Application:** Spare Parts Shop
- **Page:** My Products -> dialog "Receive stock — …"
- **Type:** text
- **Purpose:** Reference for the receipt, for example the supplier's delivery note number.
- **What user enters:** Text.
- **Required:** No (left out when empty)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `inventory.write` (the dialog saves with `POST /inventory/receive`)
- **What happens after Save:** the "Receive stock — …" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Location, Quantity received
- **Source evidence:** `ui/stock.tsx:71`

### Field: Location

- **Application:** Spare Parts Shop
- **Page:** My Products -> dialog "Adjust stock — …"
- **Type:** select
- **Purpose:** A place in a warehouse (rack / shelf / bin) where stock is kept.
- **What user enters:** Choose one option.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `inventory.write` (the dialog saves with `POST /inventory/adjust`)
- **What happens after Save:** the "Adjust stock — …" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Change in quantity, Reason
- **Source evidence:** `ui/stock.tsx:91`

### Field: Change in quantity

- **Application:** Spare Parts Shop
- **Page:** My Products -> dialog "Adjust stock — …"
- **Type:** number
- **Purpose:** How much to add (positive) or remove (negative). Must be a non-zero whole number.
- **What user enters:** A whole number. Hint shown: "Use a negative number to remove stock, e.g. -2 for damaged goods.".
- **Required:** Yes
- **Validation:** required by the form; number; server rules: see top of this document
- **Permission:** `inventory.write` (the dialog saves with `POST /inventory/adjust`)
- **What happens after Save:** the "Adjust stock — …" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Location, Reason
- **Source evidence:** `ui/stock.tsx:97`

### Field: Reason

- **Application:** Spare Parts Shop
- **Page:** My Products -> dialog "Adjust stock — …"
- **Type:** textarea
- **Purpose:** Why stock is adjusted. Required -- every adjustment must be explained.
- **What user enters:** Free text (several lines allowed).
- **Required:** Yes
- **Validation:** required by the form; server rules: see top of this document
- **Permission:** `inventory.write` (the dialog saves with `POST /inventory/adjust`)
- **What happens after Save:** the "Adjust stock — …" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Location, Change in quantity
- **Source evidence:** `ui/stock.tsx:104`

### Field: From

- **Application:** Spare Parts Shop
- **Page:** My Products -> dialog "Transfer stock — …"
- **Type:** select
- **Purpose:** Where stock moves from (transfer) / start of a period (reports).
- **What user enters:** Choose one option.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `inventory.write` (the dialog saves with `POST /inventory/transfer`)
- **What happens after Save:** the "Transfer stock — …" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** To, Quantity, Note
- **Source evidence:** `ui/stock.tsx:125`

### Field: To

- **Application:** Spare Parts Shop
- **Page:** My Products -> dialog "Transfer stock — …"
- **Type:** select
- **Purpose:** Where stock moves to (transfer) / end of a period (reports).
- **What user enters:** Choose one option.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `inventory.write` (the dialog saves with `POST /inventory/transfer`)
- **What happens after Save:** the "Transfer stock — …" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** From, Quantity, Note
- **Source evidence:** `ui/stock.tsx:126`

### Field: Quantity

- **Application:** Spare Parts Shop
- **Page:** My Products -> dialog "Transfer stock — …"
- **Type:** number
- **Purpose:** Number of units.
- **What user enters:** A whole number.
- **Required:** Yes
- **Validation:** required by the form; number; server rules: see top of this document
- **Permission:** `inventory.write` (the dialog saves with `POST /inventory/transfer`)
- **What happens after Save:** the "Transfer stock — …" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** From, To, Note
- **Source evidence:** `ui/stock.tsx:127`

### Field: Note

- **Application:** Spare Parts Shop
- **Page:** My Products -> dialog "Transfer stock — …"
- **Type:** text
- **Purpose:** Free note recorded with the movement or document.
- **What user enters:** Text.
- **Required:** No (left out when empty)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `inventory.write` (the dialog saves with `POST /inventory/transfer`)
- **What happens after Save:** the "Transfer stock — …" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** From, To, Quantity
- **Source evidence:** `ui/stock.tsx:128`

### Field: SKU (your own code)

- **Application:** Spare Parts Shop
- **Page:** My Products -> dialog "New product"
- **Type:** text
- **Purpose:** The shop's own unique product code. Must be unique; it cannot be removed later.
- **What user enters:** Text.
- **Required:** Yes
- **Validation:** required by the form; server rules: see top of this document
- **Permission:** `products.write` (the dialog saves with `POST /products`)
- **What happens after Save:** the "New product" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Name, Brand, Manufacturer, Category, Condition, Selling price, Cost price, Reorder level
- **Source evidence:** `ui/productForm.ts:10`

### Field: Name

- **Application:** Spare Parts Shop
- **Page:** My Products -> dialog "New product"
- **Type:** text
- **Purpose:** The name of the record (customer, supplier, warehouse, product...).
- **What user enters:** Text.
- **Required:** Yes
- **Validation:** required by the form; server rules: see top of this document
- **Permission:** `products.write` (the dialog saves with `POST /products`)
- **What happens after Save:** the "New product" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** SKU (your own code), Brand, Manufacturer, Category, Condition, Selling price, Cost price, Reorder level
- **Source evidence:** `ui/productForm.ts:11`

### Field: Brand

- **Application:** Spare Parts Shop
- **Page:** My Products -> dialog "New product"
- **Type:** text
- **Purpose:** Brand of the product (for example the maker of an aftermarket part).
- **What user enters:** Text.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `products.write` (the dialog saves with `POST /products`)
- **What happens after Save:** the "New product" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** SKU (your own code), Name, Manufacturer, Category, Condition, Selling price, Cost price, Reorder level
- **Source evidence:** `ui/productForm.ts:12`

### Field: Manufacturer

- **Application:** Spare Parts Shop
- **Page:** My Products -> dialog "New product"
- **Type:** text
- **Purpose:** Manufacturer of the part.
- **What user enters:** Text.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `products.write` (the dialog saves with `POST /products`)
- **What happens after Save:** the "New product" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** SKU (your own code), Name, Brand, Category, Condition, Selling price, Cost price, Reorder level
- **Source evidence:** `ui/productForm.ts:13`

### Field: Category

- **Application:** Spare Parts Shop
- **Page:** My Products -> dialog "New product"
- **Type:** text
- **Purpose:** Product group used for filtering and reports.
- **What user enters:** Text.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `products.write` (the dialog saves with `POST /products`)
- **What happens after Save:** the "New product" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** SKU (your own code), Name, Brand, Manufacturer, Condition, Selling price, Cost price, Reorder level
- **Source evidence:** `ui/productForm.ts:14`

### Field: Condition

- **Application:** Spare Parts Shop
- **Page:** My Products -> dialog "New product"
- **Type:** select (options: New, Used, Remanufactured, Other)
- **Purpose:** Condition of the part: New, Used, Remanufactured or Other.
- **What user enters:** Choose one option: New, Used, Remanufactured, Other.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `products.write` (the dialog saves with `POST /products`)
- **What happens after Save:** the "New product" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** SKU (your own code), Name, Brand, Manufacturer, Category, Selling price, Cost price, Reorder level
- **Source evidence:** `ui/productForm.ts:15`

### Field: Selling price

- **Application:** Spare Parts Shop
- **Page:** My Products -> dialog "New product"
- **Type:** money
- **Purpose:** The price the shop charges the customer. Used to price quotation lines automatically.
- **What user enters:** An amount, for example 125.00.
- **Required:** No (form does not require it)
- **Validation:** amount (money); server rules: see top of this document
- **Permission:** `products.write` (the dialog saves with `POST /products`)
- **What happens after Save:** the "New product" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** SKU (your own code), Name, Brand, Manufacturer, Category, Condition, Cost price, Reorder level
- **Source evidence:** `ui/productForm.ts:24`

### Field: Cost price

- **Application:** Spare Parts Shop
- **Page:** My Products -> dialog "New product"
- **Type:** money
- **Purpose:** What the shop pays for the part. Only visible and editable with the cost permission (products.cost.read); used for stock value.
- **What user enters:** An amount, for example 125.00.
- **Required:** No (form does not require it)
- **Validation:** amount (money); server rules: see top of this document
- **Permission:** `products.write` (the dialog saves with `POST /products`)
- **What happens after Save:** the "New product" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** SKU (your own code), Name, Brand, Manufacturer, Category, Condition, Selling price, Reorder level
- **Source evidence:** `ui/productForm.ts:27`

### Field: Reorder level

- **Application:** Spare Parts Shop
- **Page:** My Products -> dialog "New product"
- **Type:** number
- **Purpose:** When available stock falls to this number, the product shows as low stock / needs reordering.
- **What user enters:** A whole number. Hint shown: "Warn when available stock falls to this number.".
- **Required:** No (form does not require it)
- **Validation:** number; server rules: see top of this document
- **Permission:** `products.write` (the dialog saves with `POST /products`)
- **What happens after Save:** the "New product" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** SKU (your own code), Name, Brand, Manufacturer, Category, Condition, Selling price, Cost price
- **Source evidence:** `ui/productForm.ts:29`

### Field: Unit

- **Application:** Spare Parts Shop
- **Page:** My Products -> dialog "New product"
- **Type:** text
- **Purpose:** Unit of measure (for example piece).
- **What user enters:** Text. Placeholder: "Each".
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `products.write` (the dialog saves with `POST /products`)
- **What happens after Save:** the "New product" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** SKU (your own code), Name, Brand, Manufacturer, Category, Condition, Selling price, Cost price
- **Source evidence:** `ui/productForm.ts:35`

### Field: Description

- **Application:** Spare Parts Shop
- **Page:** My Products -> dialog "New product"
- **Type:** textarea
- **Purpose:** Longer description.
- **What user enters:** Free text (several lines allowed).
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `products.write` (the dialog saves with `POST /products`)
- **What happens after Save:** the "New product" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** SKU (your own code), Name, Brand, Manufacturer, Category, Condition, Selling price, Cost price
- **Source evidence:** `ui/productForm.ts:36`

### Field: Status

- **Application:** Spare Parts Shop
- **Page:** My Products -> dialog "New product"
- **Type:** select (options: Active, Inactive)
- **Purpose:** Active or Inactive. Inactive records stay in history but are not offered for new documents.
- **What user enters:** Choose one option: Active, Inactive.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `products.write` (the dialog saves with `POST /products`)
- **What happens after Save:** the "New product" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** SKU (your own code), Name, Brand, Manufacturer, Category, Condition, Selling price, Cost price
- **Source evidence:** `ui/productForm.ts:37`

### Field: Default supplier

- **Application:** Spare Parts Shop
- **Page:** My Products -> dialog "New product"
- **Type:** select (options: — none —)
- **Purpose:** The supplier usually used to buy this product.
- **What user enters:** Choose one option: — none —.
- **Required:** No (left out when empty)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `products.write` (the dialog saves with `POST /products`)
- **What happens after Save:** the "New product" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** SKU (your own code), Name, Brand, Manufacturer, Category, Condition, Selling price, Cost price
- **Source evidence:** `ui/productForm.ts:48`

### Field: Opening stock location

- **Application:** Spare Parts Shop
- **Page:** My Products -> dialog "New product"
- **Type:** select (options: — no opening stock —)
- **Purpose:** Where the opening stock is stored (warehouse location). Required when an opening quantity is entered.
- **What user enters:** Choose one option: — no opening stock —.
- **Required:** No (left out when empty)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `products.write` (the dialog saves with `POST /products`)
- **What happens after Save:** the "New product" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** SKU (your own code), Name, Brand, Manufacturer, Category, Condition, Selling price, Cost price
- **Source evidence:** `ui/productForm.ts:60`

### Field: Opening stock quantity

- **Application:** Spare Parts Shop
- **Page:** My Products -> dialog "New product"
- **Type:** number
- **Purpose:** How many are on the shelf when the product is created; recorded as an opening-balance stock movement.
- **What user enters:** A whole number.
- **Required:** No (left out when empty)
- **Validation:** number; server rules: see top of this document
- **Permission:** `products.write` (the dialog saves with `POST /products`)
- **What happens after Save:** the "New product" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** SKU (your own code), Name, Brand, Manufacturer, Category, Condition, Selling price, Cost price
- **Source evidence:** `ui/productForm.ts:70`

## Page: Product details (`/products/[id]`)

### Field: Supplier

- **Application:** Spare Parts Shop
- **Page:** Product details -> dialog "Supplier for this product"
- **Type:** select
- **Purpose:** The supplier (company you buy from).
- **What user enters:** Choose one option.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `products.write` (the dialog saves with `PUT /products/:id/suppliers`)
- **What happens after Save:** the "Supplier for this product" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Supplier's part number, Cost from this supplier, Preferred supplier
- **Source evidence:** `app/(app)/products/[id]/page.tsx:632`

### Field: Supplier's part number

- **Application:** Spare Parts Shop
- **Page:** Product details -> dialog "Supplier for this product"
- **Type:** text
- **Purpose:** The supplier's own code for this product.
- **What user enters:** Text.
- **Required:** No (left out when empty)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `products.write` (the dialog saves with `PUT /products/:id/suppliers`)
- **What happens after Save:** the "Supplier for this product" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Supplier, Cost from this supplier, Preferred supplier
- **Source evidence:** `app/(app)/products/[id]/page.tsx:638`

### Field: Cost from this supplier

- **Application:** Spare Parts Shop
- **Page:** Product details -> dialog "Supplier for this product"
- **Type:** money
- **Purpose:** Price this supplier charges; with the cost permission only.
- **What user enters:** An amount, for example 125.00.
- **Required:** No (left out when empty)
- **Validation:** amount (money); server rules: see top of this document
- **Permission:** `products.write` (the dialog saves with `PUT /products/:id/suppliers`)
- **What happens after Save:** the "Supplier for this product" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Supplier, Supplier's part number, Preferred supplier
- **Source evidence:** `app/(app)/products/[id]/page.tsx:645`

### Field: Preferred supplier

- **Application:** Spare Parts Shop
- **Page:** Product details -> dialog "Supplier for this product"
- **Type:** checkbox
- **Purpose:** Mark this supplier as the usual one for the product.
- **What user enters:** Tick to switch on.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `products.write` (the dialog saves with `PUT /products/:id/suppliers`)
- **What happens after Save:** the "Supplier for this product" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Supplier, Supplier's part number, Cost from this supplier
- **Source evidence:** `app/(app)/products/[id]/page.tsx:653`

### Field: Number

- **Application:** Spare Parts Shop
- **Page:** Product details -> dialog "Add part number"
- **Type:** text
- **Purpose:** A part number or document number.
- **What user enters:** Text.
- **Required:** Yes
- **Validation:** required by the form; server rules: see top of this document
- **Permission:** `products.write` (the dialog saves with `POST /products/:id/numbers`)
- **What happens after Save:** the "Add part number" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Type, Brand, Notes
- **Source evidence:** `app/(app)/products/[id]/page.tsx:881`

### Field: Type

- **Application:** Spare Parts Shop
- **Page:** Product details -> dialog "Add part number"
- **Type:** select (options: Oem oe, Aftermarket, Supplier, Cross reference, Replacement, Previous, Interchange, Other)
- **Purpose:** The kind of record (for example part-number type).
- **What user enters:** Choose one option: Oem oe, Aftermarket, Supplier, Cross reference, Replacement, Previous, Interchange, Other.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `products.write` (the dialog saves with `POST /products/:id/numbers`)
- **What happens after Save:** the "Add part number" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Number, Brand, Notes
- **Source evidence:** `app/(app)/products/[id]/page.tsx:882`

### Field: Brand

- **Application:** Spare Parts Shop
- **Page:** Product details -> dialog "Add part number"
- **Type:** text
- **Purpose:** Brand of the product (for example the maker of an aftermarket part).
- **What user enters:** Text.
- **Required:** No (left out when empty)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `products.write` (the dialog saves with `POST /products/:id/numbers`)
- **What happens after Save:** the "Add part number" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Number, Type, Notes
- **Source evidence:** `app/(app)/products/[id]/page.tsx:897`

### Field: Notes

- **Application:** Spare Parts Shop
- **Page:** Product details -> dialog "Add part number"
- **Type:** text
- **Purpose:** Free notes about the record.
- **What user enters:** Text.
- **Required:** No (left out when empty)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `products.write` (the dialog saves with `POST /products/:id/numbers`)
- **What happens after Save:** the "Add part number" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Number, Type, Brand
- **Source evidence:** `app/(app)/products/[id]/page.tsx:898`

### Field: Link to a reference part

- **Application:** Spare Parts Shop
- **Page:** Product details
- **Type:** text
- **Purpose:** Connect the product to a reference catalogue part.
- **What user enters:** Text.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** NOT CONFIRMED for this field; the page's write calls are `PATCH /products/:id` -> `products.write`, `PUT /products/:id/images/order` -> `products.write`, `PUT /products/:id/images/:imageId/primary` -> `products.write`, `DELETE /products/:id/images/:imageId` -> `products.write`, `DELETE /products/:id/suppliers/:linkId` -> `products.write`, `PUT /products/:id/suppliers` -> `products.write`, `DELETE /products/:id/numbers/:numberId` -> `products.write`, `DELETE /products/:id/reference-links/:linkId` -> `products.write`, `POST /products/:id/reference-links` -> `products.write`, `POST /products/:id/numbers` -> `products.write`, `POST /inventory/receive` -> `inventory.write`, `POST /inventory/adjust` -> `inventory.write`, `POST /inventory/transfer` -> `inventory.write`
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Source evidence:** `app/(app)/products/[id]/page.tsx:836`

### Field: Location

- **Application:** Spare Parts Shop
- **Page:** Product details -> dialog "Receive stock — …"
- **Type:** select
- **Purpose:** A place in a warehouse (rack / shelf / bin) where stock is kept.
- **What user enters:** Choose one option.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `inventory.write` (the dialog saves with `POST /inventory/receive`)
- **What happens after Save:** the "Receive stock — …" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Quantity received, Note (delivery note, source)
- **Source evidence:** `ui/stock.tsx:59`

### Field: Quantity received

- **Application:** Spare Parts Shop
- **Page:** Product details -> dialog "Receive stock — …"
- **Type:** number
- **Purpose:** How many units arrived. Stock on hand increases by this amount.
- **What user enters:** A whole number.
- **Required:** Yes
- **Validation:** required by the form; number; server rules: see top of this document
- **Permission:** `inventory.write` (the dialog saves with `POST /inventory/receive`)
- **What happens after Save:** the "Receive stock — …" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Location, Note (delivery note, source)
- **Source evidence:** `ui/stock.tsx:65`

### Field: Note (delivery note, source)

- **Application:** Spare Parts Shop
- **Page:** Product details -> dialog "Receive stock — …"
- **Type:** text
- **Purpose:** Reference for the receipt, for example the supplier's delivery note number.
- **What user enters:** Text.
- **Required:** No (left out when empty)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `inventory.write` (the dialog saves with `POST /inventory/receive`)
- **What happens after Save:** the "Receive stock — …" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Location, Quantity received
- **Source evidence:** `ui/stock.tsx:71`

### Field: Location

- **Application:** Spare Parts Shop
- **Page:** Product details -> dialog "Adjust stock — …"
- **Type:** select
- **Purpose:** A place in a warehouse (rack / shelf / bin) where stock is kept.
- **What user enters:** Choose one option.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `inventory.write` (the dialog saves with `POST /inventory/adjust`)
- **What happens after Save:** the "Adjust stock — …" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Change in quantity, Reason
- **Source evidence:** `ui/stock.tsx:91`

### Field: Change in quantity

- **Application:** Spare Parts Shop
- **Page:** Product details -> dialog "Adjust stock — …"
- **Type:** number
- **Purpose:** How much to add (positive) or remove (negative). Must be a non-zero whole number.
- **What user enters:** A whole number. Hint shown: "Use a negative number to remove stock, e.g. -2 for damaged goods.".
- **Required:** Yes
- **Validation:** required by the form; number; server rules: see top of this document
- **Permission:** `inventory.write` (the dialog saves with `POST /inventory/adjust`)
- **What happens after Save:** the "Adjust stock — …" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Location, Reason
- **Source evidence:** `ui/stock.tsx:97`

### Field: Reason

- **Application:** Spare Parts Shop
- **Page:** Product details -> dialog "Adjust stock — …"
- **Type:** textarea
- **Purpose:** Why stock is adjusted. Required -- every adjustment must be explained.
- **What user enters:** Free text (several lines allowed).
- **Required:** Yes
- **Validation:** required by the form; server rules: see top of this document
- **Permission:** `inventory.write` (the dialog saves with `POST /inventory/adjust`)
- **What happens after Save:** the "Adjust stock — …" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Location, Change in quantity
- **Source evidence:** `ui/stock.tsx:104`

### Field: From

- **Application:** Spare Parts Shop
- **Page:** Product details -> dialog "Transfer stock — …"
- **Type:** select
- **Purpose:** Where stock moves from (transfer) / start of a period (reports).
- **What user enters:** Choose one option.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `inventory.write` (the dialog saves with `POST /inventory/transfer`)
- **What happens after Save:** the "Transfer stock — …" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** To, Quantity, Note
- **Source evidence:** `ui/stock.tsx:125`

### Field: To

- **Application:** Spare Parts Shop
- **Page:** Product details -> dialog "Transfer stock — …"
- **Type:** select
- **Purpose:** Where stock moves to (transfer) / end of a period (reports).
- **What user enters:** Choose one option.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `inventory.write` (the dialog saves with `POST /inventory/transfer`)
- **What happens after Save:** the "Transfer stock — …" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** From, Quantity, Note
- **Source evidence:** `ui/stock.tsx:126`

### Field: Quantity

- **Application:** Spare Parts Shop
- **Page:** Product details -> dialog "Transfer stock — …"
- **Type:** number
- **Purpose:** Number of units.
- **What user enters:** A whole number.
- **Required:** Yes
- **Validation:** required by the form; number; server rules: see top of this document
- **Permission:** `inventory.write` (the dialog saves with `POST /inventory/transfer`)
- **What happens after Save:** the "Transfer stock — …" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** From, To, Note
- **Source evidence:** `ui/stock.tsx:127`

### Field: Note

- **Application:** Spare Parts Shop
- **Page:** Product details -> dialog "Transfer stock — …"
- **Type:** text
- **Purpose:** Free note recorded with the movement or document.
- **What user enters:** Text.
- **Required:** No (left out when empty)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `inventory.write` (the dialog saves with `POST /inventory/transfer`)
- **What happens after Save:** the "Transfer stock — …" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** From, To, Quantity
- **Source evidence:** `ui/stock.tsx:128`

### Field: SKU (your own code)

- **Application:** Spare Parts Shop
- **Page:** Product details -> dialog "Edit product"
- **Type:** text
- **Purpose:** The shop's own unique product code. Must be unique; it cannot be removed later.
- **What user enters:** Text.
- **Required:** Yes
- **Validation:** required by the form; server rules: see top of this document
- **Permission:** `products.write` (the dialog saves with `PATCH /products/:id`)
- **What happens after Save:** the "Edit product" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Name, Brand, Manufacturer, Category, Condition, Selling price, Cost price, Reorder level
- **Source evidence:** `ui/productForm.ts:10`

### Field: Name

- **Application:** Spare Parts Shop
- **Page:** Product details -> dialog "Edit product"
- **Type:** text
- **Purpose:** The name of the record (customer, supplier, warehouse, product...).
- **What user enters:** Text.
- **Required:** Yes
- **Validation:** required by the form; server rules: see top of this document
- **Permission:** `products.write` (the dialog saves with `PATCH /products/:id`)
- **What happens after Save:** the "Edit product" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** SKU (your own code), Brand, Manufacturer, Category, Condition, Selling price, Cost price, Reorder level
- **Source evidence:** `ui/productForm.ts:11`

### Field: Brand

- **Application:** Spare Parts Shop
- **Page:** Product details -> dialog "Edit product"
- **Type:** text
- **Purpose:** Brand of the product (for example the maker of an aftermarket part).
- **What user enters:** Text.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `products.write` (the dialog saves with `PATCH /products/:id`)
- **What happens after Save:** the "Edit product" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** SKU (your own code), Name, Manufacturer, Category, Condition, Selling price, Cost price, Reorder level
- **Source evidence:** `ui/productForm.ts:12`

### Field: Manufacturer

- **Application:** Spare Parts Shop
- **Page:** Product details -> dialog "Edit product"
- **Type:** text
- **Purpose:** Manufacturer of the part.
- **What user enters:** Text.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `products.write` (the dialog saves with `PATCH /products/:id`)
- **What happens after Save:** the "Edit product" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** SKU (your own code), Name, Brand, Category, Condition, Selling price, Cost price, Reorder level
- **Source evidence:** `ui/productForm.ts:13`

### Field: Category

- **Application:** Spare Parts Shop
- **Page:** Product details -> dialog "Edit product"
- **Type:** text
- **Purpose:** Product group used for filtering and reports.
- **What user enters:** Text.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `products.write` (the dialog saves with `PATCH /products/:id`)
- **What happens after Save:** the "Edit product" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** SKU (your own code), Name, Brand, Manufacturer, Condition, Selling price, Cost price, Reorder level
- **Source evidence:** `ui/productForm.ts:14`

### Field: Condition

- **Application:** Spare Parts Shop
- **Page:** Product details -> dialog "Edit product"
- **Type:** select (options: New, Used, Remanufactured, Other)
- **Purpose:** Condition of the part: New, Used, Remanufactured or Other.
- **What user enters:** Choose one option: New, Used, Remanufactured, Other.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `products.write` (the dialog saves with `PATCH /products/:id`)
- **What happens after Save:** the "Edit product" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** SKU (your own code), Name, Brand, Manufacturer, Category, Selling price, Cost price, Reorder level
- **Source evidence:** `ui/productForm.ts:15`

### Field: Selling price

- **Application:** Spare Parts Shop
- **Page:** Product details -> dialog "Edit product"
- **Type:** money
- **Purpose:** The price the shop charges the customer. Used to price quotation lines automatically.
- **What user enters:** An amount, for example 125.00.
- **Required:** No (form does not require it)
- **Validation:** amount (money); server rules: see top of this document
- **Permission:** `products.write` (the dialog saves with `PATCH /products/:id`)
- **What happens after Save:** the "Edit product" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** SKU (your own code), Name, Brand, Manufacturer, Category, Condition, Cost price, Reorder level
- **Source evidence:** `ui/productForm.ts:24`

### Field: Cost price

- **Application:** Spare Parts Shop
- **Page:** Product details -> dialog "Edit product"
- **Type:** money
- **Purpose:** What the shop pays for the part. Only visible and editable with the cost permission (products.cost.read); used for stock value.
- **What user enters:** An amount, for example 125.00.
- **Required:** No (form does not require it)
- **Validation:** amount (money); server rules: see top of this document
- **Permission:** `products.write` (the dialog saves with `PATCH /products/:id`)
- **What happens after Save:** the "Edit product" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** SKU (your own code), Name, Brand, Manufacturer, Category, Condition, Selling price, Reorder level
- **Source evidence:** `ui/productForm.ts:27`

### Field: Reorder level

- **Application:** Spare Parts Shop
- **Page:** Product details -> dialog "Edit product"
- **Type:** number
- **Purpose:** When available stock falls to this number, the product shows as low stock / needs reordering.
- **What user enters:** A whole number. Hint shown: "Warn when available stock falls to this number.".
- **Required:** No (form does not require it)
- **Validation:** number; server rules: see top of this document
- **Permission:** `products.write` (the dialog saves with `PATCH /products/:id`)
- **What happens after Save:** the "Edit product" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** SKU (your own code), Name, Brand, Manufacturer, Category, Condition, Selling price, Cost price
- **Source evidence:** `ui/productForm.ts:29`

### Field: Unit

- **Application:** Spare Parts Shop
- **Page:** Product details -> dialog "Edit product"
- **Type:** text
- **Purpose:** Unit of measure (for example piece).
- **What user enters:** Text. Placeholder: "Each".
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `products.write` (the dialog saves with `PATCH /products/:id`)
- **What happens after Save:** the "Edit product" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** SKU (your own code), Name, Brand, Manufacturer, Category, Condition, Selling price, Cost price
- **Source evidence:** `ui/productForm.ts:35`

### Field: Description

- **Application:** Spare Parts Shop
- **Page:** Product details -> dialog "Edit product"
- **Type:** textarea
- **Purpose:** Longer description.
- **What user enters:** Free text (several lines allowed).
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `products.write` (the dialog saves with `PATCH /products/:id`)
- **What happens after Save:** the "Edit product" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** SKU (your own code), Name, Brand, Manufacturer, Category, Condition, Selling price, Cost price
- **Source evidence:** `ui/productForm.ts:36`

### Field: Status

- **Application:** Spare Parts Shop
- **Page:** Product details -> dialog "Edit product"
- **Type:** select (options: Active, Inactive)
- **Purpose:** Active or Inactive. Inactive records stay in history but are not offered for new documents.
- **What user enters:** Choose one option: Active, Inactive.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `products.write` (the dialog saves with `PATCH /products/:id`)
- **What happens after Save:** the "Edit product" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** SKU (your own code), Name, Brand, Manufacturer, Category, Condition, Selling price, Cost price
- **Source evidence:** `ui/productForm.ts:37`

### Field: Default supplier

- **Application:** Spare Parts Shop
- **Page:** Product details -> dialog "Edit product"
- **Type:** select (options: — none —)
- **Purpose:** The supplier usually used to buy this product.
- **What user enters:** Choose one option: — none —.
- **Required:** No (left out when empty)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `products.write` (the dialog saves with `PATCH /products/:id`)
- **What happens after Save:** the "Edit product" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** SKU (your own code), Name, Brand, Manufacturer, Category, Condition, Selling price, Cost price
- **Source evidence:** `ui/productForm.ts:48`

### Field: Opening stock location

- **Application:** Spare Parts Shop
- **Page:** Product details -> dialog "Edit product"
- **Type:** select (options: — no opening stock —)
- **Purpose:** Where the opening stock is stored (warehouse location). Required when an opening quantity is entered.
- **What user enters:** Choose one option: — no opening stock —.
- **Required:** No (left out when empty)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `products.write` (the dialog saves with `PATCH /products/:id`)
- **What happens after Save:** the "Edit product" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** SKU (your own code), Name, Brand, Manufacturer, Category, Condition, Selling price, Cost price
- **Source evidence:** `ui/productForm.ts:60`

### Field: Opening stock quantity

- **Application:** Spare Parts Shop
- **Page:** Product details -> dialog "Edit product"
- **Type:** number
- **Purpose:** How many are on the shelf when the product is created; recorded as an opening-balance stock movement.
- **What user enters:** A whole number.
- **Required:** No (left out when empty)
- **Validation:** number; server rules: see top of this document
- **Permission:** `products.write` (the dialog saves with `PATCH /products/:id`)
- **What happens after Save:** the "Edit product" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** SKU (your own code), Name, Brand, Manufacturer, Category, Condition, Selling price, Cost price
- **Source evidence:** `ui/productForm.ts:70`

## Page: New purchase order (`/purchasing/new`)

### Field: Supplier

- **Application:** Spare Parts Shop
- **Page:** New purchase order
- **Type:** select (options: Choose a supplier…)
- **Purpose:** The supplier (company you buy from).
- **What user enters:** Choose one option: Choose a supplier….
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `purchasing.write` (every save on this page needs it: `POST /purchase-orders`)
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** Receive into, Expected date, Notes
- **Source evidence:** `app/(app)/purchasing/new/page.tsx:64`

### Field: Receive into

- **Application:** Spare Parts Shop
- **Page:** New purchase order
- **Type:** select (options: Choose a location…)
- **Purpose:** Location the received goods go to.
- **What user enters:** Choose one option: Choose a location….
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `purchasing.write` (every save on this page needs it: `POST /purchase-orders`)
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** Supplier, Expected date, Notes
- **Source evidence:** `app/(app)/purchasing/new/page.tsx:77`

### Field: Expected date

- **Application:** Spare Parts Shop
- **Page:** New purchase order
- **Type:** date
- **Purpose:** When the supplier is expected to deliver.
- **What user enters:** A date.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `purchasing.write` (every save on this page needs it: `POST /purchase-orders`)
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** Supplier, Receive into, Notes
- **Source evidence:** `app/(app)/purchasing/new/page.tsx:94`

### Field: Notes

- **Application:** Spare Parts Shop
- **Page:** New purchase order
- **Type:** text
- **Purpose:** Free notes about the record.
- **What user enters:** Text.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `purchasing.write` (every save on this page needs it: `POST /purchase-orders`)
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** Supplier, Receive into, Expected date
- **Source evidence:** `app/(app)/purchasing/new/page.tsx:101`

## Page: Quotation (`/quotations/[id]`)

### Field: If there is not enough stock

- **Application:** Spare Parts Shop
- **Page:** Quotation -> dialog "Create order"
- **Type:** select (options: Do not create the order, Create it and back-order the shortfall)
- **Purpose:** When creating the order from a quotation and stock is short: Do not create the order, or Create it and back-order the shortfall.
- **What user enters:** Choose one option: Do not create the order, Create it and back-order the shortfall.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `orders.write` (the dialog saves with `POST /quotations/:id/order`)
- **What happens after Save:** the "Create order" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Source evidence:** `app/(app)/quotations/[id]/page.tsx:233`

## Page: New quotation (`/quotations/new`)

### Field: Customer

- **Application:** Spare Parts Shop
- **Page:** New quotation
- **Type:** select (options: Choose a customer…)
- **Purpose:** The customer the document is for.
- **What user enters:** Choose one option: Choose a customer….
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `quotations.write` (every save on this page needs it: `POST /quotations`)
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Source evidence:** `app/(app)/quotations/new/page.tsx:53`

## Page: Reports (`/reports`)

### Field: From

- **Application:** Spare Parts Shop
- **Page:** Reports
- **Type:** date
- **Purpose:** Where stock moves from (transfer) / start of a period (reports).
- **What user enters:** A date.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: see top of this document
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** To
- **Source evidence:** `app/(app)/reports/page.tsx:121`

### Field: To

- **Application:** Spare Parts Shop
- **Page:** Reports
- **Type:** text
- **Purpose:** Where stock moves to (transfer) / end of a period (reports).
- **What user enters:** Text.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: see top of this document
- **What happens after Save:** saved with the page's form / used by the page's action; NOT CONFIRMED in more detail.
- **Related fields:** From
- **Source evidence:** `app/(app)/reports/page.tsx:129`

## Page: Suppliers (`/suppliers`)

### Field: Status

- **Application:** Spare Parts Shop
- **Page:** Suppliers -> dialog "New supplier"
- **Type:** select (options: Active, Inactive)
- **Purpose:** Active or Inactive. Inactive records stay in history but are not offered for new documents.
- **What user enters:** Choose one option: Active, Inactive.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `suppliers.write` (the dialog saves with `POST /suppliers`)
- **What happens after Save:** the "New supplier" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Name, Contact person, Phone, Email, Country, Tax number, Currency, Payment terms
- **Source evidence:** `ui/parties.ts:3`

### Field: Name

- **Application:** Spare Parts Shop
- **Page:** Suppliers -> dialog "New supplier"
- **Type:** text
- **Purpose:** The name of the record (customer, supplier, warehouse, product...).
- **What user enters:** Text.
- **Required:** Yes
- **Validation:** required by the form; server rules: see top of this document
- **Permission:** `suppliers.write` (the dialog saves with `POST /suppliers`)
- **What happens after Save:** the "New supplier" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Status, Contact person, Phone, Email, Country, Tax number, Currency, Payment terms
- **Source evidence:** `ui/parties.ts:13`

### Field: Contact person

- **Application:** Spare Parts Shop
- **Page:** Suppliers -> dialog "New supplier"
- **Type:** text
- **Purpose:** The person to talk to at this customer or supplier.
- **What user enters:** Text.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `suppliers.write` (the dialog saves with `POST /suppliers`)
- **What happens after Save:** the "New supplier" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Status, Name, Phone, Email, Country, Tax number, Currency, Payment terms
- **Source evidence:** `ui/parties.ts:14`

### Field: Phone

- **Application:** Spare Parts Shop
- **Page:** Suppliers -> dialog "New supplier"
- **Type:** text
- **Purpose:** Telephone number of the person or company.
- **What user enters:** Text.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `suppliers.write` (the dialog saves with `POST /suppliers`)
- **What happens after Save:** the "New supplier" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Status, Name, Contact person, Email, Country, Tax number, Currency, Payment terms
- **Source evidence:** `ui/parties.ts:15`

### Field: Email

- **Application:** Spare Parts Shop
- **Page:** Suppliers -> dialog "New supplier"
- **Type:** email
- **Purpose:** Email address of the person or company.
- **What user enters:** An email address.
- **Required:** No (form does not require it)
- **Validation:** must be an email address; server rules: see top of this document
- **Permission:** `suppliers.write` (the dialog saves with `POST /suppliers`)
- **What happens after Save:** the "New supplier" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Status, Name, Contact person, Phone, Country, Tax number, Currency, Payment terms
- **Source evidence:** `ui/parties.ts:16`

### Field: Country

- **Application:** Spare Parts Shop
- **Page:** Suppliers -> dialog "New supplier"
- **Type:** text
- **Purpose:** Country of the customer or supplier.
- **What user enters:** Text.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `suppliers.write` (the dialog saves with `POST /suppliers`)
- **What happens after Save:** the "New supplier" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Status, Name, Contact person, Phone, Email, Tax number, Currency, Payment terms
- **Source evidence:** `ui/parties.ts:17`

### Field: Tax number

- **Application:** Spare Parts Shop
- **Page:** Suppliers -> dialog "New supplier"
- **Type:** text
- **Purpose:** Tax / VAT number of the customer or supplier.
- **What user enters:** Text.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `suppliers.write` (the dialog saves with `POST /suppliers`)
- **What happens after Save:** the "New supplier" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Status, Name, Contact person, Phone, Email, Country, Currency, Payment terms
- **Source evidence:** `ui/parties.ts:18`

### Field: Currency

- **Application:** Spare Parts Shop
- **Page:** Suppliers -> dialog "New supplier"
- **Type:** text
- **Purpose:** 3-letter currency code (for example AED) used for prices and documents.
- **What user enters:** Text. Hint shown: "3-letter code, e.g. AED".
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `suppliers.write` (the dialog saves with `POST /suppliers`)
- **What happens after Save:** the "New supplier" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Status, Name, Contact person, Phone, Email, Country, Tax number, Payment terms
- **Source evidence:** `ui/parties.ts:19`

### Field: Payment terms

- **Application:** Spare Parts Shop
- **Page:** Suppliers -> dialog "New supplier"
- **Type:** text
- **Purpose:** Agreed payment terms text (for example '30 days').
- **What user enters:** Text.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `suppliers.write` (the dialog saves with `POST /suppliers`)
- **What happens after Save:** the "New supplier" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Status, Name, Contact person, Phone, Email, Country, Tax number, Currency
- **Source evidence:** `ui/parties.ts:20`

### Field: Notes

- **Application:** Spare Parts Shop
- **Page:** Suppliers -> dialog "New supplier"
- **Type:** textarea
- **Purpose:** Free notes about the record.
- **What user enters:** Free text (several lines allowed).
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `suppliers.write` (the dialog saves with `POST /suppliers`)
- **What happens after Save:** the "New supplier" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Status, Name, Contact person, Phone, Email, Country, Tax number, Currency
- **Source evidence:** `ui/parties.ts:22`

### Field: Billing address

- **Application:** Spare Parts Shop
- **Page:** Suppliers -> dialog "New supplier"
- **Type:** textarea
- **Purpose:** Address printed on invoices to this customer.
- **What user enters:** Free text (several lines allowed).
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `suppliers.write` (the dialog saves with `POST /suppliers`)
- **What happens after Save:** the "New supplier" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Status, Name, Contact person, Phone, Email, Country, Tax number, Currency
- **Source evidence:** `ui/parties.ts:26`

### Field: Shipping address

- **Application:** Spare Parts Shop
- **Page:** Suppliers -> dialog "New supplier"
- **Type:** textarea
- **Purpose:** Address goods are delivered to.
- **What user enters:** Free text (several lines allowed).
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `suppliers.write` (the dialog saves with `POST /suppliers`)
- **What happens after Save:** the "New supplier" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Status, Name, Contact person, Phone, Email, Country, Tax number, Currency
- **Source evidence:** `ui/parties.ts:27`

### Field: Credit limit

- **Application:** Spare Parts Shop
- **Page:** Suppliers -> dialog "New supplier"
- **Type:** money
- **Purpose:** Maximum amount this customer may owe (stored with the customer; optional).
- **What user enters:** An amount, for example 125.00.
- **Required:** No (left out when empty)
- **Validation:** amount (money); server rules: see top of this document
- **Permission:** `suppliers.write` (the dialog saves with `POST /suppliers`)
- **What happens after Save:** the "New supplier" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Status, Name, Contact person, Phone, Email, Country, Tax number, Currency
- **Source evidence:** `ui/parties.ts:28`

## Page: Supplier (`/suppliers/[id]`)

### Field: Status

- **Application:** Spare Parts Shop
- **Page:** Supplier -> dialog "Edit supplier"
- **Type:** select (options: Active, Inactive)
- **Purpose:** Active or Inactive. Inactive records stay in history but are not offered for new documents.
- **What user enters:** Choose one option: Active, Inactive.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `suppliers.write` (the dialog saves with `PATCH /suppliers/:id`)
- **What happens after Save:** the "Edit supplier" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Name, Contact person, Phone, Email, Country, Tax number, Currency, Payment terms
- **Source evidence:** `ui/parties.ts:3`

### Field: Name

- **Application:** Spare Parts Shop
- **Page:** Supplier -> dialog "Edit supplier"
- **Type:** text
- **Purpose:** The name of the record (customer, supplier, warehouse, product...).
- **What user enters:** Text.
- **Required:** Yes
- **Validation:** required by the form; server rules: see top of this document
- **Permission:** `suppliers.write` (the dialog saves with `PATCH /suppliers/:id`)
- **What happens after Save:** the "Edit supplier" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Status, Contact person, Phone, Email, Country, Tax number, Currency, Payment terms
- **Source evidence:** `ui/parties.ts:13`

### Field: Contact person

- **Application:** Spare Parts Shop
- **Page:** Supplier -> dialog "Edit supplier"
- **Type:** text
- **Purpose:** The person to talk to at this customer or supplier.
- **What user enters:** Text.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `suppliers.write` (the dialog saves with `PATCH /suppliers/:id`)
- **What happens after Save:** the "Edit supplier" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Status, Name, Phone, Email, Country, Tax number, Currency, Payment terms
- **Source evidence:** `ui/parties.ts:14`

### Field: Phone

- **Application:** Spare Parts Shop
- **Page:** Supplier -> dialog "Edit supplier"
- **Type:** text
- **Purpose:** Telephone number of the person or company.
- **What user enters:** Text.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `suppliers.write` (the dialog saves with `PATCH /suppliers/:id`)
- **What happens after Save:** the "Edit supplier" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Status, Name, Contact person, Email, Country, Tax number, Currency, Payment terms
- **Source evidence:** `ui/parties.ts:15`

### Field: Email

- **Application:** Spare Parts Shop
- **Page:** Supplier -> dialog "Edit supplier"
- **Type:** email
- **Purpose:** Email address of the person or company.
- **What user enters:** An email address.
- **Required:** No (form does not require it)
- **Validation:** must be an email address; server rules: see top of this document
- **Permission:** `suppliers.write` (the dialog saves with `PATCH /suppliers/:id`)
- **What happens after Save:** the "Edit supplier" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Status, Name, Contact person, Phone, Country, Tax number, Currency, Payment terms
- **Source evidence:** `ui/parties.ts:16`

### Field: Country

- **Application:** Spare Parts Shop
- **Page:** Supplier -> dialog "Edit supplier"
- **Type:** text
- **Purpose:** Country of the customer or supplier.
- **What user enters:** Text.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `suppliers.write` (the dialog saves with `PATCH /suppliers/:id`)
- **What happens after Save:** the "Edit supplier" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Status, Name, Contact person, Phone, Email, Tax number, Currency, Payment terms
- **Source evidence:** `ui/parties.ts:17`

### Field: Tax number

- **Application:** Spare Parts Shop
- **Page:** Supplier -> dialog "Edit supplier"
- **Type:** text
- **Purpose:** Tax / VAT number of the customer or supplier.
- **What user enters:** Text.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `suppliers.write` (the dialog saves with `PATCH /suppliers/:id`)
- **What happens after Save:** the "Edit supplier" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Status, Name, Contact person, Phone, Email, Country, Currency, Payment terms
- **Source evidence:** `ui/parties.ts:18`

### Field: Currency

- **Application:** Spare Parts Shop
- **Page:** Supplier -> dialog "Edit supplier"
- **Type:** text
- **Purpose:** 3-letter currency code (for example AED) used for prices and documents.
- **What user enters:** Text. Hint shown: "3-letter code, e.g. AED".
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `suppliers.write` (the dialog saves with `PATCH /suppliers/:id`)
- **What happens after Save:** the "Edit supplier" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Status, Name, Contact person, Phone, Email, Country, Tax number, Payment terms
- **Source evidence:** `ui/parties.ts:19`

### Field: Payment terms

- **Application:** Spare Parts Shop
- **Page:** Supplier -> dialog "Edit supplier"
- **Type:** text
- **Purpose:** Agreed payment terms text (for example '30 days').
- **What user enters:** Text.
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `suppliers.write` (the dialog saves with `PATCH /suppliers/:id`)
- **What happens after Save:** the "Edit supplier" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Status, Name, Contact person, Phone, Email, Country, Tax number, Currency
- **Source evidence:** `ui/parties.ts:20`

### Field: Notes

- **Application:** Spare Parts Shop
- **Page:** Supplier -> dialog "Edit supplier"
- **Type:** textarea
- **Purpose:** Free notes about the record.
- **What user enters:** Free text (several lines allowed).
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `suppliers.write` (the dialog saves with `PATCH /suppliers/:id`)
- **What happens after Save:** the "Edit supplier" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Status, Name, Contact person, Phone, Email, Country, Tax number, Currency
- **Source evidence:** `ui/parties.ts:22`

### Field: Billing address

- **Application:** Spare Parts Shop
- **Page:** Supplier -> dialog "Edit supplier"
- **Type:** textarea
- **Purpose:** Address printed on invoices to this customer.
- **What user enters:** Free text (several lines allowed).
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `suppliers.write` (the dialog saves with `PATCH /suppliers/:id`)
- **What happens after Save:** the "Edit supplier" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Status, Name, Contact person, Phone, Email, Country, Tax number, Currency
- **Source evidence:** `ui/parties.ts:26`

### Field: Shipping address

- **Application:** Spare Parts Shop
- **Page:** Supplier -> dialog "Edit supplier"
- **Type:** textarea
- **Purpose:** Address goods are delivered to.
- **What user enters:** Free text (several lines allowed).
- **Required:** No (form does not require it)
- **Validation:** no form-level rule; server rules: see top of this document
- **Permission:** `suppliers.write` (the dialog saves with `PATCH /suppliers/:id`)
- **What happens after Save:** the "Edit supplier" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Status, Name, Contact person, Phone, Email, Country, Tax number, Currency
- **Source evidence:** `ui/parties.ts:27`

### Field: Credit limit

- **Application:** Spare Parts Shop
- **Page:** Supplier -> dialog "Edit supplier"
- **Type:** money
- **Purpose:** Maximum amount this customer may owe (stored with the customer; optional).
- **What user enters:** An amount, for example 125.00.
- **Required:** No (left out when empty)
- **Validation:** amount (money); server rules: see top of this document
- **Permission:** `suppliers.write` (the dialog saves with `PATCH /suppliers/:id`)
- **What happens after Save:** the "Edit supplier" dialog sends the values to the server; on success the dialog closes and the page refreshes, on a validation error the message is shown and nothing is saved.
- **Related fields:** Status, Name, Contact person, Phone, Email, Country, Tax number, Currency
- **Source evidence:** `ui/parties.ts:28`
