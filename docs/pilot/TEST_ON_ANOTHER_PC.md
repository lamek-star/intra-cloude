# Testing the IntraForge installer on another (clean) PC

**Goal:** prove that `IntraForge-Setup-Complete.exe` installs and runs on a PC that has nothing of ours on it, and that your data
survives a restart. This is the test the development PC could not do. Take notes as you go (a table to fill in is at the end);
**a photo of any error screen is the most useful thing you can send back.**

**You need:** the single file `IntraForge-Setup-Complete.exe` (1.2 GB) on a USB drive formatted NTFS or exFAT (a USB 3 stick copies
it in a couple of minutes), the test PC, about 45 minutes, and someone who can approve Windows administrator prompts.

## 1. Check the PC first (2 minutes)

Press **Win+R**, type `winver`, Enter, and write down the Windows version. Then open **Task Manager** (Ctrl+Shift+Esc) >
**Performance** > **CPU** and read the bottom-right:

| What you see | Meaning |
| --- | --- |
| **Virtualization: Enabled** | Good. |
| **Virtualization: Disabled** | Switch it on in the BIOS first: restart, press Del / F2 / F10 / F12 / Esc while it starts, find **Intel Virtualization Technology (VT-x)** or **SVM Mode** (AMD), set **Enabled**, save, start Windows. **This is what stopped the first test PC** ("Virtualization support not detected"). |
| The line is missing, or the PC is a virtual machine | Use a physical PC, or enable nested virtualization for the VM. |

Also: **Windows 10 22H2 or Windows 11, 64-bit; at least 8 GB memory; at least 10 GB free on C:**; you are signed in as an
**administrator**. Setup checks all of this itself and tells you, but knowing first saves time.

## 2. Two phases: internet ON for Docker, OFF for IntraForge

Docker Desktop's own installer may need to switch on Windows features and, on some PCs, fetch Windows' WSL component. Whether it
can do that **without internet** is not yet known. So the first test has two phases; write down what happens:

* **Phase A (internet ON):** run Setup and let it install Docker Desktop (steps 3-4). Note whether Docker's installer asked for
  or downloaded anything.
* **Phase B (internet OFF):** once Docker Desktop says **Engine running**, switch the internet off (Wi-Fi off / unplug the cable /
  airplane mode) **before** IntraForge is installed, and carry on from step 5. Everything from there must work offline.

If you have a **second** clean PC, do the whole thing offline from the start and record where it needed the internet.

## 3. Start Setup

1. Copy `IntraForge-Setup-Complete.exe` to the test PC (Desktop is fine).
2. Optional integrity check (PowerShell): `Get-FileHash "$env:USERPROFILE\Desktop\IntraForge-Setup-Complete.exe"` and compare with the
   value in the `.sha256` file next to it.
3. **Double-click it.** Windows will say **"Windows protected your PC / Unknown publisher"** (it is not code-signed): click
   **More info**, then **Run anyway**.
4. A black window opens. The first block is **"Checking this PC"**. Every line should start with **[OK]** (or a yellow **[!]**
   note). A red **[X]** means Setup stopped on purpose; it prints exactly how to fix it, e.g. the BIOS steps. **Photograph it.**
   (To only see this report without installing, open Command Prompt and run `IntraForge-Setup-Complete.exe /check`.)
5. It checks itself ("complete, checksum matches" twice), then asks you to press **Enter** to install.

## 4. Docker Desktop (only if the PC does not have it)

Setup says "Docker Desktop is not installed", prepares its copy, says **"signed by Docker Inc"**, and asks for Enter.
Press Enter, **allow the administrator prompt**, keep **"Use WSL 2"** ticked, finish Docker's installer. If it asks to
**restart Windows: restart, then double-click `IntraForge-Setup-Complete.exe` again** (it carries on from where it stopped).
Open Docker Desktop once, accept its terms if asked, and wait until it says **Engine running** (bottom left). If instead it shows
an error such as *"Virtualization support not detected"* or *"WSL needs updating"*, **photograph it and stop**: that is the
result of the test.

