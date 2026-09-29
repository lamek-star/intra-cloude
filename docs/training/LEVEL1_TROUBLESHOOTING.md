# Level 1 -- troubleshooting

Real messages from the applications and what to do. Fixes are only those the applications support. Appendix: every message found in the code.

## IntraForge does not open in the browser

- **What it means:** IntraForge (or Docker, which it runs on) is not running, or still starting.
- **What to check:** Open the **IntraForge** shortcut (Control Center): what is the status? Starting / Stopped / Failed / Degraded?
- **How to fix:** Stopped: press **Start**. Starting: wait 1-2 minutes. Degraded or Failed: **Restart services**.
- **When to contact an administrator:** If it stays Failed or Repair required: press **Diagnostics** and send the zip (no passwords or keys inside).

## The browser says the connection is not private / certificate warning

- **What it means:** IntraForge uses the PC's own certificate.
- **What to check:** The address is `https://localhost:8443`.
- **How to fix:** Choose *Advanced > continue*. This is expected on this PC.
- **When to contact an administrator:** If the address is different from localhost.

## "Invalid credentials." when signing in

- **What it means:** The email or password is wrong.
- **What to check:** Caps Lock; the email you registered with.
- **How to fix:** Type them again. There is no password-reset screen in IntraForge.
- **When to contact an administrator:** If you forgot the password: an administrator. (A reset screen is NOT IMPLEMENTED.)

## Signing in is refused after several tries

- **What it means:** Sign-in is limited to 10 attempts per minute on purpose (security).
- **What to check:** How many attempts in the last minute.
- **How to fix:** Wait one minute, then try once more carefully.
- **When to contact an administrator:** If it continues after waiting.

## "This account has MFA enabled — enter the 6-digit code from your authenticator app."

- **What it means:** Two-step sign-in is on for your account.
- **What to check:** The 6-digit code in your authenticator app (it changes every 30 seconds) and the phone's clock.
- **How to fix:** Enter the current code.
- **When to contact an administrator:** If you lost the phone with the authenticator.

## "You don't have permission …" (IntraForge pages)

- **What it means:** Your role does not include the permission this action needs; the server refused it.
- **What to check:** Which action / page; see LEVEL1_ROLES.md.
- **How to fix:** Ask an administrator to give you the right role.
- **When to contact an administrator:** Always -- roles are given by an administrator (and there is currently no screen to give roles; see the discrepancy list).

## A page says something "wasn't found" / "not found"

- **What it means:** The item does not exist, or it belongs to an organization you are not a member of (shown as not found on purpose).
- **What to check:** The link / address; your organization.
- **How to fix:** Open it from the lists instead of an old link.
- **When to contact an administrator:** If you should be a member of that organization.

## Spare Parts is not in Apps

- **What it means:** It is not installed in your organization, or you have no role that allows opening it.
- **What to check:** Apps page; ask whether Spare Parts is installed.
- **How to fix:** An administrator installs it (Apps > Install) or gives you a Spare Parts role.
- **When to contact an administrator:** Yes.

## A Spare Parts menu item is missing

- **What it means:** Each menu item needs its own permission; your role does not include it.
- **What to check:** LEVEL1_ROLES.md for your role.
- **How to fix:** Nothing to fix -- it is by design.
- **When to contact an administrator:** If your work needs it.

## "People, passwords and roles are managed in IntraForge (Organization > Members and Roles)."

- **What it means:** Inside IntraForge, Spare Parts' Users page cannot add or change people.
- **What to check:** --
- **How to fix:** Use IntraForge (add the member there).
- **When to contact an administrator:** To give roles (no screen yet).

## Spare Parts says "Insufficient available stock for … requested, … available."

- **What it means:** More is ordered than is available (on hand minus reserved).
- **What to check:** Stock & Locations: On hand, Reserved, Available.
- **How to fix:** Receive stock first, or create the order with *Create it and back-order the shortfall*.
- **When to contact an administrator:** If the stock count looks wrong.

## "Give a reason for the stock adjustment."

- **What it means:** An adjustment always needs a reason.
- **What to check:** The Reason field.
- **How to fix:** Write why (count difference, damage...).
- **When to contact an administrator:** --

## "… of the stock here is reserved for orders; release those first."

- **What it means:** The adjustment would leave less than what is reserved.
- **What to check:** Reserved on that location.
- **How to fix:** Deliver or cancel the order first, or adjust a smaller amount.
- **When to contact an administrator:** If unsure which order.

