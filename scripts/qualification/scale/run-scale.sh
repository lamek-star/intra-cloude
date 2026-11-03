#!/usr/bin/env bash
# Scale qualification on the DISPOSABLE stack only: generate a large business through the real services,
# then measure it. Never touches the primary stack.
#   QUALIFICATION_ENV_FILE=<private env> ./run-scale.sh generate|measure [tag] [products]
set -euo pipefail
export MSYS_NO_PATHCONV=1
HERE="$(cygpath -m "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)")"
RUNNER="intraforge-local-qualification-runner-1"
: "${QUALIFICATION_ENV_FILE:?set QUALIFICATION_ENV_FILE}"
mode="${1:?generate|measure}"; tag="${2:-}"; products="${3:-5000}"
docker exec -i --env-file "$QUALIFICATION_ENV_FILE" -e DJANGO_SETTINGS_MODULE=config.settings.prod \
  -e BACKUP_DIR=/backups -e SCALE_MODE="$mode" -e SCALE_TAG="$tag" -e SCALE_PRODUCTS="$products" \
  "$RUNNER" python manage.py shell < "$HERE/scale.py"
