#!/usr/bin/env bash
# Business recovery drill: seed a business -> back it up -> COPY BACKUPS OFF THE STACK ->
# destroy the disposable environment -> fresh-initialize -> restore from the off-stack copy ->
# verify by measurement (drill.py). Run from Git Bash on the qualification host.
#
#   QUALIFICATION_ENV_FILE=<private env file> ./run-drill.sh [stage ...]
#   stages: destroy init seed backup restore verify   (default: the whole drill, in order)
#
# SAFETY: this only ever touches the compose project `intraforge-local-qualification`
# and its four named volumes. It refuses to remove anything else. It never runs against the
# primary `intra-cloude` stack, its volumes, or any WSL distribution.
set -euo pipefail
export MSYS_NO_PATHCONV=1

# Windows-style paths (C:/...): the docker CLI here is a native Windows binary.
HERE="$(cygpath -m "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)")"
REPO="$(cygpath -m "$(cd "$HERE/../../.." && pwd)")"
PROJECT="intraforge-local-qualification"
RUNNER="${PROJECT}-runner-1"
: "${QUALIFICATION_ENV_FILE:?set QUALIFICATION_ENV_FILE to the private disposable env file}"
export QUALIFICATION_ENV_FILE
# Logs and the off-stack backup copy live beside the private env file, outside the repository.
LOGDIR="${DRILL_LOGDIR:-$(cygpath -m "$(dirname "$QUALIFICATION_ENV_FILE")")/recovery-drill}"
OFFSITE="$LOGDIR/offsite"   # stands in for an external USB/NAS copy that survives the disaster
mkdir -p "$LOGDIR" "$OFFSITE"
COMPOSE=(docker compose -f "$REPO/scripts/qualification/compose.yaml")

log() { printf '\n=== %s | %s\n' "$(date -u +%H:%M:%S)" "$*" | tee -a "$LOGDIR/drill.log"; }

# Every exec uses the disposable env file and the real production settings module (the appliance
# runs prod settings), with the runner's test overrides undone.
rexec() {
  docker exec -i --env-file "$QUALIFICATION_ENV_FILE" \
    -e DJANGO_SETTINGS_MODULE=config.settings.prod -e BACKUP_DIR=/backups "$RUNNER" "$@"
}

guard_volume() {
  case "$1" in
    "${PROJECT}_control" | "${PROJECT}_tenant" | "${PROJECT}_objects" | "${PROJECT}_backups") ;;
    *) echo "REFUSING to touch volume '$1' -- not a qualification volume" >&2; exit 3 ;;
  esac
}

wait_pg() {
  for svc in postgres-control postgres-tenant; do
    for _ in $(seq 1 60); do
      docker exec "${PROJECT}-${svc}-1" pg_isready -U qualification >/dev/null 2>&1 && break
      sleep 2
    done
    docker exec "${PROJECT}-${svc}-1" pg_isready -U qualification
  done
}

stage_destroy() {
  log "DESTROY the disposable environment (containers + its four volumes)"
  "${COMPOSE[@]}" down --remove-orphans 2>&1 | tail -3
  for v in control tenant objects backups; do
    guard_volume "${PROJECT}_${v}"
    docker volume rm "${PROJECT}_${v}" 2>&1 || true
  done
  docker volume ls --format '{{.Name}}' | grep "^${PROJECT}_" || echo "(no qualification data volumes remain)"
}

stage_init() {
  log "FRESH INITIALIZE: empty databases, migrate, seed permissions"
  "${COMPOSE[@]}" up -d --no-build postgres-control postgres-tenant valkey object-storage runner 2>&1 | tail -6
  wait_pg
  rexec python manage.py migrate --noinput 2>&1 | tail -3
  rexec python manage.py seed_permissions 2>&1 | tail -1
}

stage_seed() {
  log "SEED a Spare Parts business through the real services/API"
  rexec sh -c "mkdir -p /backups/drill"
  docker exec -i --env-file "$QUALIFICATION_ENV_FILE" -e DJANGO_SETTINGS_MODULE=config.settings.prod \
    -e BACKUP_DIR=/backups -e DRILL_MODE=seed "$RUNNER" python manage.py shell < "$HERE/drill.py" \
    2>&1 | tee "$LOGDIR/seed.log"
}

stage_backup() {
  log "BACKUP control_db, tenant_db, object_storage, configuration (encrypted at rest)"
  : > "$LOGDIR/backup-ids.txt"
  for t in control_db tenant_db object_storage configuration; do
    out="$(rexec python manage.py run_backup "$t" 2>&1)"; echo "$out"
    echo "$t $(echo "$out" | grep -o 'Backup [0-9a-f-]*' | awk '{print $2}')" >> "$LOGDIR/backup-ids.txt"
  done
  while read -r t _id; do
    # verifies the latest successful backup of this type in an isolated throwaway target
    rexec python manage.py verify_backup "$t" < /dev/null 2>&1 | tail -2
  done < "$LOGDIR/backup-ids.txt"
  log "COPY backups OFF the stack (the external-drive copy) and checksum them"
  rm -rf "$OFFSITE"; mkdir -p "$OFFSITE"
  docker cp "$RUNNER:/backups/." "$OFFSITE/"
  (cd "$OFFSITE" && find . -type f ! -name '*.sha256' -exec sha256sum {} \; | sort -k2 | tee "$LOGDIR/offsite.sha256")
}

stage_offsite() {
  rexec sh -c "mkdir -p /backups"
  docker cp "$OFFSITE/." "$RUNNER:/backups/"
}

stage_restore_gap() {
  log "R1 (reproduction of the gap): restore by BackupRecord id on a freshly initialized install"
  stage_offsite
  set +e
  old_id="$(awk '$1=="control_db"{print $2}' "$LOGDIR/backup-ids.txt")"
  rexec python manage.py restore_backup "$old_id" --yes 2>&1 | tail -3 | tee "$LOGDIR/restore-by-record-reproduction.log"
  set -e
}

stage_restore() {
  log "R2: restore from the off-stack backup FILES (no BackupRecord needed)"
  stage_offsite
  for spec in "control_db:control_db_" "tenant_db:tenant_db_" "object_storage:object_storage_"; do
    t="${spec%%:*}"; prefix="${spec##*:}"
    # File names are <type>_<record id>_<UTC timestamp>.<ext>: sort on the timestamp, not the id.
    f="$(rexec sh -c "ls /backups/${prefix}* | sed -E 's/.*_([0-9]{8}T[0-9]{6}Z).*/\1 &/' | sort | tail -1 | cut -d' ' -f2")"
    rexec python manage.py restore_backup_file "$f" --type "$t" --yes 2>&1 | tail -4
  done
}

stage_verify() {
  log "VERIFY the restored business by measurement (drill.py verify)"
  docker exec -i --env-file "$QUALIFICATION_ENV_FILE" -e DJANGO_SETTINGS_MODULE=config.settings.prod \
    -e BACKUP_DIR=/backups -e DRILL_MODE=verify "$RUNNER" python manage.py shell < "$HERE/drill.py" \
    2>&1 | tee "$LOGDIR/verify.log"
}

stages=("$@"); [ ${#stages[@]} -eq 0 ] && stages=(destroy init seed backup destroy init restore verify)
for s in "${stages[@]}"; do "stage_$s"; done
log "drill stages finished: ${stages[*]}"
