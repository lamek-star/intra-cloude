#!/usr/bin/env bash
# Compiles the IntraForge Setup window (this folder) into one exe with the C# compiler that ships with Windows (.NET Framework
# 4.x): no SDK needed to build it, nothing needed on the PC that runs it. The icon, the manifest and the two brand images are
# compiled in.   SETUP_VERSION=1.5.2-abc bash scripts/shop-kit/setup-stub/build-stub.sh <output.exe>
set -euo pipefail
export MSYS_NO_PATHCONV=1
OUT="${1:?output exe}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/../../.." && pwd)"
CSC="/c/Windows/Microsoft.NET/Framework64/v4.0.30319/csc.exe"
[ -x "$CSC" ] || { echo "the .NET Framework C# compiler was not found at $CSC" >&2; exit 1; }
w() { cygpath -w "$1"; }
BRAND="$REPO/design-references/brand/generated"
sources=()
for f in "$HERE"/*.cs "$HERE"/Ui/*.cs; do sources+=("$(w "$f")"); done
# The version shown in the exe's file properties: SETUP_VERSION (the kit's VERSION, e.g. 1.5.2-ce9b03c85), numeric part as the
# file version.
SETUP_VERSION="${SETUP_VERSION:-0.0.0}"
NUMERIC="$(printf '%s' "$SETUP_VERSION" | grep -oE '^[0-9]+(\.[0-9]+){0,3}' || echo 0.0.0)"
GEN="$(mktemp -d)/Version.g.cs"
cat > "$GEN" <<CS
[assembly: System.Reflection.AssemblyVersion("$NUMERIC")]
[assembly: System.Reflection.AssemblyFileVersion("$NUMERIC")]
[assembly: System.Reflection.AssemblyInformationalVersion("$SETUP_VERSION")]
CS
sources+=("$(w "$GEN")")
"$CSC" -nologo -codepage:65001 -target:winexe -optimize+ -warnaserror+ -out:"$(w "$OUT")" \
  -win32icon:"$(w "$HERE/setup.ico")" -win32manifest:"$(w "$HERE/app.manifest")" \
  -resource:"$(w "$BRAND/intraforge-lockup-dark.png")",intraforge-lockup-dark.png \
  -resource:"$(w "$BRAND/intraforge-icon.png")",intraforge-icon.png \
  -reference:System.IO.Compression.dll -reference:System.IO.Compression.FileSystem.dll -reference:System.Management.dll \
  -reference:System.Windows.Forms.dll -reference:System.Drawing.dll \
  "${sources[@]}"
