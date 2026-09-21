#!/usr/bin/env bash
# Assembles the ONE-FOLDER "full install" for the shop PC:
#   IntraForge-Setup.exe  (the kit zip wrapped by build-setup-exe.sh)
#   prerequisites/Docker Desktop Installer.exe  (optional; NOT redistributable, only for the owner's own PC)
#   READ ME FIRST.txt, CHECKSUMS.txt
#
#   scripts/shop-kit/package-full-install.sh <kit.zip> <output-folder> ["Docker Desktop Installer.exe"]
set -euo pipefail
export MSYS_NO_PATHCONV=1

ZIP="${1:?kit zip}"; OUT="${2:?output folder}"; DOCKER="${3:-}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
mkdir -p "$OUT/prerequisites"; OUT="$(cd "$OUT" && pwd)"

bash "$HERE/build-setup-exe.sh" "$ZIP" "$OUT/IntraForge-Setup.exe" >/dev/null
rm -f "$OUT/IntraForge-Setup.exe.sha256"
cp "$HERE/full-install-readme.txt" "$OUT/READ ME FIRST.txt"
if [ -n "$DOCKER" ]; then cp "$DOCKER" "$OUT/prerequisites/Docker Desktop Installer.exe"; fi

{
  echo "IntraForge full install -- checksums (SHA-256)"
  echo
  ( cd "$OUT" && sha256sum --binary IntraForge-Setup.exe )
  if [ -f "$OUT/prerequisites/Docker Desktop Installer.exe" ]; then
    ( cd "$OUT" && sha256sum --binary "prerequisites/Docker Desktop Installer.exe" )
    env -u PSModulePath powershell.exe -NoProfile -Command "\$f='$(cygpath -w "$OUT/prerequisites/Docker Desktop Installer.exe")'; \$s=Get-AuthenticodeSignature \$f; 'Docker installer: version ' + (Get-Item \$f).VersionInfo.ProductVersion + ', signature ' + \$s.Status + ', signed by ' + (\$s.SignerCertificate.Subject -split ',')[0]" | tr -d '\r'
  fi
  echo
  echo "IntraForge-Setup.exe contains the shop kit zip below; its own first check is this checksum."
  echo "  $(tr -d '\r\n' < "${ZIP}.sha256" | cut -d' ' -f1)  $(basename "$ZIP")"
  echo
  echo "Verify (PowerShell):  Get-FileHash .\\IntraForge-Setup.exe -Algorithm SHA256"
} > "$OUT/CHECKSUMS.txt"
cat "$OUT/CHECKSUMS.txt"
echo; du -sh "$OUT" | cut -f1 | sed 's/^/full-install folder size: /'
