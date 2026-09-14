# Operational & Development Scripts

## Windows qualification VM

`New-QualificationVM.ps1` / `Checkpoint-QualificationVM.ps1` /
`Restore-QualificationVM.ps1` — create and checkpoint a disposable
Hyper-V VM to run `docs/deployment/WINDOWS_QUALIFICATION_MATRIX.md`
against, instead of a real development machine (that matrix is
explicitly destructive: fresh install, deliberately-damaged repair,
uninstall, upgrade-over). Nested virtualization is enabled on the VM's
vCPU because IntraForge's own installer runs WSL2 (itself a lightweight
Hyper-V VM) inside the guest. All three require an elevated PowerShell
session and the Hyper-V Windows feature already enabled.

```powershell
.\scripts\New-QualificationVM.ps1 -Name IntraForge-Win11Pro -IsoPath D:\isos\Win11_24H2.iso
# complete Windows Setup interactively (vmconnect.exe localhost IntraForge-Win11Pro), then:
.\scripts\Checkpoint-QualificationVM.ps1 -Name IntraForge-Win11Pro -CheckpointName clean-post-oobe
# ... run a destructive matrix section, then roll back for the next one:
.\scripts\Restore-QualificationVM.ps1 -Name IntraForge-Win11Pro -CheckpointName clean-post-oobe
```

Not yet implemented: local bootstrap script, backup/restore automation
entry points (implementing `docs/operations/BACKUP_RESTORE.md`), CI
helper scripts.
