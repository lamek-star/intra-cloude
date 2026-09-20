#!/usr/bin/env bash
# Builds the offline investor-demo kit -- run ONCE, ONLINE, on the build machine (Docker Desktop running).
#
#   scripts/demo-kit/build-demo-kit.sh <output-folder> [rehearsal-port]
#
# Produces <output-folder> containing everything the demo laptop needs and nothing it does not:
#   docker-compose.yml, .env (fresh random secrets), infrastructure/proxy/Caddyfile, VERSION,
#   images/intraforge-demo-images.tar, backups/ (the fictional demo business), the install/start/stop/reset scripts,
#   README.txt, DEMO_LOGINS.txt, IMAGES.txt (what is inside, with digests).
#
# It uses its OWN compose project ("intraforge-demo"), image tags and volumes, and a rehearsal port (default 8453).
# It never touches any other IntraForge or Docker project: not the primary stack, not the qualification stack.
set -euo pipefail
export MSYS_NO_PATHCONV=1

OUT="${1:?output folder}"
PORT="${2:-8453}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/../.." && pwd)"
mkdir -p "$OUT"; OUT="$(cd "$OUT" && pwd)"
# The native Docker client wants Windows-style paths (C:/...), not Git-Bash /c/... ones.
OUTW="$(cygpath -m "$OUT")"; REPOW="$(cygpath -m "$REPO")"

DEMO_OWNER_EMAIL="owner@harmoney-demo.example"
DEMO_CASHIER_EMAIL="cashier@harmoney-demo.example"
DEMO_PASSWORD="correct-horse-battery-9"   # the password the e2e fixture registers with (e2e/flagship-setup.ts)

echo "== 1/6 build the two IntraForge images (current source)"
docker build -q -t intraforge-demo-backend:1.0 "$REPOW/apps/backend" >/dev/null
docker build -q -t intraforge-demo-frontend:1.0 "$REPOW/apps/frontend" >/dev/null

echo "== 2/6 assemble the kit folder"
mkdir -p "$OUT/infrastructure/proxy" "$OUT/images" "$OUT/backups"
cp "$HERE/template/"*.yml "$HERE/template/"*.ps1 "$OUT/"
cp "$REPO/infrastructure/proxy/Caddyfile" "$OUT/infrastructure/proxy/Caddyfile"
cp "$REPO/VERSION" "$OUT/VERSION"
python - "$OUTW" "$PORT" <<'PY'
import pathlib, secrets, sys
out, port = pathlib.Path(sys.argv[1]), sys.argv[2]
env = out / ".env"
if env.exists():
    print("keeping the existing .env (its secrets belong to the existing backups)")
    raise SystemExit
db = secrets.token_urlsafe(24)
store = secrets.token_urlsafe(24)
lines = {
    "DJANGO_SETTINGS_MODULE": "config.settings.prod",
    "SECRET_KEY": secrets.token_urlsafe(48),
    "CREDENTIAL_ENCRYPTION_KEY": secrets.token_urlsafe(48),
    "BACKUP_ENCRYPTION_KEY": secrets.token_urlsafe(32),
    "BACKUP_DIR": "/backups",
    "ALLOWED_HOSTS": "localhost,127.0.0.1,backend",
    # 8443 is the laptop's default; the build machine rehearses on another port.
    "CSRF_TRUSTED_ORIGINS": f"https://localhost:8443,https://localhost:{port}",
    "OIDC_ISSUER": "https://localhost:8443",
    "CACHE_URL": "redis://valkey:6379/1",
    "REDIS_URL": "redis://valkey:6379/0",
    "POSTGRES_USER": "intraforge", "POSTGRES_DB": "intraforge", "POSTGRES_PASSWORD": db,
    "CONTROL_DB_HOST": "postgres-control", "CONTROL_DB_NAME": "intraforge", "CONTROL_DB_USER": "intraforge",
    "CONTROL_DB_PASSWORD": db,
    "TENANT_DB_HOST": "postgres-tenant", "TENANT_DB_NAME": "intraforge", "TENANT_DB_USER": "intraforge",
    "TENANT_DB_PASSWORD": db,
    "OBJECT_STORAGE_ENDPOINT": "http://object-storage:9000", "OBJECT_STORAGE_BUCKET_PREFIX": "intraforge",
    "OBJECT_STORAGE_ROOT_USER": "intraforge", "OBJECT_STORAGE_ROOT_PASSWORD": store,
    "MINIO_ROOT_USER": "intraforge", "MINIO_ROOT_PASSWORD": store,
    # the customer default: only qualified applications are offered
    "SHOW_UNQUALIFIED_BUILT_IN_APPS": "0",
}
env.write_text("".join(f"{k}={v}\n" for k, v in lines.items()), encoding="utf-8", newline="\n")
print("generated a fresh .env")
PY

