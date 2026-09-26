#!/usr/bin/env bash
# Builds the IntraForge Local Edition own-shop pilot kit -- run ONCE, ONLINE, on the build machine (Docker Desktop running).
#
#   scripts/shop-kit/build-shop-kit.sh <output-folder>
#
# Produces <output-folder> (the kit) and, next to it, IntraForge-Local-v1.0-Pilot-<HEAD>.zip + .sha256.
# The kit is built from the CURRENT source (it refuses a dirty application tree so that the recorded HEAD is true),
# contains every image the shop needs (nothing is downloaded on the shop PC), a pinned MinIO, the install / start /
# backup / restore / status / uninstall scripts, and an offline manifest listing every component with its checksum.
# It contains NO secrets and NO demo data: the shop PC generates its own keys at install time.
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
EXPORT="$(mktemp -d)"
git archive HEAD apps infrastructure docker-compose.yml VERSION | tar -x -C "$EXPORT"
EXPORTW="$(cygpath -m "$EXPORT")"
HEAD_FULL="$(git rev-parse HEAD)"; HEAD_SHORT="$(git rev-parse --short=9 HEAD)"
VERSION="$(tr -d '\r\n' < VERSION)"
TAG="1.0-pilot-$HEAD_SHORT"
BUILT_UTC="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "   HEAD $HEAD_SHORT  version $VERSION  tag $TAG"

echo "== 2/6 build the two IntraForge images from source"
docker build -q -t "intraforge-shop-backend:$TAG" "$EXPORTW/apps/backend" >/dev/null
docker build -q -t "intraforge-shop-frontend:$TAG" "$EXPORTW/apps/frontend" >/dev/null

# The spare parts reference application: a SEPARATE project, built from a COPY of its working tree (its own folder is only read;
# its .env* files, auth data, dev certificates and import data are never copied: no secrets belong in an installer).
SPAREPARTS_SRC="${SPAREPARTS_SRC:-$HOME/Documents/intraforge-spareparts-demo}"
[ -d "$SPAREPARTS_SRC" ] || { echo "the spare parts project was not found at $SPAREPARTS_SRC (set SPAREPARTS_SRC)" >&2; exit 1; }
SP_CTX="$(mktemp -d)"
tar -C "$SPAREPARTS_SRC" --exclude=./node_modules --exclude='./.next*' --exclude=./.git --exclude='./.env*' --exclude=./.auth-data \
  --exclude=./.catalogue-import-data --exclude=./.dev-certs --exclude=./test-results --exclude=./playwright-report --exclude='*.tsbuildinfo' -cf - . \
  | tar -C "$SP_CTX" -xf -
[ -z "$(ls -A "$SP_CTX" | grep -E '^\.env' || true)" ] || { echo "an .env file reached the spare parts build context: refusing" >&2; exit 1; }
export SP_COMMIT="$(git --no-optional-locks -C "$(cygpath -m "$SPAREPARTS_SRC")" rev-parse --short=9 HEAD 2>/dev/null || echo unknown)"
export SP_DIRTY="$(git --no-optional-locks -C "$(cygpath -m "$SPAREPARTS_SRC")" status --porcelain 2>/dev/null | wc -l | tr -d ' ')"
export SP_HASH="$(cd "$SP_CTX" && find . -type f -print0 | sort -z | xargs -0 sha256sum | sha256sum | cut -c1-16)"
echo "   spare parts app: commit $SP_COMMIT, $SP_DIRTY uncommitted file(s) included, content hash $SP_HASH"
docker build -q -t "intraforge-shop-spareparts:$TAG" -f "$(cygpath -m "$HERE/spareparts-app/Dockerfile")" "$(cygpath -m "$SP_CTX")" >/dev/null

echo "== 3/6 pin MinIO to the exact tested release"
MINIO_TAG="$(docker image inspect minio/minio:latest --format '{{index .Config.Labels "version"}}')"
[ -n "$MINIO_TAG" ] || { echo "cannot read the MinIO release label" >&2; exit 1; }
docker tag minio/minio:latest "minio/minio:$MINIO_TAG"
echo "   minio/minio:$MINIO_TAG"

