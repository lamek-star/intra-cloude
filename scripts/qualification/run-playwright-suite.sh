#!/usr/bin/env bash
# Runs every Playwright spec against the disposable qualification stack, ONE FILE AT A TIME with a pause between
# files. The pause is deliberate: the authentication endpoints are rate limited to 10/minute on purpose (never
# loosened for tests), and several specs register accounts, so back-to-back files would be throttled -- that is the
# limit working, not a defect. Specs that need a prepared business (UI_STATE_FILE / SCALE_APP) skip themselves.
#
#   E2E_BASE_URL=https://localhost:8444 ./run-playwright-suite.sh <log-dir>
set -uo pipefail
LOGDIR="${1:?log directory}"
mkdir -p "$LOGDIR"
cd "$(dirname "${BASH_SOURCE[0]}")/../../apps/frontend"
: "${E2E_BASE_URL:=https://localhost:8444}"
export E2E_BASE_URL
overall=0
for spec in e2e/*.spec.ts; do
  name="$(basename "$spec" .spec.ts)"
  echo "=== $(date +%H:%M:%S) $name"
  timeout 600 npx playwright test "$spec" > "$LOGDIR/pw-$name.log" 2>&1
  rc=$?
  sed 's/\x1b\[[0-9;]*m//g' "$LOGDIR/pw-$name.log" | grep -E "passed|failed|skipped|flaky" | tail -3
  [ $rc -ne 0 ] && overall=1
  start=$(date +%s); while [ $(( $(date +%s) - start )) -lt 65 ]; do sleep 5; done
done
echo "=== suite finished rc=$overall"
exit $overall