echo "== 3/6 create the demo business inside a clean copy of the kit's own stack (port $PORT)"
cd "$OUT"
export DEMO_HTTPS_PORT="$PORT"
docker compose down --volumes --remove-orphans >/dev/null 2>&1 || true
docker compose up -d --pull never postgres-control postgres-tenant valkey object-storage >/dev/null
for svc in postgres-control postgres-tenant; do
  for _ in $(seq 1 60); do docker compose exec -T "$svc" sh -c 'pg_isready -U "$POSTGRES_USER"' >/dev/null 2>&1 && break; sleep 2; done
done
docker compose run --rm backend python manage.py migrate --noinput >/dev/null
docker compose run --rm backend python manage.py seed_permissions >/dev/null
docker compose up -d --pull never >/dev/null
for _ in $(seq 1 60); do
  docker compose exec -T backend python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/readyz', timeout=5).status == 200 else 1)" >/dev/null 2>&1 && break
  sleep 3
done
STATE="$OUT/.demo-state.json"
( cd "$REPO/apps/frontend" && \
  E2E_BASE_URL="https://localhost:$PORT" UI_STATE_FILE="$(cygpath -m "$STATE")" \
  DEMO_OWNER_EMAIL="$DEMO_OWNER_EMAIL" DEMO_CASHIER_EMAIL="$DEMO_CASHIER_EMAIL" \
  npx playwright test e2e/spare-parts-recovery-prep.spec.ts 2>&1 | sed 's/\x1b\[[0-9;]*m//g' | grep -E "passed|failed|Error" )

echo "== 4/6 back the demo business up (control database, business data, files) and copy the files out"
rm -f "$OUT/backups/"*
for type in control_db tenant_db object_storage; do
  docker compose exec -T backend python manage.py run_backup "$type" >/dev/null
done
CID="$(docker compose ps -q backend)"
docker cp "$CID:/backups/." "$OUTW/backups/" >/dev/null
ls "$OUT/backups" | sed 's/^/   /'

echo "== 5/6 export the images (no internet needed to load them)"
docker save -o "$OUTW/images/intraforge-demo-images.tar" \
  intraforge-demo-backend:1.0 intraforge-demo-frontend:1.0 postgres:18 valkey/valkey:9-alpine minio/minio:latest caddy:2-alpine
{
  echo "Images inside images/intraforge-demo-images.tar (loaded by Install-IntraForgeDemo.ps1):"
  for image in intraforge-demo-backend:1.0 intraforge-demo-frontend:1.0 postgres:18 valkey/valkey:9-alpine minio/minio:latest caddy:2-alpine; do
    echo "  $image  $(docker image inspect "$image" --format '{{.Id}}')"
  done
  echo
  echo "Note: minio/minio:latest is NOT pinned (docs/operations/THIRD_PARTY_LICENSES.md); MinIO is AGPL-3.0."
} > "$OUT/IMAGES.txt"

echo "== 6/6 write the logins and the one-page guide, then clean up the build-time stack"
{
  echo "IntraForge demo logins (fictional data only; demo computer only)"
  echo
  echo "Address:   https://localhost:8443   (accept the certificate warning: Advanced, then continue)"
  echo "Owner:     $DEMO_OWNER_EMAIL"
  echo "Cashier:   $DEMO_CASHIER_EMAIL   (can sell; cannot receive, add products or see suppliers)"
  echo "Password:  $DEMO_PASSWORD   (both)"
  echo
  echo "Starting state: company 'Harmoney Auto Parts LLC -- DEMO'; Demo Oil Filter, part number 04465-0K290,"
  echo "supplier Demo Supplier A, warehouse Main Warehouse, customer Demo Retail Customer; 95 on hand"
  echo "(received 100, sold 5); one sales document; one stored data sheet."
} > "$OUT/DEMO_LOGINS.txt"
cp "$HERE/template/README.txt" "$OUT/README.txt"
rm -f "$STATE"
docker compose down --volumes --remove-orphans >/dev/null
docker rmi -f intraforge-demo-backend:1.0 intraforge-demo-frontend:1.0 >/dev/null 2>&1 || true
echo
echo "Kit ready: $OUT"
du -sh "$OUT" | cut -f1 | sed 's/^/size: /'
