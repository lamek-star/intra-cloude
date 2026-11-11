#!/usr/bin/env bash
# Finalises an offline investor-demo kit folder: refreshes the scripts and guides from the repository, proves the image
# file is self-sufficient, writes the checksum list the installer verifies, and makes one transfer package.
#
#   scripts/demo-kit/package-demo-kit.sh <kit-folder>
#
# Cheap and re-runnable (seconds): build-demo-kit.sh calls it as its last step, and it can be run alone after a
# change to the scripts or the guide. It changes nothing about the demo business, the .env or the backups.
# Output, next to the folder:  IntraForge-Demo-Kit-<version>.zip  and  IntraForge-Demo-Kit-<version>.zip.sha256
set -euo pipefail
export MSYS_NO_PATHCONV=1

KIT="${1:?kit folder}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/../.." && pwd)"
KIT="$(cd "$KIT" && pwd)"
IMAGES_TAR="images/intraforge-demo-images.tar"

for required in .env docker-compose.yml VERSION infrastructure/proxy/Caddyfile "$IMAGES_TAR"; do
  [ -f "$KIT/$required" ] || { echo "not a complete kit folder: $required is missing" >&2; exit 1; }
done
ls "$KIT/backups/"control_db_* "$KIT/backups/"tenant_db_* "$KIT/backups/"object_storage_* >/dev/null

echo "== refresh the scripts and guides from the repository"
cp "$HERE/template/"*.yml "$HERE/template/"*.ps1 "$KIT/"
cp "$HERE/template/README.txt" "$KIT/README.txt"
cp "$REPO/docs/INVESTOR_DEMO.md" "$KIT/INVESTOR_DEMO_SCRIPT.md"

echo "== every image the compose file names must be inside the image file"
manifest_tags="$( cd "$KIT/images" && tar -xOf intraforge-demo-images.tar manifest.json )"
missing=0
for image in $(grep -E '^[[:space:]]+image:' "$KIT/docker-compose.yml" | awk '{print $2}' | sort -u); do
  if printf '%s' "$manifest_tags" | grep -q "\"$image\""; then echo "   ok       $image"
  else echo "   MISSING  $image" >&2; missing=1; fi
done
[ "$missing" -eq 0 ] || { echo "the image file does not contain every image the compose file uses" >&2; exit 1; }

echo "== write SHA256SUMS.txt (checked by Install-IntraForgeDemo.ps1 before anything is installed)"
( cd "$KIT" && sha256sum --binary .env VERSION docker-compose.yml infrastructure/proxy/Caddyfile "$IMAGES_TAR" backups/* \
    > SHA256SUMS.txt )
sed 's/^\([0-9a-f]\{12\}\)[0-9a-f]*/\1.../' "$KIT/SHA256SUMS.txt" | sed 's/^/   /'

echo "== make the transfer package"
VERSION="$(tr -d '\r\n' < "$KIT/VERSION")"
ZIP="$(dirname "$KIT")/IntraForge-Demo-Kit-$VERSION.zip"
rm -f "$ZIP" "$ZIP.sha256"
# Windows' own bsdtar writes a normal zip (forward-slash paths, dotfiles included); GNU tar cannot write zips.
/c/Windows/System32/tar.exe -a -c -f "$(cygpath -m "$ZIP")" -C "$(cygpath -m "$KIT")" .
( cd "$(dirname "$ZIP")" && sha256sum --binary "$(basename "$ZIP")" > "$(basename "$ZIP").sha256" )
count="$(/c/Windows/System32/tar.exe -tf "$(cygpath -m "$ZIP")" | grep -c '')"
/c/Windows/System32/tar.exe -tf "$(cygpath -m "$ZIP")" | grep -qx '\./\.env\|\.env' || { echo "the package does not contain .env" >&2; exit 1; }

echo
echo "Kit folder : $KIT"
echo "Package    : $ZIP  ($(du -h "$ZIP" | cut -f1), $count entries, includes .env)"
echo "Checksum   : $(cut -d' ' -f1 "$ZIP.sha256")"
