# IntraForge licence tool (vendor only)

`intraforge-license.py` makes serial numbers and activation codes (ADR-0023). It needs Python 3.11+ and the
`cryptography` package, and is run from a checkout of this repository on the vendor's own PC.

```
python scripts/licensing/intraforge-license.py init                  # once: the key pair
python scripts/licensing/intraforge-license.py master                # the master SN for your own PCs
python scripts/licensing/intraforge-license.py serials 10            # SNs to sell
python scripts/licensing/intraforge-license.py activate SN PC-CODE   # the activation code for that PC
python scripts/licensing/intraforge-license.py list
```

Its folder (`IFLICENSE_HOME`, default `C:\Users\<you>\intraforge\licensing`) holds `private-key.pem` and
`registry.json`. **Keep it private and backed up.** Never copy it into a repository, a kit or a shop PC: whoever has
the private key can make activation codes. If the key pair is ever replaced, IntraForge's `LICENSE_PUBLIC_KEY` must
change with it and every shop needs a new activation code.
