# IntraForge Local Edition — investor demonstration

**Status: rehearsal plan; NOT YET QUALIFIED.** Do not deliver this as a working
demo until the receive/sell, document and recovery checkpoints below have
recorded evidence. Refer to [Current State](implementation/CURRENT_STATE.md).

Use only the clearly fictional organization **Harmoney Auto Parts LLC — DEMO**.
Use original text documents and generated/owned illustrations. Do not show
third-party catalogue images as licensed assets or invented numbers as OEM
facts. Demo records are company-owned examples, separate from reference data.

| Minutes | One business story | Required evidence before rehearsal |
|---|---|---|
| 0–1 | Explain: “This business's records and files are stored on this computer.” Show the actual local address. | Running local stack; no unsupported privacy/legal claims |
| 1–2 | Show Control Center health and open IntraForge. Explain offline operation. | Real Control Center if available; otherwise explicitly identify the dev-stack demonstration |
| 2–4 | Open the DEMO company. Search `DEMO-90915-10009`, open Demo Oil Filter, and show its original document/image. | Normalized search, file permissions and locally served image verified |
| 4–6 | Receive 100 units into Main Warehouse from Demo Supplier A. Show movement and balance. | Atomic operation; balance 100, matching movement +100 |
| 6–8 | Sell 5 to Demo Workshop Customer. Open the supported sales document. | Balance 95, matching movement −5, linked sale/document; no claim of tax/accounting compliance |
| 8–9 | Show Shop Floor as a separate warehouse and the movement history. | Part × Warehouse uniqueness and transfer behavior qualified |
| 9–10 | Upload and reopen a company document. Show a restricted staff account. | File round trip, permissions and revocation evidence |
| 10–11 | Show activity history and restart persistence evidence. | Records, files and audit retained after restart |
| 11–13 | Create/show a full recovery set and explain the recorded disposable restore drill. | Matched control/tenant/files/configuration set, verified restore; never substitute `.icp` as equivalent |
| 13–14 | Explain LAN Server Mode and the future Enterprise path. | Label physical-LAN, bridged-VM or unverified status accurately |
| 14–15 | Recap the demonstrated business journey and disclose remaining release requirements. | Separate functional, investor-demo and commercial verdicts |

Rehearsal must start from reproducible DEMO data. Record starting quantities
and use a fresh operation identity for intentional new transactions; reuse
the same identity only when demonstrating a retry. Do not silently reset
customer data or overwrite the Phase 8 Reference Apps organization.

If a required step is not reliable, mark the demonstration NOT READY and fix
or explicitly rescope it before presenting. Signing and clean-Windows
qualification can remain disclosed commercial blockers even after a local
demonstration works. Do not describe development-phase completion as release
certification.
