# Testing the IntraForge installer on another (clean) PC

**Goal:** prove that `IntraForge-Setup-Complete.exe` installs and runs on a PC that has nothing of ours on it (no WSL, no Docker),
with **no internet**, and that your data survives a restart. It has been proven in a clean Windows 11 virtual machine (see
[../implementation/OWN_SHOP_PILOT_READINESS.md](../implementation/OWN_SHOP_PILOT_READINESS.md)); a real PC is the test that is
still missing. Take notes as you go; **a photo of any error screen is the most useful thing you can send back.**

**You need:** the single file `IntraForge-Setup-Complete.exe` (about 1.4 GB) on a USB drive formatted NTFS or exFAT, the test PC,
about 45 minutes, and someone who can approve Windows administrator prompts (two of them).

## 1. Check the PC first (2 minutes)

Press **Win+R**, type `winver`, Enter, and write down the Windows version. Then open **Task Manager** (Ctrl+Shift+Esc) >
**Performance** > **CPU** and read the bottom-right:

| What you see | Meaning |
| --- | --- |
| **Virtualization: Enabled** | Good. |
| **Virtualization: Disabled** | Switch it on in the BIOS first: restart, press Del / F2 / F10 / F12 / Esc while it starts, find **Intel Virtualization Technology (VT-x)** or **SVM Mode** (AMD), set **Enabled**, save, start Windows. This is what stopped the first test PC. |
| The line is missing, or the PC is a virtual machine | Use a physical PC, or turn on nested virtualization for the VM in its host. |

Also: **Windows 10 22H2 or Windows 11, 64-bit; at least 8 GB memory; at least 10 GB free on C:**; you are an **administrator**.
Setup checks all of this itself and tells you.

## 2. Internet: switch it OFF

Everything needed is inside the file: the IntraForge program, the WSL package and Docker Desktop. Windows' own features are switched
on from Windows itself, without downloading. So do the whole test **with the internet off** (Wi-Fi off / cable out / airplane mode)
from before you start. If something needs the internet after all, that is a defect: write down exactly which step.

## 3. Start Setup

1. Copy `IntraForge-Setup-Complete.exe` to the test PC (Desktop is fine).
2. Optional integrity check (PowerShell): `Get-FileHash "$env:USERPROFILE\Desktop\IntraForge-Setup-Complete.exe"` and compare it with
   the `.sha256` file that came with it. Setup also checks its own three parts.
3. **Double-click it.** Windows says **"Windows protected your PC / Unknown publisher"** (not code-signed): **More info > Run anyway**.
4. The first block is **"Checking this PC"**: every line should start with **[OK]** or a yellow **[!]** note. A red **[X]** means Setup
   stopped on purpose and prints how to fix it. **Photograph it.** (To see only this report: open Command Prompt and run
   `IntraForge-Setup-Complete.exe /check`.)
5. Press **Enter** when asked. It confirms that each part of the file is complete, then unpacks into `C:\IntraForge`.

## 4. What Setup does on a PC with nothing on it

