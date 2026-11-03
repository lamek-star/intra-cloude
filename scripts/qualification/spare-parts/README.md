# Spare Parts service application -- qualification scripts (ADR-0018)

Run against the disposable qualification stack (`scripts/qualification/compose.yaml`, port 8444) with the
`spareparts` service built by `scripts/shop-kit/build-spareparts-image.sh`. Never against a real installation.

1. `bash reset_slot.sh` -- empties the Spare Parts deployment slot (drops the disposable test install).
2. `python e2e_platform.py` -- 22 HTTP checks through the real proxy: install, live health, Open with no second
   login, cookie flags, CSRF, capabilities, audit relay, logout, internal API refused from outside.
3. `bash reset_slot.sh`, then from `apps/frontend`:
   `E2E_BASE_URL=https://localhost:8444 npx playwright test e2e/spare-parts-service-app.spec.ts` -- a shop's day
   through both UIs (writes `apps/frontend/e2e-results-spare-parts-service-app.json`).
4. `python backup_roundtrip.py apps/frontend/e2e-results-spare-parts-service-app.json` -- backup (the shop kit's
   commands), modify, restore, then verify stock, customers, invoices, the photo's bytes, price and ledger integrity.
