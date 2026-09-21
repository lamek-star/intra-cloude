#!/usr/bin/env bash
# Wraps a shop-kit zip into ONE double-click self-extracting installer.
#
#   scripts/shop-kit/build-setup-exe.sh <kit.zip> <output IntraForge-Setup.exe>
#
# The stub (setup-stub/Program.cs) is compiled with the C# compiler that ships with Windows (.NET Framework 4.x), so the
# build needs no SDK and the resulting exe needs nothing on the shop PC. Layout of the output:
#   [stub exe][kit zip][32-byte SHA-256 of the zip][8-byte little-endian zip length][8-byte magic "IFSFX001"]
# The exe is UNSIGNED (no certificate exists): Windows SmartScreen shows "Unknown publisher" until it is signed.
set -euo pipefail
export MSYS_NO_PATHCONV=1

ZIP="${1:?kit zip}"; OUT="${2:?output exe}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CSC="/c/Windows/Microsoft.NET/Framework64/v4.0.30319/csc.exe"
[ -x "$CSC" ] || { echo "the .NET Framework C# compiler was not found at $CSC" >&2; exit 1; }
[ -f "$ZIP" ] || { echo "kit zip not found: $ZIP" >&2; exit 1; }

STUB="$(mktemp -d)/IntraForgeSetupStub.exe"
"$CSC" -nologo -target:exe -optimize+ -out:"$(cygpath -w "$STUB")" \
  -reference:System.IO.Compression.dll -reference:System.IO.Compression.FileSystem.dll \
  "$(cygpath -w "$HERE/setup-stub/Program.cs")"

python - "$(cygpath -m "$STUB")" "$(cygpath -m "$ZIP")" "$(cygpath -m "$OUT")" <<'PY'
import hashlib, pathlib, shutil, struct, sys
stub, zip_path, out = (pathlib.Path(p) for p in sys.argv[1:4])
digest = hashlib.sha256(); size = 0
with open(out, "wb") as dst:
    with open(stub, "rb") as f: shutil.copyfileobj(f, dst)
    with open(zip_path, "rb") as f:
        while chunk := f.read(1 << 20):
            digest.update(chunk); size += len(chunk); dst.write(chunk)
    dst.write(digest.digest()); dst.write(struct.pack("<q", size)); dst.write(b"IFSFX001")
print(f"payload {size:,} bytes, sha256 {digest.hexdigest()}")
PY
( cd "$(dirname "$OUT")" && sha256sum --binary "$(basename "$OUT")" > "$(basename "$OUT").sha256" )
echo "Setup exe : $OUT ($(du -h "$OUT" | cut -f1))"
echo "SHA-256   : $(cut -d' ' -f1 "$OUT.sha256")"