1. **Windows parts (administrator prompt #1, about a minute).** It switches on the Windows features Docker's engine needs and asks to
   **restart** (answer Y). Nothing else happens before the restart.
2. **Restart, then sign in.** Setup **continues by itself** in a window after you sign in (or double-click the file again).
3. **WSL and Docker (administrator prompt #2, about 2 minutes).** It installs the WSL package and Docker Desktop from the copies inside
   the file, after checking that each is signed by Microsoft / Docker Inc.
4. **IntraForge (about 2-3 minutes).** It loads its images, creates this shop's own keys, starts everything and sets up automatic start,
   the daily backup and the desktop shortcuts. It ends with **"IntraForge is installed and running"**.

If Setup stops with red text at any point, fix the cause and run the file again: it **carries on from where it stopped** (only one
Setup runs at a time). Its log is `C:\IntraForgeData\logs\setup.log`.

## 5. Use it

0. The browser opens the **Spare Parts application** (`http://127.0.0.1:3000/`): press **Enter demo workspace**; you should see a dashboard
   (stock valuation, recent sales, four warehouses) and be able to open Catalogue, Inventory, Sales and Reports. There is also an
   **Open Spare Parts** icon on the desktop.

1. Double-click **Open IntraForge** (accept the certificate warning: **Advanced > continue**). **Create account** (the administrator),
   create the company, install **Spare Parts / Inventory & Sales** from the Application Gallery.
2. Real-work check (5 minutes): add a warehouse, a supplier and a product with a part number; **Receive 10**; **Sell 2**; the stock must
   show **8** and a **sales document** must exist. Search the part number typed two ways (`04465-0K290`, `044650k290`).
3. Copy **`C:\IntraForgeData\keys\intraforge-keys.env`** to a USB drive.

## 6. Backup

Double-click **IntraForge Backup Now**. It should end with "backup completed"; `C:\IntraForgeData\backups` then holds three files and
`LATEST-BACKUP.txt`. Then **IntraForge Backup to USB** with a USB drive plugged in.

## 7. The restart test (the most important one)

1. Restart Windows. **Do not open Docker or IntraForge yourself.** Wait **2 minutes** (sign in if asked).
2. Double-click **Open IntraForge**. Sign in: the product, the stock of 8 and the sales document must still be there.
3. Double-click **IntraForge Status** and keep the file it saves (`C:\IntraForgeData\logs\status-*.txt`): *IntraForge: HEALTHY*,
   *Starts at sign-in: yes*.
4. With the internet still **off**: search, receive 1, sell 1.

## 8. What to send back

* A photo/screenshot of **any** red or unexpected screen.
* From `C:\IntraForgeData\logs`: the newest `status-*.txt`, `setup.log`, `shop.log` and `backup.log` (no passwords or keys inside).
* The table below, filled in.

| Check | Expected | Your result (pass / fail / notes) |
| --- | --- | --- |
| Windows version, virtualization enabled | Win 10 22H2+/11, "Enabled" | |
| Setup "Checking this PC" | all [OK] | |
| Windows parts step, restart | works with the internet off | |
| Setup continued by itself after the restart | yes (or: had to double-click again) | |
| WSL + Docker Desktop installed with the internet off | works | |
| IntraForge installs, "installed and running" | works | |
| Spare Parts application opens at http://127.0.0.1:3000/ and shows its dashboard | works | |
| Create account, company, Spare Parts | works | |
| Receive 10, sell 2, stock 8, sales document | works | |
| Backup Now, three files + `LATEST-BACKUP.txt` | works | |
| Restart Windows, no manual start, data still there | works within ~2 minutes | |
| Spare Parts application answers again after the restart | works | |
| Works with the internet off | works | |
| Anything slow (> 2 s)? what and when | note | |

## 9. Putting the test PC back

To remove IntraForge and its data: PowerShell,
`powershell -ExecutionPolicy Bypass -File C:\IntraForge\Uninstall-IntraForgeShop.ps1 -DeleteData` (type `YES`, then
`DELETE-MY-SHOP-DATA`). Backups in `C:\IntraForgeData` are never deleted by it. Docker Desktop and WSL stay (uninstall them from
Settings > Apps if you want them gone).

## If something fails: what it usually means

| You see | Meaning and next step |
| --- | --- |
| `[X] Virtualization is switched OFF ...` | BIOS setting (step 1). Fix it and run Setup again. |
| `[X] ... a virtual machine that does not pass virtualization through` | Turn on nested virtualization for the VM in its host (the message shows how), then run Setup again. |
| "This setup file does not match its checksum" | The file was damaged while copying. Copy it again. |
| "Another Setup is already running" | The run that started by itself after the restart is doing the work. Let it finish. |
| Docker Desktop is installed but never becomes ready (VM only) | Nested virtualization is off for the VM; fix it in the host and run Setup again. |
| IntraForge does not open after a restart | Open Docker Desktop, wait for "Engine running", double-click **Open IntraForge**; then **IntraForge Status**, and send the file. |
