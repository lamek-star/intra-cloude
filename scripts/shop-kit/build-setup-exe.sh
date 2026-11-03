#!/usr/bin/env bash
# Wraps a shop-kit zip (and, optionally, the Windows prerequisites) into ONE double-click self-extracting installer.
#
#   scripts/shop-kit/build-setup-exe.sh <kit.zip> <output IntraForge-Setup.exe> ["Docker Desktop Installer.exe"] [wsl.x64.msi]
#
# With the third argument the Docker Desktop installer is embedded, with the fourth the WSL package (Microsoft's open-source
# wsl.<version>.x64.msi from github.com/microsoft/WSL). Both together make a PC with nothing on it installable with no internet.
# Docker Desktop's licence does not allow redistribution: an exe that embeds it is for the owner's own PCs only and must never be
# shared. Setup runs each embedded installer only after checking its publisher signature (Docker Inc / Microsoft Corporation).
#
# The stub (setup-stub/Program.cs) is compiled with the C# compiler that ships with Windows (.NET Framework 4.x), so the build
# needs no SDK and the resulting exe needs nothing on the shop PC. Layout of the output:
#   [stub exe][kit zip][docker installer][wsl msi][SHA-256 kit][SHA-256 docker][SHA-256 wsl][kit len][docker len][wsl len][magic "IFSFX003"]
# (each optional payload may be absent: length 0, hash zeros). The exe is UNSIGNED (no certificate exists): Windows SmartScreen
# shows "Unknown publisher" until it is signed.
set -euo pipefail
export MSYS_NO_PATHCONV=1

ZIP="${1:?kit zip}"; OUT="${2:?output exe}"; DOCKER="${3:-}"; WSL="${4:-}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CSC="/c/Windows/Microsoft.NET/Framework64/v4.0.30319/csc.exe"
[ -x "$CSC" ] || { echo "the .NET Framework C# compiler was not found at $CSC" >&2; exit 1; }
[ -f "$ZIP" ] || { echo "kit zip not found: $ZIP" >&2; exit 1; }

STUB="$(mktemp -d)/IntraForgeSetupStub.exe"
"$CSC" -nologo -target:exe -optimize+ -out:"$(cygpath -w "$STUB")" \
  -reference:System.IO.Compression.dll -reference:System.IO.Compression.FileSystem.dll -reference:System.Management.dll \
  "$(cygpath -w "$HERE/setup-stub/Program.cs")"

python - "$(cygpath -m "$STUB")" "$(cygpath -m "$ZIP")" "$(cygpath -m "$OUT")" "${DOCKER:+$(cygpath -m "$DOCKER")}" "${WSL:+$(cygpath -m "$WSL")}" <<'PY'
import hashlib, pathlib, shutil, struct, sys
stub, zip_path, out = (pathlib.Path(p) for p in sys.argv[1:4])
docker = pathlib.Path(sys.argv[4]) if len(sys.argv) > 4 and sys.argv[4] else None
wsl = pathlib.Path(sys.argv[5]) if len(sys.argv) > 5 and sys.argv[5] else None

def append(dst, path):
    if path is None:
        return b"\0" * 32, 0
    digest = hashlib.sha256(); size = 0
    with open(path, "rb") as f:
        while chunk := f.read(1 << 20):
            digest.update(chunk); size += len(chunk); dst.write(chunk)
    return digest.digest(), size

with open(out, "wb") as dst:
    with open(stub, "rb") as f: shutil.copyfileobj(f, dst)
    kit_hash, kit_size = append(dst, zip_path)
    docker_hash, docker_size = append(dst, docker)
    wsl_hash, wsl_size = append(dst, wsl)
    dst.write(kit_hash + docker_hash + wsl_hash)
    dst.write(struct.pack("<qqq", kit_size, docker_size, wsl_size))
    dst.write(b"IFSFX003")
print(f"kit {kit_size:,} bytes sha256 {kit_hash.hex()}")
if docker: print(f"docker installer {docker_size:,} bytes sha256 {docker_hash.hex()}")
if wsl: print(f"wsl package {wsl_size:,} bytes sha256 {wsl_hash.hex()}")
PY
( cd "$(dirname "$OUT")" && sha256sum --binary "$(basename "$OUT")" > "$(basename "$OUT").sha256" )
echo "Setup exe : $OUT ($(du -h "$OUT" | cut -f1))"
echo "SHA-256   : $(cut -d' ' -f1 "$OUT.sha256")"
