# Lesson 8 — The internet café website — Every day (staff)

Topic for: shop owners, managers and staff. Source: IntraForge Training Guide, Lesson 8 — The internet café website.

- The `cafe_orders` table lists every order: **paid** (with its receipt and code), **pending**, **expired**,
  **cancelled** or **failed**.
- A package with no codes left shows **Sold out** by itself. Import more codes from the router.
- "I paid but I have no code": use **My code** with the customer's order number and phone, or look up the order in
  `cafe_orders`. Its receipt number matches the IF Pay receipt.

### Exercise 8

1. Add a package "Two hours" (120 minutes) and import three 120-minute codes. 2. Buy it on a phone with a test wallet.
3. Find the order in `cafe_orders` and check the code is marked **sold** in `cafe_vouchers`. 4. Start a purchase and do
not pay: after two minutes check the code is **available** again.
