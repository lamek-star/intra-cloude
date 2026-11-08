#!/usr/bin/env bash
# Builds the IntraForge Local Edition own-shop pilot kit -- run ONCE, ONLINE, on the build machine (Docker Desktop running).
#
#   scripts/shop-kit/build-shop-kit.sh <output-folder>
#
# Produces <output-folder> (the kit) and, next to it, IntraForge-Local-<KIT_VERSION>-<HEAD>.zip + .sha256.
# The kit is built from COMMITTED source only: IntraForge from `git archive HEAD`, the Spare Parts service application
# (ADR-0018) from `git archive` of its own repository (SPAREPARTS_REPO / SPAREPARTS_REF, see build-spareparts-image.sh).
# It contains every image the shop needs (nothing is downloaded on the shop PC), a pinned MinIO, the IntraForge Control
# Center (a native Windows program, compiled here with the C# compiler that ships with Windows), the install / start /
# backup / restore / status / upgrade / uninstall scripts, and an offline manifest listing every component with its
# checksum. It contains NO secrets and NO demo data: the shop PC generates its own keys at install time.
#
# KIT_VERSION  the release version of this kit (default 1.1.0): what the shop PC reports and what the installer's file
#              name carries. The repository's VERSION file stays the IntraForge product version.
set -euo pipefail
export MSYS_NO_PATHCONV=1

OUT="${1:?output folder}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/../.." && pwd)"
mkdir -p "$OUT"; OUT="$(cd "$OUT" && pwd)"
OUTW="$(cygpath -m "$OUT")"; REPOW="$(cygpath -m "$REPO")"
cd "$REPO"

echo "== 1/6 build from the COMMITTED source (HEAD), never from a working tree that may hold unfinished work"
DIRTY="$(git status --porcelain -- apps infrastructure docker-compose.yml VERSION)"
if [ -n "$DIRTY" ]; then
  echo "   note: these uncommitted changes are NOT in this build (it is built from HEAD):"; echo "$DIRTY" | sed 's/^/     /'