echo "== 4/6 assemble the kit"
rm -rf "$OUT/images" "$OUT/infrastructure"; mkdir -p "$OUT/images" "$OUT/infrastructure/proxy"
sed "s/@TAG@/$TAG/g; s/@MINIO_TAG@/$MINIO_TAG/g" "$HERE/template/docker-compose.yml" > "$OUT/docker-compose.yml"
cp "$HERE/template/"*.ps1 "$HERE/template/README.txt" "$OUT/"
cp "$EXPORT/infrastructure/proxy/Caddyfile" "$OUT/infrastructure/proxy/Caddyfile"
cat "$HERE/template/Caddyfile.spareparts" >> "$OUT/infrastructure/proxy/Caddyfile"
cp "$REPO/VERSION" "$OUT/VERSION"
cp "$REPO/docs/OWN_SHOP_PILOT_QUICKSTART.md" "$OUT/OWN_SHOP_PILOT_QUICKSTART.md"
cp "$REPO/docs/LOCAL_EDITION_PILOT.md" "$OUT/LOCAL_EDITION_PILOT.md"
cp "$REPO/docs/pilot/PILOT_LOG.md" "$OUT/PILOT_LOG.md"
rm -f "$OUT/.env" "$OUT/DEMO_LOGINS.txt"
IMAGES=("intraforge-shop-backend:$TAG" "intraforge-shop-frontend:$TAG" "intraforge-shop-spareparts:$TAG" "postgres:18" "valkey/valkey:9-alpine" "minio/minio:$MINIO_TAG" "caddy:2-alpine")
docker save -o "$OUTW/images/intraforge-shop-images.tar" "${IMAGES[@]}"
{
  echo "IntraForge Local Edition v1.0 -- own-shop pilot build"
  echo "Source HEAD:   $HEAD_FULL"
  echo "Product ver:   $VERSION"
  echo "Built (UTC):   $BUILT_UTC"
  echo "Architecture:  linux/amd64 containers on Windows (Docker Desktop, WSL2 backend)"
  echo "Docker build host: $(docker version --format 'Docker {{.Server.Version}}')"
  echo "Spare parts app: project intraforge-spareparts-demo, commit $SP_COMMIT, $SP_DIRTY uncommitted file(s) included, content hash $SP_HASH"
} > "$OUT/BUILD_INFO.txt"

echo "== 5/6 offline manifest and checksums"
python - "$OUTW" "$HEAD_FULL" "$VERSION" "$BUILT_UTC" "${IMAGES[@]}" <<'PY'
import json, os, pathlib, subprocess, sys
out = pathlib.Path(sys.argv[1]); head, version, built = sys.argv[2:5]; images = sys.argv[5:]
def inspect(ref, fmt):
    return subprocess.run(["docker", "image", "inspect", ref, "--format", fmt], capture_output=True, text=True, check=True).stdout.strip()
purpose = {
    "intraforge-shop-backend": ("IntraForge backend, workers and scheduler (Django, Celery), migrations", f"built from source at {head[:9]}", "project"),
    "intraforge-shop-frontend": ("IntraForge web interface (Next.js)", f"built from source at {head[:9]}", "project"),
    "intraforge-shop-spareparts": ("Spare parts reference application (separate Next.js project with its own sample data; http://127.0.0.1:3000)",
        "separate project intraforge-spareparts-demo at " + os.environ.get("SP_COMMIT", "?") + (" + " + os.environ["SP_DIRTY"] + " uncommitted file(s)" if os.environ.get("SP_DIRTY", "0") != "0" else "") + ", content hash " + os.environ.get("SP_HASH", "?"), "project (its npm dependencies keep their own licences)"),
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
    "product": "IntraForge Local Edition v1.0 -- own-shop pilot", "product_version": version, "source_head": head, "built_utc": built,
    "docker_desktop_tested": subprocess.run(["docker", "version", "--format", "{{.Server.Version}}"], capture_output=True, text=True).stdout.strip(),
    "network_needed_at_install": False, "images": rows, "prerequisites": prereq,
    "not_used_at_install": ["npm/pnpm", "pip", "docker pull", "online WSL download", "GitHub", "Microsoft Store", "any package manager"],
}
(out / "OFFLINE_MANIFEST.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8", newline="\n")
lines = [f"IntraForge Local Edition v1.0 -- own-shop pilot -- OFFLINE MANIFEST", f"Source HEAD {head}   version {version}   built {built}", "",
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
( cd "$OUT" && sha256sum --binary VERSION BUILD_INFO.txt docker-compose.yml infrastructure/proxy/Caddyfile OFFLINE_MANIFEST.json images/intraforge-shop-images.tar > SHA256SUMS.txt )

rm -rf "$EXPORT" "$SP_CTX"

echo "== 6/6 package"
ZIP="$(dirname "$OUT")/IntraForge-Local-v1.0-Pilot-$HEAD_SHORT.zip"
rm -f "$ZIP" "$ZIP.sha256"
/c/Windows/System32/tar.exe -a -c -f "$(cygpath -m "$ZIP")" -C "$OUTW" .
( cd "$(dirname "$ZIP")" && sha256sum --binary "$(basename "$ZIP")" > "$(basename "$ZIP").sha256" )
echo
echo "Kit folder : $OUT"
echo "Package    : $ZIP  ($(du -h "$ZIP" | cut -f1))"
echo "SHA-256    : $(cut -d' ' -f1 "$ZIP.sha256")"
echo "HEAD       : $HEAD_FULL"
echo "Built      : $BUILT_UTC"
