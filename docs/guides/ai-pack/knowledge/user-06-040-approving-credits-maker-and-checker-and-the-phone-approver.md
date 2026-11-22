# Lesson 6 — IntraForge Pay — Approving credits: maker and checker, and the phone approver

Topic for: shop owners, managers and staff. Source: IntraForge Training Guide, Lesson 6 — IntraForge Pay.

Giving a customer credits needs **two accounts**: one asks (the maker, under **Admin > Credits (maker/checker)**), a
**different** one approves (the checker: a **Pay Supervisor**, **Pay Manager** or Organization Administrator). Pay
never lets anyone approve their own request; the request shows "awaiting another checker" until someone else does.

With a second trusted person: give them **Pay Supervisor** (Organization > Members > Give a role).

With one owner, make a **phone approver**: **Control Center > Settings > Owner > Create the phone approver...**, keep
`approver@shop` (nothing is sent to it), press **Create** and **Yes** to open its link. On that page choose **Add a
passkey on my phone**, scan the QR code with your phone and confirm with your fingerprint or face. That account has
**no password**: it signs in only with your phone (**Sign in with a passkey**, scan the QR code). Sign in as the
approver, open **Pay > Admin > Credits** and approve. It is two devices, not two people: the audit log shows both
accounts. When a second trusted person joins, give them Pay Supervisor and remove the approver's role.
