#!/usr/bin/env bash
# Collects a support-diagnostics bundle from a running (or broken) IntraForge Compose stack.
#
#   collect-diagnostics.sh --compose-file <compose.yaml> --env-file <.env> [--url https://localhost:8444]
#                          [--out <dir>] [--tail 500]
#
# What is in the bundle: versions, service status, health and readiness, the last N log lines of every
# service, whether migrations are pending, the names (never the values) of the configured settings, the
# backup files present (names and sizes) and free disk space. WHAT IS NEVER IN IT: passwords, keys, tokens,
# cookies, connection-string credentials, the environment file, or any customer data.
#
# Safety, in this order: (1) every text is passed through system.redaction (the same module the unit tests
# cover); if redaction cannot run, raw logs are omitted rather than included; (2) before the bundle is sealed,
# every secret VALUE from the environment file is searched for literally in the whole bundle -- one hit and the
# bundle is deleted and the script fails. Read-only: it changes nothing on the stack.
set -uo pipefail
export MSYS_NO_PATHCONV=1

COMPOSE_FILE=""; ENV_FILE=""; URL="https://localhost:8444"; OUT="."; TAIL=500
while [ $# -gt 0 ]; do
  case "$1" in
    --compose-file) COMPOSE_FILE="$2"; shift 2 ;;
    --env-file) ENV_FILE="$2"; shift 2 ;;
    --url) URL="$2"; shift 2 ;;
    --out) OUT="$2"; shift 2 ;;
    --tail) TAIL="$2"; shift 2 ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done
: "${COMPOSE_FILE:?--compose-file is required}"
: "${ENV_FILE:?--env-file is required}"

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$OUT"
DIR="$(mktemp -d)/intraforge-diagnostics-$STAMP"
mkdir -p "$DIR/logs"
COMPOSE=(docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE")

# Redaction runs in the backend IMAGE (so it works even when the stack is down). It is probed ONCE, up front, in
# this shell (a flag set inside a pipeline would be lost): if the probe does not come back redacted, no raw text
# is ever kept -- every section says "omitted" and the script ends with a warning.
REDACTOR=("${COMPOSE[@]}" run --rm --no-deps -T backend python -m system.redaction)
if [ "$(echo 'password=probe-value-123' | "${REDACTOR[@]}" 2>/dev/null)" = "password=[REDACTED]" ]; then REDACT_OK=1; else REDACT_OK=0; fi
redact() {
  if [ "$REDACT_OK" = 1 ]; then "${REDACTOR[@]}" 2>/dev/null; else cat > /dev/null; echo "[omitted: redaction unavailable]"; fi
}
section() { printf '\n== %s ==\n' "$1"; }

{
  echo "IntraForge diagnostics bundle"; echo "collected (UTC): $STAMP"
  section "host"; uname -a 2>/dev/null || true
  section "docker"; docker version --format 'client {{.Client.Version}} / server {{.Server.Version}}' 2>&1 | head -2
  section "services"; "${COMPOSE[@]}" ps 2>&1 | head -30
  section "images"; "${COMPOSE[@]}" images 2>&1 | head -30
  section "disk (free space on the volume holding this bundle)"; df -h "$OUT" 2>/dev/null | head -3 || true
  section "health"
  for path in healthz readyz; do
    printf '%s: ' "$path"; curl -sk --max-time 10 -w ' (HTTP %{http_code})\n' "$URL/$path" 2>&1 | head -3
  done
  section "configured settings (NAMES ONLY -- values are never collected)"
  grep -vE '^\s*(#|$)' "$ENV_FILE" | cut -d= -f1 | sort
} 2>&1 | redact > "$DIR/summary.txt"

{
  section "pending migrations (count of unapplied)"
  "${COMPOSE[@]}" exec -T backend python manage.py showmigrations --plan 2>&1 | grep -c '\[ \]' || true
  section "recent backups (from the application's own backup list)"
  "${COMPOSE[@]}" exec -T backend python manage.py list_backups 2>&1 | tail -25 || true
} 2>&1 | redact > "$DIR/backend.txt"

for service in $("${COMPOSE[@]}" config --services 2>/dev/null); do
  "${COMPOSE[@]}" logs --no-color --tail "$TAIL" "$service" 2>&1 | redact > "$DIR/logs/$service.log"
done

# ---- self-check: no secret value from the environment file may appear anywhere in the bundle ------------------
LEAK=0
while IFS='=' read -r key value; do
  value="${value%\"}"; value="${value#\"}"; value="${value%\'}"; value="${value#\'}"
  case "$key" in *[Pp][Aa][Ss][Ss]*|*[Ss][Ee][Cc][Rr][Ee][Tt]*|*[Kk][Ee][Yy]*|*[Tt][Oo][Kk][Ee][Nn]*|*[Cc][Rr][Ee][Dd]*) ;; *) continue ;; esac
  [ "${#value}" -ge 8 ] || continue
  if grep -rqF -- "$value" "$DIR"; then echo "LEAK: the value of $key appears in the bundle" >&2; LEAK=1; fi
done < <(grep -vE '^\s*(#|$)' "$ENV_FILE")
if [ "$LEAK" = 1 ]; then rm -rf "$DIR"; echo "Bundle deleted: a secret survived redaction. Nothing was written." >&2; exit 3; fi

ARCHIVE="$OUT/intraforge-diagnostics-$STAMP.tar.gz"
tar -czf "$ARCHIVE" -C "$(dirname "$DIR")" "$(basename "$DIR")"
rm -rf "$(dirname "$DIR")"
echo "Diagnostics bundle written: $ARCHIVE"
[ "$REDACT_OK" = 1 ] || echo "WARNING: redaction was unavailable; raw logs were omitted from the bundle." >&2
