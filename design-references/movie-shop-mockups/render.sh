#!/usr/bin/env bash
# Renders each mockup page to a PNG (2x) with headless Edge: bash render.sh [page.html ...]
set -euo pipefail
cd "$(dirname "$0")"
EDGE="/c/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"
mkdir -p png
for page in "${@:-*.html}"; do
  for p in $page; do
    size=$(grep -oE 'data-size="[0-9]+,[0-9]+"' "$p" | head -1 | grep -oE '[0-9]+,[0-9]+' || echo 1440,900)
    "$EDGE" --headless=new --disable-gpu --hide-scrollbars --force-device-scale-factor=2 --virtual-time-budget=4000 \
      --window-size="$size" --screenshot="$(cygpath -w "$PWD/png/${p%.html}.png")" "file:///$(cygpath -m "$PWD/$p")" 2>/dev/null
    echo "png/${p%.html}.png"
  done
done