fi
# The kit's own scripts and the Control Center are taken from this folder: they must be committed, so that the recorded
# HEAD describes exactly what the shop PC runs.
KIT_DIRTY="$(git status --porcelain -- scripts/shop-kit)"
[ -z "$KIT_DIRTY" ] || { echo "scripts/shop-kit has uncommitted changes; commit them first:" >&2; echo "$KIT_DIRTY" >&2; exit 1; }
EXPORT="$(mktemp -d)"
git archive HEAD apps infrastructure docker-compose.yml VERSION | tar -x -C "$EXPORT"
EXPORTW="$(cygpath -m "$EXPORT")"
HEAD_FULL="$(git rev-parse HEAD)"; HEAD_SHORT="$(git rev-parse --short=9 HEAD)"
VERSION="$(tr -d '\r\n' < VERSION)"
KIT_VERSION="${KIT_VERSION:-1.1.0}"
[[ "$KIT_VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || { echo "KIT_VERSION must look like 1.2.3" >&2; exit 1; }
TAG="$KIT_VERSION-$HEAD_SHORT"
BUILT_UTC="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "   HEAD $HEAD_SHORT  kit $KIT_VERSION  product $VERSION  tag $TAG"

echo "== 2/6 build the images from source, and the Control Center"
docker build -q -t "intraforge-shop-backend:$TAG" "$EXPORTW/apps/backend" >/dev/null
docker build -q -t "intraforge-shop-frontend:$TAG" "$EXPORTW/apps/frontend" >/dev/null

# The service applications (ADR-0018: Spare Parts, its Pharmacy edition, IntraForge Pay) and the hosted-app Node.js
# runtime (ADR-0020) are separate projects whose source is not in this repository. CARRY_APPS_FROM=<earlier kit tag>
# takes them UNCHANGED from that kit's images (already on this machine, e.g. loaded from its images tar) and records
# each image id, so the shop runs exactly what that kit ran. With no tag the build stops: nothing is rebuilt from a
# guess. (build-spareparts-image.sh builds Spare Parts alone from its repository, for when that source is available.)
CARRY_APPS_FROM="${CARRY_APPS_FROM:?set CARRY_APPS_FROM to the earlier kit tag whose app images to carry over, e.g. 1.4.0-dbf44f593}"
# PAY_IMAGE=<image> + PAY_SOURCE=<repository, branch and commit> take IntraForge Pay from a newer build instead of
# carrying it over (for example its refunds and cashback release); both are required together, and recorded.
if [ -n "${PAY_IMAGE:-}" ]; then
  [ -n "${PAY_SOURCE:-}" ] || { echo "PAY_IMAGE needs PAY_SOURCE (where that Pay image was built from)" >&2; exit 1; }
  docker image inspect "$PAY_IMAGE" >/dev/null 2>&1 || { echo "$PAY_IMAGE is not on this machine" >&2; exit 1; }
fi
CARRIED=()
for name in intraforge-shop-spareparts intraforge-shop-pharmacy intraforge-shop-pay intraforge-runtime-node; do
  source_ref="$name:$CARRY_APPS_FROM"
  [ "$name" = intraforge-shop-pay ] && [ -n "${PAY_IMAGE:-}" ] && source_ref="$PAY_IMAGE"
  docker image inspect "$source_ref" >/dev/null 2>&1 || { echo "$source_ref is not on this machine" >&2; exit 1; }
  docker tag "$source_ref" "$name:$TAG"
  if [ "$source_ref" = "$name:$CARRY_APPS_FROM" ]; then
    CARRIED+=("$name $(docker image inspect "$name:$TAG" --format '{{.Id}}')")
    echo "   carried over unchanged: $source_ref -> $name:$TAG"
  else
    echo "   from a newer build: $source_ref ($PAY_SOURCE) -> $name:$TAG"
  fi
done
export CARRY_APPS_FROM PAY_SOURCE="${PAY_SOURCE:-}"
# The Cloudflare Tunnel connector: the exact release the compose template names (RUNNER_TUNNEL_IMAGE).
TUNNEL_IMAGE="$(sed -n 's/^ *RUNNER_TUNNEL_IMAGE: *//p' "$HERE/template/docker-compose.yml" | tr -d '\r')"
docker image inspect "$TUNNEL_IMAGE" >/dev/null 2>&1 || { echo "$TUNNEL_IMAGE is not on this machine (docker pull it once)" >&2; exit 1; }

CSC="/c/Windows/Microsoft.NET/Framework64/v4.0.30319/csc.exe"
[ -x "$CSC" ] || { echo "the .NET Framework C# compiler was not found at $CSC" >&2; exit 1; }
CC_TMP="$(mktemp -d)"
"$CSC" -nologo -codepage:65001 -target:winexe -optimize+ -out:"$(cygpath -w "$CC_TMP/IntraForgeControlCenter.exe")" \
  -win32icon:"$(cygpath -w "$REPO/installer/assets/icon.ico")" -win32manifest:"$(cygpath -w "$HERE/control-center/app.manifest")" \
  -reference:System.Windows.Forms.dll -reference:System.Drawing.dll -reference:System.Management.dll \
  -reference:System.Web.Extensions.dll -reference:System.IO.Compression.dll -reference:System.IO.Compression.FileSystem.dll \
  "$(cygpath -w "$HERE/control-center/ControlCenter.cs")"
echo "   control center compiled"

echo "== 3/6 pin MinIO to the exact tested release"
# MINIO_TAG=<release> keeps the release the shop already runs (an upgrade must not silently change the object store);
# without it the newest local minio/minio:latest is pinned, as before.
if [ -z "${MINIO_TAG:-}" ]; then
  MINIO_TAG="$(docker image inspect minio/minio:latest --format '{{index .Config.Labels "version"}}')"
  [ -n "$MINIO_TAG" ] || { echo "cannot read the MinIO release label" >&2; exit 1; }
  docker tag minio/minio:latest "minio/minio:$MINIO_TAG"
fi
docker image inspect "minio/minio:$MINIO_TAG" >/dev/null 2>&1 || { echo "minio/minio:$MINIO_TAG is not on this machine" >&2; exit 1; }
echo "   minio/minio:$MINIO_TAG"

echo "== 4/6 assemble the kit"
rm -rf "$OUT/images" "$OUT/infrastructure"; mkdir -p "$OUT/images" "$OUT/infrastructure/proxy"
sed "s/@TAG@/$TAG/g; s/@MINIO_TAG@/$MINIO_TAG/g" "$HERE/template/docker-compose.yml" > "$OUT/docker-compose.yml"
cp "$HERE/template/"*.ps1 "$HERE/template/README.txt" "$OUT/"
cp "$CC_TMP/IntraForgeControlCenter.exe" "$OUT/IntraForgeControlCenter.exe"
cp "$EXPORT/infrastructure/proxy/Caddyfile" "$OUT/infrastructure/proxy/Caddyfile"
printf '%s\n' "$KIT_VERSION" > "$OUT/VERSION"
cp "$REPO/docs/OWN_SHOP_PILOT_QUICKSTART.md" "$OUT/OWN_SHOP_PILOT_QUICKSTART.md"
cp "$REPO/docs/LOCAL_EDITION_PILOT.md" "$OUT/LOCAL_EDITION_PILOT.md"
cp "$REPO/docs/pilot/PILOT_LOG.md" "$OUT/PILOT_LOG.md"
rm -f "$OUT/.env" "$OUT/DEMO_LOGINS.txt"
IMAGES=("intraforge-shop-backend:$TAG" "intraforge-shop-frontend:$TAG" "intraforge-shop-spareparts:$TAG" "intraforge-shop-pharmacy:$TAG"
  "intraforge-shop-pay:$TAG" "intraforge-runtime-node:$TAG" "$TUNNEL_IMAGE" "postgres:18" "valkey/valkey:9-alpine" "minio/minio:$MINIO_TAG" "caddy:2-alpine")
docker save -o "$OUTW/images/intraforge-shop-images.tar" "${IMAGES[@]}"
{
  echo "IntraForge Local Edition -- shop kit $KIT_VERSION"
  echo "Source HEAD:   $HEAD_FULL"
  echo "Kit version:   $KIT_VERSION"
  echo "Product ver:   $VERSION (repository VERSION)"
  echo "Built (UTC):   $BUILT_UTC"
  echo "Architecture:  linux/amd64 containers on Windows (Docker Desktop, WSL2 backend)"
  echo "Docker build host: $(docker version --format 'Docker {{.Server.Version}}')"
  echo "Apps carried over unchanged from kit $CARRY_APPS_FROM (their source is not in this repository):"
  for line in "${CARRIED[@]}"; do echo "               $line"; done
  if [ -n "$PAY_SOURCE" ]; then
    echo "Pay:           IntraForge Pay from $PAY_SOURCE, image $(docker image inspect "intraforge-shop-pay:$TAG" --format '{{.Id}}')"
  fi
  echo "Tunnel:      $TUNNEL_IMAGE (Cloudflare Tunnel connector, used only when the Super Administrator switches internet access on)"
  echo "Control Center: IntraForgeControlCenter.exe (.NET Framework 4.x) sha256 $(sha256sum "$CC_TMP/IntraForgeControlCenter.exe" | cut -d' ' -f1)"
} > "$OUT/BUILD_INFO.txt"

echo "== 5/6 offline manifest and checksums"
python - "$OUTW" "$HEAD_FULL" "$KIT_VERSION (product $VERSION)" "$BUILT_UTC" "${IMAGES[@]}" <<'PY'
import json, os, pathlib, subprocess, sys
out = pathlib.Path(sys.argv[1]); head, version, built = sys.argv[2:5]; images = sys.argv[5:]
def inspect(ref, fmt):
    return subprocess.run(["docker", "image", "inspect", ref, "--format", fmt], capture_output=True, text=True, check=True).stdout.strip()
purpose = {
    "intraforge-shop-backend": ("IntraForge backend, workers and scheduler (Django, Celery), migrations", f"built from source at {head[:9]}", "project"),
    "intraforge-shop-frontend": ("IntraForge web interface (Next.js)", f"built from source at {head[:9]}", "project"),
    "intraforge-shop-spareparts": ("Spare Parts / Inventory & Sales service application (Next.js), served inside IntraForge at /apps/spare-parts/ (no port of its own)",
        "separate project, image carried over unchanged from kit " + os.environ.get("CARRY_APPS_FROM", "?"), "project (its npm dependencies keep their own licences)"),
    "intraforge-shop-pharmacy": ("Pharmacy: the Spare Parts engine built as its pharmacy edition, served at /apps/pharmacy/",
        "separate project, image carried over unchanged from kit " + os.environ.get("CARRY_APPS_FROM", "?"), "project (its npm dependencies keep their own licences)"),
    "intraforge-shop-pay": ("IntraForge Pay service application (simulated IF Credits), served at /apps/pay-N/",
        ("separate project, " + os.environ["PAY_SOURCE"]) if os.environ.get("PAY_SOURCE") else
        ("separate project, image carried over unchanged from kit " + os.environ.get("CARRY_APPS_FROM", "?")),
        "project (its Python dependencies keep their own licences)"),
    "intraforge-runtime-node": ("Node.js runtime the app runner starts hosted Node.js apps in (ADR-0020)",
        "image carried over unchanged from kit " + os.environ.get("CARRY_APPS_FROM", "?"), "project (Node.js: MIT)"),
    "cloudflare/cloudflared": ("Cloudflare Tunnel connector, started only when the Super Administrator switches internet access on",
        "Docker Hub cloudflare/cloudflared, pinned release", "Apache-2.0"),
    "postgres": ("Databases (company data and business records)", "Docker official image, postgres:18", "PostgreSQL licence"),
    "valkey/valkey": ("Cache and job queue", "Docker Hub valkey/valkey", "BSD-3-Clause"),
    "minio/minio": ("Stored files (object storage), PINNED to the tested release", "Docker Hub minio/minio", "AGPL-3.0 (commercial-distribution decision OPEN, see THIRD_PARTY_LICENSES.md)"),
    "caddy": ("Local web server / HTTPS proxy", "Docker official image, caddy:2-alpine", "Apache-2.0"),
}
rows = []
for ref in images:
    name = ref.rsplit(":", 1)[0]
    what, source, licence = purpose[name]
    digests = inspect(ref, "{{json .RepoDigests}}")
    rows.append({
        "image": ref, "image_id": inspect(ref, "{{.Id}}"), "repo_digests": json.loads(digests) if digests not in ("", "null") else [],
        "created": inspect(ref, "{{.Created}}"), "size_bytes": int(inspect(ref, "{{.Size}}")),
        "purpose": what, "source": source, "licence": licence, "bundled": True,
        "location": "images/intraforge-shop-images.tar",
    })
prereq = [
    {"component": "Windows 10 22H2 (build 19045) or Windows 11, 64-bit", "class": "B: provided by Windows", "checked_by": "Install-IntraForgeShop.ps1 (blocking)"},
    {"component": "Virtualization + WSL2 (Windows features 'Virtual Machine Platform' / 'Windows Subsystem for Linux')", "class": "C: Windows feature; enabled by the Docker Desktop installer (needs administrator, may need one restart)", "checked_by": "Docker Desktop installer; Install-IntraForgeShop.ps1 checks that the Docker engine answers"},
    {"component": "Docker Desktop (Windows, WSL2 backend)", "class": "D: NOT bundled (its licence does not allow redistribution in this kit); download once from docker.com on any connected PC and carry the installer; tested build recorded below", "checked_by": "Install-IntraForgeShop.ps1 (blocking if missing)"},
    {"component": "A web browser (Chrome or Edge)", "class": "B: provided by Windows / already on the PC", "checked_by": "-"},
    {"component": "Memory 8 GB, free disk 10 GB", "class": "sizing evidence: demo containers 994 MiB idle; scale-qualified at 5,000 products", "checked_by": "Install-IntraForgeShop.ps1 (warning; blocking under 3 GB disk)"},
]
manifest = {
    "product": "IntraForge Local Edition -- shop kit", "product_version": version, "source_head": head, "built_utc": built,
    "docker_desktop_tested": subprocess.run(["docker", "version", "--format", "{{.Server.Version}}"], capture_output=True, text=True).stdout.strip(),
    "network_needed_at_install": False, "images": rows, "prerequisites": prereq,
    "not_used_at_install": ["npm/pnpm", "pip", "docker pull", "online WSL download", "GitHub", "Microsoft Store", "any package manager"],
}
(out / "OFFLINE_MANIFEST.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8", newline="\n")
lines = ["IntraForge Local Edition -- shop kit -- OFFLINE MANIFEST", f"Source HEAD {head}   version {version}   built {built}", "",
         "Bundled in this kit (nothing is downloaded during installation):"]
for r in rows:
    lines += [f"  {r['image']}", f"      {r['purpose']}", f"      source: {r['source']}   licence: {r['licence']}", f"      id: {r['image_id']}   size: {r['size_bytes']:,} bytes"]
    for d in r["repo_digests"]:
        lines.append(f"      digest: {d}")
lines += ["", "Prerequisites of the PC (not in this kit unless stated):"]
for p in prereq:
    lines += [f"  - {p['component']}", f"      {p['class']}", f"      checked by: {p['checked_by']}"]
lines += ["", f"Docker Desktop / engine version this kit was built and rehearsed with: {manifest['docker_desktop_tested']}",
          "Never used during installation: " + ", ".join(manifest["not_used_at_install"]) + "."]
(out / "OFFLINE_MANIFEST.txt").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
PY
( cd "$OUT" && sha256sum --binary VERSION BUILD_INFO.txt IntraForgeControlCenter.exe docker-compose.yml infrastructure/proxy/Caddyfile OFFLINE_MANIFEST.json images/intraforge-shop-images.tar > SHA256SUMS.txt )

rm -rf "$EXPORT" "$CC_TMP"

echo "== 6/6 package"
ZIP="$(dirname "$OUT")/IntraForge-Local-$KIT_VERSION-$HEAD_SHORT.zip"
rm -f "$ZIP" "$ZIP.sha256"
# Plain entry names (VERSION, images/...): Windows Explorer's "Extract All" refuses a zip whose names start with "./",
# which is what `tar -a -c -C <dir> .` writes.
python - "$OUTW" "$(cygpath -m "$ZIP")" <<'PY'
import os, sys, zipfile
src, dst = sys.argv[1:3]
with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
    for root, dirs, files in os.walk(src):
        dirs.sort()
        for name in sorted(files):
            path = os.path.join(root, name)
            z.write(path, os.path.relpath(path, src).replace(os.sep, "/"))
PY
( cd "$(dirname "$ZIP")" && sha256sum --binary "$(basename "$ZIP")" > "$(basename "$ZIP").sha256" )
echo
echo "Kit folder : $OUT"
echo "Package    : $ZIP  ($(du -h "$ZIP" | cut -f1))"
echo "SHA-256    : $(cut -d' ' -f1 "$ZIP.sha256")"
echo "HEAD       : $HEAD_FULL"
echo "Built      : $BUILT_UTC"
