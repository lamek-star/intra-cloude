# Level 1 -- quick start for a new employee

Short answers to the first-day questions. Each answer is what the applications actually do. Words in **bold** are the exact
button or menu names on screen.

**How do I start IntraForge?**
It normally starts by itself when someone signs in to Windows (1-2 minutes). Otherwise double-click the **IntraForge**
shortcut (the Control Center) and press **Start**; when the status says **Healthy**, press **Open IntraForge**.

**How do I log in?**
In the browser at `https://localhost:8443`: **Email** and **Password**, then sign in. If your account has two-step sign-in,
also enter the 6-digit **Authenticator code**. (First time on this PC the browser warns about the certificate: *Advanced >
continue*.) New staff first create their own account (**Create account**: First name, Email, Password); an administrator then
adds them to the company and gives them a role.

**How do I open Spare Parts?**
Sidebar **Apps** > **Open** next to Spare Parts. No second sign-in. If Spare Parts is not listed, you have no role that allows
it yet -- ask the administrator.

**How do I search for an OEM part?**
Spare Parts > **Reference Catalogue** > type the part number in any format (with or without dashes or spaces) or a
description, vehicle or chassis > **Search**. Click a part number to see its fitment and drawings.

**How do I add a reference part to My Products?**
On the part's page press **IMPORT TO MY PRODUCTS**, fill **Your SKU** and **Product name** (required), selling price (and cost
price if you may see costs), reorder level, supplier, where it is stored and how many are on the shelf now, then save. (Needs
the inventory / manager role.)

**How do I check stock?**
**My Products** (columns Available and On hand), or open the product > **Stock** tab, or **Stock & Locations > Stock**
(On hand, Reserved, Available per location). *Available = on hand − reserved.*

**How do I receive stock?**
With a purchase order: **Purchase Orders** > the order > **Receive goods** > enter what arrived > **Receive into stock**.
Without one: on the product (or Stock & Locations) press **Receive**, choose the location, **Quantity received**, a note
(delivery note number) > save. Stock goes up.

**How do I find a product's location?**
Open the product > **Stock** tab: warehouse and location (rack / shelf / bin) with the quantities. Or scan its label in
**Scan / Lookup** to open it.

**How do I add a customer?**
**Customers** > **New customer** > **Name** (required) and the details you have > save.

**How do I create an enquiry?**
In the Reference Catalogue (a result, a part page or a drawing) press **Add to enquiry** for each part. Open the enquiry cart,
choose the **Existing customer** or type a **Contact name**, add phone / email / VIN if useful > **Submit enquiry**.

**How do I create a quotation?**
**Enquiries** > open the enquiry > **Create quotation** (lines are priced from My Products when the part number matches). Check
it, then **Issue to customer**; the quotation has a PDF. Or **Quotations** > **New quotation** directly.

**How do I create an order?**
When the customer agrees: on the quotation press **Customer accepted**, then **Create order**, and choose what to do if stock
is short. The order reserves the stock. When the goods leave: **Record delivery** > enter quantities > **Save delivery**.

**How do I create an invoice?**
On the order: **Invoice delivered items**. The invoice is created for what was delivered; it has a PDF.

**How do I record payment?**
On the invoice: **Record payment** > **Amount**, **Method** (Cash, Bank transfer, Card, Other), **Reference**, notes > save. The
invoice becomes *Partially paid* or *Paid*. Payments cannot be undone -- if you made a mistake, tell an administrator.

**How do I find an old transaction?**
Open the list (**Enquiries**, **Quotations**, **Orders**, **Invoices & Payments**, **Purchase Orders**) and use the search box and
the status filter; or open the **customer** to see all their quotations, orders and invoices. Managers can also look in the
**Audit log**.

**How do I log out?**
In Spare Parts: account menu > **Sign out** (you return to IntraForge). In IntraForge: account menu > **Log out** (this also ends
your Spare Parts session).

**Something does not work?** See LEVEL1_TROUBLESHOOTING.md.
