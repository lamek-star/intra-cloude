// /uipreview=<screen>: shows one Setup screen with sample data, for screenshots and documentation. Installs nothing.
using System;

sealed partial class SetupForm
{
    void FillPreview(string which)
    {
        productVersion = "1.5.2"; incomingVersion = "1.5.2";
        pc = new PcReport { Windows = "Windows 11 Pro", Memory = "16 GB memory", Disk = "214 GB free", Virtualization = "Virtualization on" };
        string[] log = {
            "==> Checking this computer", "Windows 11 Pro (build 22631), 64-bit", "==> Loading the images from the kit (no download)",
            "Loaded image: intraforge-shop-backend:1.5.2", "Loaded image: intraforge-shop-frontend:1.5.2", "==> Starting the databases and storage",
            "Error response from daemon: Ports are not available: listen tcp 127.0.0.1:8443: bind: address already in use",
            @"Installing IntraForge failed. Details: C:\IntraForgeData\logs\setup.log" };
        switch (which)
        {
            case "choose": Go(Page.Choose); break;
            case "blocked":
                pc.Blocked = true; pc.Virtualization = "Virtualization off";
                pc.Problems.Add("Virtualization is switched OFF in this PC's BIOS/UEFI, so Docker Desktop (and IntraForge) cannot run. To fix it (about 5 minutes): restart the PC and open its BIOS/UEFI setup (press Del, F2, F10, F12 or Esc while it starts), set 'Intel Virtualization Technology' / 'VT-x' to Enabled, save and exit, then run this Setup again.");
                Go(Page.Choose); break;
            case "upgrade":
                installed = new Installed { Complete = true, Version = "1.5.1" };
                Go(Page.Upgrade); break;
            case "installed":
                installed = new Installed { Complete = true, Version = "1.5.2" };
                Go(Page.Installed); break;
            case "install":
                run = new InstallRun(InstallRun.Kind.Install, options, null);
                run.PreviewState(4, 12 / 19f, 12, 19, -1, log);
                Go(Page.Working); break;
            case "finish":
                options.BackupTime = "19:00";
                run = new InstallRun(InstallRun.Kind.Install, options, null);
                run.PreviewState(7, -1, 0, 0, 0);
                run.Address = "https://localhost:8443";
                Go(Page.Finish); break;
            case "restart":
                run = new InstallRun(InstallRun.Kind.Install, options, null);
                run.PreviewState(2, -1, 0, 0, 3010);
                run.FailureMessage = "to finish switching on the Windows parts Docker needs.";
                Go(Page.Restart); break;
            case "failed":
                run = new InstallRun(InstallRun.Kind.Install, options, null);
                run.PreviewState(5, -1, 0, 0, 1, log);
                Go(Page.Failed); break;
            default: Go(Page.Choose); break;
        }
    }
}
