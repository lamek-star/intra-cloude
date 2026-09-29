# Level 1 -- workflow screenshot sequence

A numbered sequence of screenshots that tells the story of one sale from start to finish. Every step below is supported by
the implementation (verified end to end by the automated browser test `apps/frontend/e2e/spare-parts-service-app.spec.ts`
and on the clean Windows test PC). Capture it in a **test organization with sample data**, not with real customers.

Prerequisite: an administrator has installed Spare Parts and the person capturing has the Spare Parts Manager (or Organization
Administrator) role, so every step is visible.

| # | Step | How to get there | What must be visible | Dialog open | File name |
|---|---|---|---|---|---|
| 01 | Start IntraForge | Double-click the **IntraForge** shortcut | Control Center status **Healthy**, Spare Parts listed with **Open** | -- | `WF-01-Control-Center-Healthy.png` |
| 02 | Login | Open IntraForge (`https://localhost:8443/login`) | Email, Password, sign-in button | -- | `WF-02-Login.png` |
| 03 | Dashboard | After signing in | Organizations, system health | -- | `WF-03-Dashboard.png` |
| 04 | Open the organization | Sidebar **Organizations** > the organization | Workspaces, members, buttons Apps / Teams / Units / Developer / Audit log | -- | `WF-04-Organization.png` |
| 05 | Applications | Sidebar **Apps** | Spare Parts card with status **Running**, **Open**, **Settings** | -- | `WF-05-Apps.png` |
| 06 | Open Spare Parts | **Open** | Spare Parts **Business overview** (no second sign-in) | -- | `WF-06-Spare-Parts-Dashboard.png` |
| 07 | Reference Catalogue | Menu **Reference Catalogue** | Search box, filters | -- | `WF-07-Reference-Catalogue.png` |
| 08 | Search OEM | Type a number without dashes, e.g. `1111036F00` > **Search** | Results with the formatted number `11110-36F00` | -- | `WF-08-Search-OEM.png` |
| 09 | Open the part | Click the part number | Part details, fitment, drawings, **IMPORT TO MY PRODUCTS**, **Add to enquiry** | -- | `WF-09-Part-Details.png` |
| 10 | Import to My Products | **IMPORT TO MY PRODUCTS** | Your SKU, Product name, Selling price, Cost price, Reorder level, Supplier, Store in, Quantity in stock now | **Import … to My Products** | `WF-10-Import-To-My-Products.png` |
| 11 | Complete the product | The new product page | Tabs Overview / Fitment / Stock / Supplier / OEM Reference / Sales / History; "Linked to the Reference Catalogue"; photo added | -- | `WF-11-Product-Details.png` |
| 12 | Receive stock | Product > **Stock** tab > **Receive** | Location, Quantity received, Note | **Receive stock — …** | `WF-12-Receive-Stock.png` |
| 13 | Stock after receiving | Product > **Stock** tab | On hand / Reserved / Available | -- | `WF-13-Stock-Levels.png` |
| 14 | Create customer | **Customers** > **New customer** | Name and details | **New customer** | `WF-14-New-Customer.png` |
| 15 | Create enquiry | Catalogue > **Add to enquiry**, then the cart | Cart lines; Existing customer / Contact name; **Submit enquiry** | -- | `WF-15-Enquiry-Cart.png` |
| 16 | Enquiry submitted | After **Submit enquiry** | Enquiry `ENQ-…` with **Create quotation** | -- | `WF-16-Enquiry.png` |
| 17 | Create quotation | **Create quotation** | Quotation `QUO-…`, lines priced from My Products, **Issue to customer** | -- | `WF-17-Quotation-Draft.png` |
| 18 | Quotation issued | **Issue to customer** | Status Issued, PDF link, **Customer accepted / rejected** | -- | `WF-18-Quotation-Issued.png` |
| 19 | Create order | **Customer accepted** > **Create order** | "If there is not enough stock" choice | **Create order** | `WF-19-Create-Order.png` |
| 20 | Order | After creating | Order `SO-…`/`ORD-…`, **Record delivery** | -- | `WF-20-Order.png` |
| 21 | Record delivery | **Record delivery** | Quantity per line | **Record delivery** | `WF-21-Record-Delivery.png` |
| 22 | Create invoice | **Invoice delivered items** | Invoice `INV-…` | -- | `WF-22-Invoice.png` |
| 23 | Record payment | **Record payment** | Amount (balance), Method, Reference, Notes | **Record payment** | `WF-23-Record-Payment.png` |
| 24 | Paid | After saving | Status **Paid** | -- | `WF-24-Invoice-Paid.png` |
| 25 | Review audit (app) | Menu **Audit log** | The day's actions | -- | `WF-25-Spare-Parts-Audit.png` |
| 26 | Review audit (IntraForge) | Organization > **Audit log** | `spareparts.…` events, filters | -- | `WF-26-IntraForge-Audit.png` |
| 27 | Logout | Spare Parts account menu > **Sign out**; IntraForge account menu > **Log out** | The sign-in page | -- | `WF-27-Logged-Out.png` |

Not included because it is not implemented in the user interface: assigning a role to a member (server API only), switching
on two-step sign-in (server API only), returning goods to a supplier.
