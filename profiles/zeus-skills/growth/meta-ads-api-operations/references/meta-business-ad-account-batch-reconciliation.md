# Meta Business ad-account batch reconciliation

Use with the class-level Meta Business browser-write workflow when creating repeated ad accounts through an authenticated persistent Chromium profile.

## Stale detail pane after success

A successful creation modal can update the URL to a new internal `selected_asset_id` while the detail pane still displays the previously selected account. Capture that asset ID before closing the modal, click `Done`, then navigate explicitly to:

`ad_accounts?business_id=<BM>&selected_asset_id=<ASSET>&selected_asset_type=ad-account`

Read the real `ID:` and `Owned by:` there. Never classify the stale prior ID as a duplicate creation.

## Blank page or timeout after Create

A blank page, timeout, or visual error after the mutation click does not prove failure. Do not retry immediately. Reload the canonical BM account list and compare real ad-account IDs with the durable checkpoint. If exactly one unknown ID appears, confirm name/owner, record it as committed, and continue without retry. Zero IDs permits one controlled retry after the fixed interval; more than one requires stopping for concurrent-state reconciliation.

## Fixed-cadence and final validation

- Persist sequence, real ad-account ID, internal asset ID, timestamps, owner, assignment count, and access readback after every account.
- Measure cadence from the previous confirmed completion to the next mutation click; sleeping from iteration start is not sufficient proof.
- Virtualized lists may hide older rows. For final verification, search each real ID or navigate each captured internal asset directly, then verify requested count, unique IDs, name, owner, and access.
- In Playwright, pass `waitForFunction` options as the third argument: `page.waitForFunction(fn, null, {timeout: 90000})`. Passing `{timeout: ...}` as the second argument supplies the function argument and leaves the default timeout active.
