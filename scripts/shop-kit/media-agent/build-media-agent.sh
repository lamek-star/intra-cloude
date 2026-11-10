#!/usr/bin/env bash
# Compiles the Movie Shop media agent (ADR-0022) with the C# compiler that ships with Windows (.NET Framework 4.x).
#   bash scripts/shop-kit/media-agent/build-media-agent.sh <output.exe>
set -euo pipefail
export MSYS_NO_PATHCONV=1
OUT="${1:?output exe}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/../../.." && pwd)"
CSC="/c/Windows/Microsoft.NET/Framework64/v4.0.30319/csc.exe"
FW="/c/Windows/Microsoft.NET/Framework64/v4.0.30319"
[ -x "$CSC" ] || { echo "the .NET Framework C# compiler was not found at $CSC" >&2; exit 1; }
w() { cygpath -w "$1"; }
"$CSC" -nologo -codepage:65001 -target:winexe -optimize+ -warnaserror+ -out:"$(w "$OUT")" \
  -win32icon:"$(w "$REPO/installer/assets/icon.ico")" \
  -reference:System.Drawing.dll -reference:System.Security.dll -reference:"$(w "$FW/System.Web.Extensions.dll")" \
  "$(w "$HERE/MediaAgent.cs")"