## "Choose two different locations." / "Only … available to transfer from this location."

- **What it means:** A transfer needs different From / To and at most the available quantity.
- **What to check:** From, To, Quantity.
- **How to fix:** Correct them.
- **When to contact an administrator:** --

## "SKU … already exists."

- **What it means:** Every shop product needs a unique SKU.
- **What to check:** Search My Products for that SKU.
- **How to fix:** Use a different SKU or open the existing product.
- **When to contact an administrator:** --

## "Choose a customer or enter a contact name."

- **What it means:** An enquiry needs a customer or a contact name.
- **What to check:** Existing customer / Contact name.
- **How to fix:** Fill one of them.
- **When to contact an administrator:** --

## "Add at least one part before submitting."

- **What it means:** The enquiry cart is empty.
- **What to check:** The cart.
- **How to fix:** Add parts with *Add to enquiry*.
- **When to contact an administrator:** --

## "Line … needs a description." / "Line … needs a price greater than zero."

- **What it means:** Every document line needs a description and a price above zero.
- **What to check:** The lines of the quotation / purchase order.
- **How to fix:** Complete the line or remove it.
- **When to contact an administrator:** --

## "The valid-until date is in the past."

- **What it means:** A quotation cannot be issued after its validity ended.
- **What to check:** Valid until.
- **How to fix:** Edit the quotation's validity, then issue.
- **When to contact an administrator:** --

## "That customer is inactive."

- **What it means:** Inactive customers cannot be used on new documents.
- **What to check:** The customer's status.
- **How to fix:** Set the customer Active (Edit).
- **When to contact an administrator:** --

## "A cancelled order cannot be invoiced."

- **What it means:** The order was cancelled.
- **What to check:** Order status.
- **How to fix:** Create a new quotation / order.
- **When to contact an administrator:** --

## "A void invoice cannot take payments." / "This invoice is already paid in full."

- **What it means:** The invoice is void or already paid.
- **What to check:** Invoice status and balance.
- **How to fix:** Nothing to pay.
- **When to contact an administrator:** If a payment was recorded by mistake: "Payments are permanent records. To correct a mistake, contact an administrator."

## "You may not change cost prices."

- **What it means:** Your role cannot see / change costs.
- **What to check:** --
- **How to fix:** Ask someone with the cost permission (Inventory / Manager).
- **When to contact an administrator:** --

## "Only PNG, JPEG, GIF or WebP images are accepted."

- **What it means:** Product photos must be one of these formats.
- **What to check:** The file type.
- **How to fix:** Save the photo as JPEG or PNG.
- **When to contact an administrator:** --

## Catalogue import refused without the confirmation

- **What it means:** You must confirm the organisation may use the data.
- **What to check:** The confirmation checkbox.
- **How to fix:** Tick it if true.
- **When to contact an administrator:** If you are not sure you may use the data.

## "No product in My Products matches that code. Search the Reference Catalogue instead."

- **What it means:** The scanned / typed code is not a shop product.
- **What to check:** The code.
- **How to fix:** Search the Reference Catalogue; import the part to My Products if the shop sells it.
- **When to contact an administrator:** --

## Stopped working after Windows restarted

- **What it means:** IntraForge starts at Windows **sign-in**, not at boot.
- **What to check:** Is someone signed in to Windows?
- **How to fix:** Sign in; wait 1-2 minutes.
- **When to contact an administrator:** If it does not come back: Diagnostics.

## A backup failed (Control Center shows the last backup in red)

- **What it means:** The daily backup did not complete.
- **What to check:** Free disk space; the message in the Control Center.
- **How to fix:** Press **Backup now**.
- **When to contact an administrator:** If it fails again: Diagnostics.

## A restore failed

- **What it means:** The chosen backup could not be restored; the shop was put back as it was automatically.
- **What to check:** The message: "Nothing was lost: IntraForge is running again with the data it had before this restore."
- **How to fix:** Use another backup; check it first with *Check this backup*.
- **When to contact an administrator:** Send Diagnostics.

## Appendix A -- every Spare Parts server message (from the code)

Kinds: *validation* = something entered is not acceptable (fix the input); *conflict* = the record's current state does not allow it; *notFound* = it does not exist (or was removed); *forbidden* / *unauthorized* = not allowed / not signed in. `…` stands for a value filled in at run time.

