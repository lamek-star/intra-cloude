# Lesson 8 — The internet café website — Setting up (the owner, once)

Topic for: shop owners, managers and staff. Source: IntraForge Training Guide, Lesson 8 — The internet café website.

1. In the router: make voucher codes for each package (for example 30 min, 1 hour, 3 hours) and allow the IntraForge
   PC's address before login (the "walled garden").
2. In IntraForge: create the `Internet Cafe` database with its four tables, enter the packages and the café's details,
   and import the codes from a CSV file.
3. **Websites > New website**: upload `internet-cafe-site.zip` with the address `netspot`.
4. **Developer > Applications** > the website: **Allow IntraForge Pay**, and give it read and write on the `Internet
   Cafe` database.

> **Careful:** the two "unique" columns (`cafe_vouchers.code` and `cafe_orders.voucher`) are what stop one code being
> sold twice. The website refuses to sell until they are there.
