# Finance UI — country blocks — 1546030544213516358

Authorization: Rodolfo, Discord thread 1545426987756298340, message 1546030544213516358.
Target: https://dash.mgsdigitalcorp.com; existing authenticated release on MatteiInc01.

## Delivered and verified
- Invalids immediately below gross, same component values.
- Alphabetic domain families with root/subdomain adjacency; ranking preserved separately.
- MGS display aliases for unmapped/Geizian/G002; source identity and payroll unchanged.
- Vertical country blocks, original country order, daily columns including native gross and ROI; all shared/complementary facts retained.
- Final country/site consolidation, current filters consistent, no new country expense allocation.
- Daily edit action pinned right and scrolling guidance.
- USD origin-cell label correction; unused CAD cells left blank.

## Evidence
- 20 Python tests PASS; 10 Node tests PASS.
- Local browser editing/expense CRUD tested only in isolated DB.
- Public authenticated browser PASS, 390/768/1440 px, six destinations, order/MGS filters/country coverage/editor currency assertions, zero JS errors and zero viewport overflow.
- 2015 CAD/GBP captured-source comparisons, zero mismatches.
- Financial public test writes: 0. No changes to Google Sheets, formulas, engine, grants, credentials, system configuration or gateway.
- Static remote hash readback PASS. Backups under existing release/private/ui-static-backups/{app.js,refinements.css}.before-1546030544213516358.
- Local pre-change snapshots: apps/finance-system/private/ui-country-blocks-1546030544213516358/before/.
- Detailed logs: same evidence directory; browser screenshots in private/ui-redesign-1546005809845243944/.

## Changed assets and governance
public/app.js, public/refinements.css; tests/ui-country-blocks.test.mjs, tests/ui-browser.mjs; deploy/publish-ui-assets.py now requires --change-id for unique rollback copies; product-direction document; own finance skill v0.1.18; registry/checkpoint and infra inventory/audit.

## Boundaries
Financial entries remain independent between the captured-source dash and Sheets; only the existing two automatic FX quotes synchronize read-only. Sheet remains authoritative. Full native product migration/importers/cutover remain open. Financial engine and raw legacy metadata were not rewritten; USD label is resolved safely in the UI against the exact source.gross cell.