| Kind | Message | Source |
|---|---|---|
| conflict | A cancelled order cannot be invoiced. | `domain/sales.ts` |
| conflict | A product may have at most … photos. | `domain/products.ts` |
| conflict | A user with that email already exists. | `standalone/identity.ts` |
| conflict | A void invoice cannot take payments. | `domain/sales.ts` |
| conflict | A … enquiry cannot be cancelled. | `domain/sales.ts` |
| conflict | A … enquiry cannot be quoted. | `domain/sales.ts` |
| conflict | A … job cannot be cancelled. | `catalogue/importer.ts` |
| conflict | A … job cannot be imported. | `catalogue/importer.ts` |
| conflict | A … order cannot be fulfilled. | `domain/sales.ts` |
| conflict | A … order cannot reserve stock. | `domain/sales.ts` |
| conflict | A … purchase order cannot be …. | `domain/purchasing.ts` |
| conflict | A … purchase order cannot receive goods. | `domain/purchasing.ts` |
| conflict | A … quotation cannot be issued. | `domain/sales.ts` |
| conflict | A … quotation cannot be …. | `domain/sales.ts` |
| conflict | Give the location a code, or a rack, shelf or bin. | `domain/masterdata.ts` |
| conflict | Goods have already been delivered on this order. Record a return instead of cancelling. | `domain/sales.ts` |
| conflict | Goods have already been received on this order. | `domain/purchasing.ts` |
| conflict | Insufficient available stock for …: … requested, … available. | `domain/inventory.ts` |
| conflict | Insufficient available stock. | `standalone/repos/inventory.ts` |
| conflict | Invalid quantity for this reservation. | `standalone/repos/inventory.ts` |
| conflict | Location … already exists in this warehouse. | `domain/masterdata.ts` |
| conflict | Only a draft enquiry can be edited. | `domain/sales.ts` |
| conflict | Only a draft purchase order can be edited. | `domain/purchasing.ts` |
| conflict | Only a draft quotation can be edited. Cancel it and create a new one to change an issued quotation. | `domain/sales.ts` |
| conflict | Only … available to transfer from this location. | `domain/inventory.ts` |
| conflict | Only … on hand at this location. | `domain/inventory.ts` |
| conflict | Quotation … is …; only an accepted quotation can become an order. | `domain/sales.ts` |
| conflict | Reservation is no longer active. | `standalone/repos/inventory.ts` |
| conflict | Rows can only be excluded while the job awaits review. | `catalogue/importer.ts` |
| conflict | SKU … already exists. | `domain/products.ts` |
| conflict | That customer is inactive. | `domain/sales.ts` |
| conflict | That number is already on this product. | `domain/products.ts` |
| conflict | The shop SKU cannot be removed. | `domain/products.ts` |
| conflict | There is not enough reserved stock to fulfil that quantity. | `domain/inventory.ts` |
| conflict | There is nothing delivered that has not already been invoiced. Fulfil the order first. | `domain/sales.ts` |
| conflict | There must always be at least one active Owner. | `standalone/identity.ts` |
| conflict | This enquiry has already been submitted. | `domain/sales.ts` |
| conflict | This invoice has payments recorded and cannot be voided. | `domain/sales.ts` |
| conflict | This invoice is already paid in full. | `domain/sales.ts` |
| conflict | This job is not a staged CSV import. | `catalogue/importer.ts` |
| conflict | This product is already linked to that reference part. | `domain/products.ts` |
| conflict | This product was changed by someone else. Reload it and try again. | `domain/products.ts` |
| conflict | This quotation has expired. Create a new one to continue. | `domain/sales.ts` |
| conflict | This quotation was changed by someone else. Reload it and try again. | `domain/sales.ts` |
| conflict | … is inactive and cannot be reserved. | `domain/inventory.ts` |
| conflict | … of the stock here is reserved for orders; release those first. | `domain/inventory.ts` |
| forbidden | Cross-site requests are not allowed. | `http/core.ts` |
| forbidden | The security token is missing or has expired. Reload the page and try again. | `http/core.ts` |
| forbidden | This enquiry cart belongs to another user. | `domain/sales.ts` |
| forbidden | You may not change cost prices. | `domain/products.ts` |
| notFound | Customer | `domain/documents.ts` |
| notFound | Drawing | `domain/catalogue.ts` |
| notFound | Endpoint | `http/routes.ts` |
| notFound | Enquiry | `domain/sales.ts` |
| notFound | File | `http/routes.ts` |
| notFound | Image | `domain/catalogue.ts` |
| notFound | Import job | `catalogue/importer.ts` |
| notFound | Invoice | `domain/documents.ts` |
| notFound | Location | `domain/inventory.ts` |
| notFound | Number | `domain/products.ts` |
| notFound | Order line | `domain/purchasing.ts` |
| notFound | Photo | `domain/products.ts` |
| notFound | Product | `domain/inventory.ts` |
| notFound | Product for that code | `http/routes.ts` |
| notFound | Product on line … | `domain/purchasing.ts` |
| notFound | Purchase order | `domain/purchasing.ts` |
| notFound | Quotation | `domain/documents.ts` |
| notFound | Reference link | `domain/products.ts` |
| notFound | Reference part | `domain/catalogue.ts` |
| notFound | Report | `http/routes.ts` |
| notFound | Sales order | `domain/sales.ts` |
| notFound | Staged row | `catalogue/importer.ts` |
| notFound | Supplier | `domain/masterdata.ts` |
| notFound | Supplier link | `domain/products.ts` |
| notFound | User | `standalone/identity.ts` |
| notFound | Warehouse | `domain/masterdata.ts` |
| validation | A document may have at most 200 lines. | `domain/sales.ts` |
| validation | A purchase order may have at most 200 lines. | `domain/purchasing.ts` |
| validation | Add at least one line. | `domain/purchasing.ts` |
| validation | Add at least one part before submitting. | `domain/sales.ts` |
| validation | Adjustment must be a non-zero whole number. | `domain/inventory.ts` |
| validation | An enquiry may have at most 200 items. | `domain/sales.ts` |
| validation | Choose a customer or enter a contact name. | `domain/sales.ts` |
| validation | Choose a different password. | `standalone/identity.ts` |
| validation | Choose a file to upload. | `http/routes.ts` |
| validation | Choose a location for the opening stock. | `domain/products.ts` |
| validation | Choose the customer this quotation is for. | `domain/sales.ts` |
| validation | Choose the items being returned. | `domain/sales.ts` |
| validation | Choose two different locations. | `domain/inventory.ts` |
| validation | Confirm that you may store and show these drawings before importing them. | `catalogue/package.ts` |
| validation | Confirm that your organization may use this data before importing it. | `catalogue/importer.ts` |
| validation | Currency must be a 3-letter code such as AED. | `domain/validate.ts` |
| validation | Currency must be a 3-letter code. | `standalone/config.ts` |
| validation | Enter a valid email address. | `standalone/identity.ts` |
| validation | Enter a valid number. | `domain/products.ts` |
| validation | Enter the person's name. | `standalone/identity.ts` |
| validation | Give a reason for the stock adjustment. | `domain/inventory.ts` |
| validation | Images may be at most … MB. | `domain/products.ts` |
| validation | Larger than the 64 MB limit. | `catalogue/package.ts` |
| validation | Line … needs a description. | `domain/sales.ts` |
| validation | Line … needs a price greater than zero. | `domain/sales.ts` |
| validation | Map a column to manufacturer, or choose a default manufacturer. | `catalogue/importer.ts` |
| validation | Map a column to oem_number. | `catalogue/importer.ts` |
| validation | No PNG or JPEG drawings were found. | `catalogue/package.ts` |
| validation | Not a PNG/JPEG file. | `catalogue/package.ts` |
| validation | Nothing to fulfil. | `domain/sales.ts` |
| validation | Nothing to receive. | `domain/purchasing.ts` |
| validation | Only PNG, JPEG, GIF or WebP images are accepted. | `domain/products.ts` |
| validation | Only … more expected on this line. | `domain/purchasing.ts` |
| validation | Only … of "…" can be returned. | `domain/sales.ts` |
| validation | Only … of "…" remain to fulfil. | `domain/sales.ts` |
| validation | Part … is not in parts.csv or the catalogue; list it there first. | `catalogue/package.ts` |
| validation | Password is too long. | `standalone/identity.ts` |
| validation | Password must not contain your email name. | `standalone/identity.ts` |
| validation | Price every line before issuing — "…" has no price. | `domain/sales.ts` |
| validation | Provider key may use lower-case letters, digits and hyphens. | `catalogue/package.ts` |
| validation | Record the rights evidence or reason (at least 12 characters). | `domain/catalogue.ts` |
| validation | Tax rate is out of range. | `standalone/config.ts` |
| validation | That password is too easy to guess. | `standalone/identity.ts` |
| validation | The address is malformed. | `http/core.ts` |
| validation | The column mapping is not valid JSON. | `http/routes.ts` |
| validation | The file is empty. | `domain/products.ts` |
| validation | The file is not valid UTF-8 text. Save it as CSV (UTF-8) and try again. | `catalogue/importer.ts` |
| validation | The file name says .… but the content is …. | `domain/products.ts` |
| validation | The first account must be the Owner. | `standalone/identity.ts` |
| validation | The mapped column "…" does not exist in the file. | `catalogue/importer.ts` |
| validation | The payment exceeds the balance due (… minor units). | `domain/sales.ts` |
| validation | The photo order must list every photo exactly once. | `domain/products.ts` |
| validation | The request body is not valid JSON. | `http/core.ts` |
| validation | The request body must be a JSON object. | `http/core.ts` |
| validation | The upload could not be read. | `http/core.ts` |
| validation | The valid-until date is in the past. | `domain/sales.ts` |
| validation | This enquiry has no items. | `domain/sales.ts` |
| validation | This report cannot be exported as CSV. | `http/routes.ts` |
| validation | Unknown field "…" in the mapping. | `catalogue/importer.ts` |
| validation | Unknown image-rights state. | `domain/catalogue.ts` |
| validation | Unknown role. | `standalone/identity.ts` |
| validation | Unknown status. | `standalone/identity.ts` |
| validation | Unknown verification state. | `domain/catalogue.ts` |
| validation | Use a password of at least 10 characters. | `standalone/identity.ts` |
| validation | ids must be a list of image ids. | `http/routes.ts` |
| validation | type must be code128 or qr. | `http/routes.ts` |
| validation | … contains invalid characters. | `domain/validate.ts` |
| validation | … is not a valid email address. | `domain/validate.ts` |
| validation | … is required. | `domain/validate.ts` |
| validation | … must be a JSON object. | `domain/validate.ts` |
| validation | … must be a date (YYYY-MM-DD). | `domain/validate.ts` |
| validation | … must be a non-negative whole number. | `standalone/config.ts` |
| validation | … must be a whole number greater than zero. | `domain/inventory.ts` |
| validation | … must be a whole number. | `domain/validate.ts` |
| validation | … must be at least …. | `domain/validate.ts` |
| validation | … must be at most … characters. | `domain/validate.ts` |
| validation | … must be at most …. | `domain/validate.ts` |
| validation | … must be one of: …. | `domain/validate.ts` |
| validation | … must be text. | `domain/validate.ts` |
| validation | … must be true or false. | `http/core.ts` |

