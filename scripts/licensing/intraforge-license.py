#!/usr/bin/env python3
"""IntraForge licence tool -- for the vendor only (ADR-0023). Keep its folder private and backed up: whoever has
private-key.pem can make activation codes.

    python intraforge-license.py init                      create the key pair (once) and print the public key
    python intraforge-license.py master                    the master SN (made once; works on any number of your PCs)
    python intraforge-license.py serials 10                ten new serial numbers to sell
    python intraforge-license.py activate SN PC-CODE        the activation code for that SN on that PC
    python intraforge-license.py activate SN PC-CODE --transfer   move a sold SN to a new PC (the old PC is recorded)
    python intraforge-license.py list                      every SN, its PC and when it was activated

The folder is IFLICENSE_HOME, or C:\\Users\\<you>\\intraforge\\licensing. It holds private-key.pem (never share or
commit it) and registry.json (which SN belongs to which PC -- this is what makes one SN work on one PC only).
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "apps" / "backend"))

from cryptography.hazmat.primitives import serialization  # noqa: E402
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey  # noqa: E402

from licensing import codes  # noqa: E402

HOME = Path(os.environ.get("IFLICENSE_HOME") or Path.home() / "intraforge" / "licensing")
KEY = HOME / "private-key.pem"
REGISTRY = HOME / "registry.json"


def load_key() -> Ed25519PrivateKey:
    if not KEY.exists():
        sys.exit(f"No key yet in {HOME}. Run: python intraforge-license.py init")
    return serialization.load_pem_private_key(KEY.read_bytes(), password=None)


def load_registry() -> dict:
    return json.loads(REGISTRY.read_text(encoding="utf-8")) if REGISTRY.exists() else {"serials": {}}


def save_registry(reg: dict) -> None:
    tmp = REGISTRY.with_suffix(".tmp")
    tmp.write_text(json.dumps(reg, indent=2, sort_keys=True), encoding="utf-8")
    tmp.replace(REGISTRY)


def now() -> str:
    return datetime.datetime.now().isoformat(timespec="seconds")


def cmd_init(_args) -> None:
    HOME.mkdir(parents=True, exist_ok=True)
    if KEY.exists():
        print(f"The key already exists in {HOME}; it was not replaced.")
    else:
        key = Ed25519PrivateKey.generate()
        KEY.write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                          serialization.NoEncryption()))
        save_registry(load_registry())
        print(f"Created {KEY}. Back this folder up somewhere safe; never share private-key.pem.")
    print("Public key (built into IntraForge):", codes.public_key_text(load_key()))


def new_entry(reg: dict, kind: str) -> str:
    while True:
        sn = codes.new_serial(kind)
        if sn not in reg["serials"]:
            reg["serials"][sn] = {"kind": kind, "created": now(), "pcs": [], "note": ""}
            return sn


def cmd_master(_args) -> None:
    load_key()
    reg = load_registry()
    existing = [sn for sn, e in reg["serials"].items() if e["kind"] == codes.MASTER]
    if existing:
        print("Master SN:", existing[0])
        return
    sn = new_entry(reg, codes.MASTER)
    save_registry(reg)
    print("Master SN:", sn)
    print("It activates any number of your own PCs; each still needs its activation code from this tool.")


def cmd_serials(args) -> None:
    load_key()
    reg = load_registry()
    made = [new_entry(reg, codes.STANDARD) for _ in range(args.count)]
    save_registry(reg)
    print("\n".join(made))


def cmd_activate(args) -> None:
    key = load_key()
    reg = load_registry()
    sn, pc = codes.normalize_serial(args.serial), codes.normalize_pc(args.pc)
    if not sn:
        sys.exit("That serial number is not valid (check for a typo).")
    if not pc:
        sys.exit("That PC code is not valid. It looks like PC-1A2B-3C4D-5E6F-7A8B (IntraForge > Licence shows it).")
    entry = reg["serials"].get(sn)
    if entry is None:
        sys.exit("This serial number was not made by this tool (it is not in registry.json).")
    known = [p["pc"] for p in entry["pcs"] if not p.get("moved_at")]
    if entry["kind"] == codes.STANDARD and known and pc not in known:
        if not args.transfer:
            sys.exit(f"Refused: {sn} already belongs to {known[0]}. One SN works on one PC only. "
                     "To move it to a new PC, add --transfer.")
        for p in entry["pcs"]:
            if not p.get("moved_at"):
                p["moved_at"] = now()
    if pc not in known:
        entry["pcs"].append({"pc": pc, "activated": now()})
    if args.note:
        entry["note"] = args.note
    save_registry(reg)
    print(codes.sign_activation(key, serial=sn, pc=pc))


def cmd_list(_args) -> None:
    reg = load_registry()
    for sn, e in sorted(reg["serials"].items(), key=lambda kv: kv[1]["created"]):
        pcs = ", ".join(p["pc"] + (" (moved)" if p.get("moved_at") else "") for p in e["pcs"]) or "not activated"
        print(f"{sn}  {e['kind']:8}  {pcs}  {e.get('note', '')}")


def main() -> None:
    ap = argparse.ArgumentParser(description="IntraForge licence tool (vendor only)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init").set_defaults(fn=cmd_init)
    sub.add_parser("master").set_defaults(fn=cmd_master)
    s = sub.add_parser("serials")
    s.add_argument("count", type=int)
    s.set_defaults(fn=cmd_serials)
    a = sub.add_parser("activate")
    a.add_argument("serial")
    a.add_argument("pc")
    a.add_argument("--transfer", action="store_true")
    a.add_argument("--note", default="")
    a.set_defaults(fn=cmd_activate)
    sub.add_parser("list").set_defaults(fn=cmd_list)
    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