## 5. IntraForge installs (about 2 minutes)

Setup prints its steps and ends with **"IntraForge is installed and running"** and opens the browser. Accept the certificate
warning (**Advanced > continue**). Then:

1. **Create account** (this is the administrator), create the company, open the **Application Gallery**, install
   **Spare Parts / Inventory & Sales**.
2. Quick real-work check (5 minutes): add a warehouse, a supplier and one product with a part number; **Receive 10**; **Sell 2**;
   the stock must show **8** and a **sales document** must exist. Search the part number typed two different ways
   (`04465-0K290` and `044650k290`).
3. Copy **`C:\IntraForgeData\keys\intraforge-keys.env`** to a USB drive (this is the step that protects you after a PC loss).

## 6. Backup

Double-click **IntraForge Backup Now** on the desktop. It should end with "backup completed". Look in
`C:\IntraForgeData\backups`: three files and `LATEST-BACKUP.txt`. Then **IntraForge Backup to USB** with a USB drive plugged in.

## 7. The restart test (the most important one)

1. Restart Windows. **Do not open Docker or IntraForge yourself.** Sign in and wait **2 minutes**.
2. Double-click **Open IntraForge**. Sign in: the product, the stock of 8 and the sales document must still be there.
3. Double-click **IntraForge Status** and keep the file it saves (`C:\IntraForgeData\logs\status-*.txt`). It should say
   *IntraForge: HEALTHY* and *Starts at sign-in: yes*.
4. With the internet still **off**: search, receive 1, sell 1. Everything must work.

## 8. What to send back

* A photo/screenshot of **any** red or unexpected screen (Setup window, Docker error).
* From `C:\IntraForgeData\logs`: the newest `status-*.txt`, `shop.log` and `backup.log` (they contain no passwords or keys).
* The table below, filled in.

| Check | Expected | Your result (pass / fail / notes) |
| --- | --- | --- |
| Windows version, virtualization enabled | Win 10 22H2+/11, "Enabled" | |
| Setup "Checking this PC" | all [OK] | |
| Docker's installer: did it need the internet? | (unknown: record it) | |
| Docker Desktop reaches "Engine running" | yes | |
| IntraForge installs, browser opens | "installed and running" | |
| Create account, company, install Spare Parts | works | |
| Receive 10, sell 2, stock 8, sales document | works | |
| Backup Now, three files + `LATEST-BACKUP.txt` | works | |
| Restart Windows, no manual start, data still there | works within ~2 minutes | |
| Works with the internet off | works | |
| Anything slow (> 2 s)? what and when | note | |

## 9. Putting the test PC back

Docker Desktop stays (uninstall it from Settings > Apps if you want it gone). To remove IntraForge and its data, open PowerShell and
run: `powershell -ExecutionPolicy Bypass -File C:\IntraForge\Uninstall-IntraForgeShop.ps1 -DeleteData` (it asks you to type
`YES`, then `DELETE-MY-SHOP-DATA`). Backups in `C:\IntraForgeData` are never deleted by it.

## If something fails: what it usually means

| You see | Meaning and next step |
| --- | --- |
| `[X] Virtualization is switched OFF ...` (Setup) or *"Virtualization support not detected"* (Docker) | BIOS setting (step 1). Fix it and run Setup again. If the PC has no such setting or is a virtual machine without nested virtualization, use another PC. |
| "This setup file does not match its checksum" | The file was damaged while copying. Copy it again. |
| Docker installer finishes but Setup says Docker is not installed yet | Restart Windows, then run Setup again. |
| `The IntraForge installer stopped` right after "Checking this computer" | Read the red line above it; send a photo. |
| IntraForge does not open after a restart | Open Docker Desktop, wait for "Engine running", double-click **Open IntraForge**; then run **IntraForge Status** and send the file. |