## Appendix B -- IntraForge screen messages (from the code)

- Analysis failed.
- Attach a file that's already been uploaded to a bucket in this project.
- Every widget re-runs against live data and re-checks your permissions each time this page loads.
- Failed to grant permission.
- Failed to load permissions.
- Files couldn't be loaded.
- Grant permission
- Installation failed.
- It could not be reinstated.
- Movements couldn't be loaded.
- Organizations are optional — your personal account already works without one. Create one when you need shared workspaces, storage, or databases.
- Part numbers couldn't be searched.
- Protect information using encryption, role-based permissions and audit trails.
- Sales couldn't be loaded.
- Stock couldn't be loaded.
- That application wasn't found.
- That product wasn't found.
- That project wasn't found.
- That sale wasn't found.
- The application could not be installed. Nothing is lost; please try again.
- The application could not be opened.
- The application could not be opened. Please try again.
- The application couldn't be opened.
- The applications could not be loaded.
- The applications couldn't be loaded.
- The file couldn't be added.
- The part number couldn't be added.
- The product couldn't be loaded.
- The sale was recorded but its order could not be found.
- The sales document couldn't be loaded.
- The … couldn't be added.
- The … couldn't be loaded.
- This application could not be loaded.
- This application isn't available.
- User roles and permissions
- You don't have permission to add files here.
- You don't have permission to create dashboards in this database.
- You don't have permission to install applications here. Ask an administrator.
- You don't have permission to manage sharing for this resource.
- You don't have permission to manage this application's credentials.
- You don't have permission to manage this application's permissions.
- You don't have permission to manage this environment's credentials.
- You don't have permission to manage this environment's secrets.
- You don't have permission to manage unit access.
- You don't have permission to view this application's environments.
- You don't have permission to view this organization's audit log (requires audit.read).
