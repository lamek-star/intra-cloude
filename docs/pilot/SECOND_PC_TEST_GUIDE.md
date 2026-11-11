# Testing IntraForge from a second PC on the shop network

This is a test plan for a real second PC (and, if you have one, a phone) on the same network as the shop PC. Work
through it in order; for every case write down **the case number, Pass or Fail, and what you saw**, and take a
screenshot of anything that looks wrong (Windows: `Win + Shift + S`). Send the list back and each failure gets fixed.

The words in **bold** are exactly what you click or see on screen.

## Part 0 -- Prepare the shop PC (5 minutes, on the shop PC)

When this guide was written the shop PC was set up like this, and **both settings stop a second PC from connecting**:

| What | Now | Needed |
| --- | --- | --- |
| IntraForge access | This computer only (listens on `127.0.0.1:8443`) | This PC and the shop network |
| Windows network type of the Wi-Fi | **Public** | **Private** (IntraForge's firewall rule admits Private networks only, on purpose) |

1. **Make the shop's Wi-Fi Private.** Windows **Settings > Network & internet > Wi-Fi >** your Wi-Fi's name **>
   Network profile type: Private network**. Do this only for your own shop's network, never a café or hotel Wi-Fi.
2. **Switch the shop network on.** Open **IntraForge Control Center > Settings > Shop network > Allow other PCs in this
   shop...**, tick that this is the shop's own network, press **Allow** and answer **Yes** to Windows' administrator
   question. IntraForge restarts (about a minute).
3. When it is back, the same Settings card says **"The other PCs in the shop open IntraForge at https://...:8443"**.
   Write that address down. It is normally `https://<this PC's name>:8443` and `https://<this PC's address>:8443`;
   when this guide was written the PC was `DESKTOP-AT6T184` at `192.168.8.37`, but read the real one from the card.
4. Copy the folder **`C:\IntraForgeData\shop-network`** to a USB stick (or a shared folder). It holds the certificate
   and the one-click script for the other PC.
5. In your router's settings, **reserve** this PC's address (often called *DHCP reservation* or *static lease*) so it
   does not change tomorrow. If you cannot, the Control Center tells you when the address changed, and **Update the
   address** fixes it.
6. Keep the shop PC on and awake for the whole test.

| # | Check on the shop PC | Expected |
| --- | --- | --- |
| 0.1 | Control Center home screen, **Access** line | Green: "This PC and the shop network: https://..." |
| 0.2 | Open the written address on the shop PC itself | IntraForge's sign-in page |

## Part 1 -- Connect the second PC

On the second PC (Windows 10 or 11, same Wi-Fi or same router):

1. Plug in the USB stick, open the `shop-network` folder and double-click **Trust-IntraForge-on-this-PC.cmd**. Answer
   **Yes** to Windows' certificate question. It trusts IntraForge's own certificate for this Windows user only, then
   opens the address.

| # | Test | Expected | If it fails, note |
| --- | --- | --- | --- |
| 1.1 | The script opens the address in the browser | IntraForge's sign-in page, padlock with no warning | The exact message |
| 1.2 | Type `https://<address>:8443` yourself in Edge and in Chrome | Same page, padlock in both | Which browser |
| 1.3 | Type `https://<PC name>:8443` (the name instead of the number) | Same page | Works with number but not name? |
| 1.4 | On the second PC, open **Command Prompt** and run `ping <address>` | Replies | "Request timed out" = network/firewall |
| 1.5 | Run `powershell -c "Test-NetConnection <address> -Port 8443"` | `TcpTestSucceeded : True` | Copy the output |

If 1.4 works but 1.5 fails, the shop PC's Wi-Fi is still Public (Part 0 step 1) or the shop network is off. If 1.4
fails too, the PCs are not on the same network (a guest Wi-Fi often separates devices).

## Part 2 -- People and permissions

| # | Test | Expected |
| --- | --- | --- |
| 2.1 | On the second PC: sign-in page > **Create one** (under "Don't have an account?"), with a new e-mail (for example `staff1@yourshop.local`) | The account is created; it belongs to no organization yet |
| 2.2 | On the shop PC, as the owner: **Organizations >** your shop **> Add member**, enter that e-mail | The staff member appears in the member list |
| 2.3 | On the second PC, sign out and in again as the staff member | They see the shop's organization, but **no** settings, audit log or other people's data unless given a role |
| 2.4 | Give the staff member a role (owner: the member's row > role) and reload on the second PC | Exactly what that role allows becomes visible; nothing more |
| 2.5 | Owner and staff signed in **at the same time** on the two PCs | Both keep working; neither is signed out |
| 2.6 | Type a wrong password 11 times in one minute on the second PC | After 10, "too many attempts, wait a minute" (on purpose) |

## Part 3 -- The apps from the second PC

Run each case as the staff member (with a role that may use the app) unless the case says owner.

| # | Test | Expected |
| --- | --- | --- |
| 3.1 | **Apps** > open **Spare Parts** | The app opens inside IntraForge at `/apps/spare-parts/` |
| 3.2 | Spare Parts: open a product > **Print label** | Preview shows the **shop's name**, the product name, the barcode and **Part No.**; Print opens a page sized for the paper |
| 3.3 | Print label > **QR**, **A4 sheet**, 24 copies > **Download picture** | A PNG page of 24 labels with light cut guides |
| 3.4 | Print one label on a real label printer (if you have one) | The label fits the paper; the barcode scans |
| 3.5 | Sell one item on the second PC; look at the stock on the shop PC | Stock goes down once, on both PCs after a reload |
| 3.6 | A staff member **without** the sell permission tries to sell | Refused with a clear message; stock unchanged |
| 3.7 | **Pharmacy** (if installed) > a prescription medicine > Print label | The label shows **Rx** boxed and **Item No.** |
| 3.8 | **Apps > Movie Shop** > open the shop | The catalogue with storage on the left, coloured folder tiles, posters, a **Today** card |
| 3.9 | Movie Shop: every folder tile is fully visible (none cut off at the left or right) | All visible, wrapping onto a second row if there are many |
| 3.10 | Movie Shop: sell a title for cash from the second PC; the shop PC's media agent copies it to a USB stick plugged into **the shop PC** | The sale moves to Paid, then Done; the files are on the stick; **Today** counts it |
| 3.11 | Pay (IF Pay) opens from Apps for someone with a Pay role | The Pay screen inside IntraForge |

Cases 3.2, 3.3, 3.7, 3.8 and 3.9 need the 1.5.6 kit (the new labels and the Movie Shop changes); on 1.5.5 they show
the old screens.

## Part 4 -- The Movie Shop's customer portal on a phone

The portal is for customers: they open it on their own phones on the shop's Wi-Fi.

| # | Test | Expected |
| --- | --- | --- |
| 4.1 | Owner: Movie Shop > **Customers** > portal on; note the portal address it shows | An address like `https://<address>:8443/portal/<shop>` |
| 4.2 | Phone on the shop Wi-Fi opens it | A certificate warning appears the first time (phones do not run the trust script); after accepting, the portal opens |
| 4.3 | Sign up on the phone with a name, phone number and password | "Waiting for the shop's approval" |
| 4.4 | Owner approves the customer on the shop PC or the second PC | The phone shows the catalogue after a refresh |
| 4.5 | Customer orders two titles; owner charges the order at the counter | The order shows Ready on the phone; points added |
| 4.6 | Customer: **Forgot password?** > owner gives a **Password code** > customer sets a new password with it | Customer signs in with the new password; the old one no longer works |

## Part 5 -- Resilience (what a real shop day does)

| # | Test | Expected |
| --- | --- | --- |
| 5.1 | Restart the **second** PC, open the address again | Works without running the trust script again |
| 5.2 | Restart the **shop** PC; wait 3 minutes after Windows starts | IntraForge comes back by itself; the second PC reconnects after a reload |
| 5.3 | Switch the shop PC's Wi-Fi off for 30 s while the second PC has a page open, then on | The page shows an error while offline, then works after a reload; nothing is lost |
| 5.4 | Two people edit the **same** product at the same time on the two PCs and both save | The later save either wins cleanly or is refused with a message; no half-saved record |
| 5.5 | Upload a 1 GB file from the second PC (Storage) | Progress, then the file is listed and downloads intact on the shop PC |
| 5.6 | Note how long the catalogue, a product page and a sale take to open on the second PC | Each under about 2 seconds on Wi-Fi |

## Part 6 -- Security checks a tester should always do

| # | Test | Expected |
| --- | --- | --- |
| 6.1 | From the second PC open `https://<address>:8443/admin/` | Not found, or a sign-in for administrators only; never an open admin page |
| 6.2 | From the second PC open `http://<address>:8443` (http, not https) | Refused or redirected to https; never served unencrypted |
| 6.3 | As the staff member, paste an address the owner used (for example an audit-log or settings page) | "You don't have permission", not the data |
| 6.4 | From a phone on a **different** network (mobile data, Wi-Fi off) open the address | Does not load: IntraForge is not on the internet unless the Super Administrator switches internet access on |
| 6.5 | Sign out on the second PC, press the browser's Back button | The sign-in page, not the previous data |

## Undo when the test is finished

To make IntraForge reachable from the shop PC only again: **Control Center > Settings > Shop network > This computer
only**. On the second PC, the trusted certificate can stay (it is IntraForge's own, valid only for this shop PC's
addresses); to remove it, run `certmgr.msc` > *Trusted Root Certification Authorities > Certificates* and delete the
IntraForge entry.

## What to send back

A list like this is all that is needed:

```
1.1 Pass
1.3 Fail - "This site can't be reached" with the name; the number works
3.2 Fail - shop name missing on the label (screenshot 3.2.png)
5.2 Pass - came back after about 2 minutes
```
