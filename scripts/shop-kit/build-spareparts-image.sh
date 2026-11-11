#!/usr/bin/env bash
# Builds the Spare Parts service-application image (ADR-0018) from a COMMITTED revision of the Spare Parts project:
# `git archive` of REF, so no working-tree file (.env*, local data, node_modules, build output) can reach the image.
#
#   scripts/shop-kit/build-spareparts-image.sh <image:tag> [version]
#
# SPAREPARTS_REPO  the Spare Parts git checkout or worktree (default: ~/projects/spareparts-platform)
# SPAREPARTS_REF   revision to build (default: HEAD of that checkout)
# Prints "commit=<sha> hash=<content hash>" on its last line for the build record.
set -euo pipefail
export MSYS_NO_PATHCONV=1
IMAGE="${1:?usage: build-spareparts-image.sh <image:tag> [version]}"
VERSION="${2:-dev}"
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="${SPAREPARTS_REPO:-$HOME/projects/spareparts-platform}"
REF="${SPAREPARTS_REF:-HEAD}"
REPO_M="$(cygpath -m "$REPO" 2>/dev/null || echo "$REPO")"

COMMIT="$(git --no-optional-locks -C "$REPO_M" rev-parse --short=9 "$REF")"
CTX="$(mktemp -d)"
trap 'rm -rf "$CTX"' EXIT
git --no-optional-locks -C "$REPO_M" archive --format=tar "$REF" | tar -C "$CTX" -xf -
if ls -A "$CTX" | grep -qE '^\.env'; then
  echo "an .env file is committed in the Spare Parts repository: refusing to build" >&2
  exit 1
fi
HASH="$(cd "$CTX" && find . -type f -print0 | sort -z | xargs -0 sha256sum | sha256sum | cut -c1-16)"
CTX_M="$(cygpath -m "$CTX" 2>/dev/null || echo "$CTX")"
DOCKERFILE_M="$(cygpath -m "$HERE/spareparts-app/Dockerfile" 2>/dev/null || echo "$HERE/spareparts-app/Dockerfile")"
docker build -q \
  --build-arg "SPAREPARTS_VERSION=$VERSION+$COMMIT" \
  -t "$IMAGE" -f "$DOCKERFILE_M" "$CTX_M" >/dev/null
echo "commit=$COMMIT hash=$HASH"
