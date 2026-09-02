# Meta Business ad-account batch reconciliation

Use with the class-level Meta Business browser-write workflow when creating repeated ad accounts through an authenticated persistent Chromium profile.

## Stale detail pane after success

A successful creation modal can update the URL to a new internal `selected_asset_id` while the detail pane still displays the previously selected account. Capture that asset ID before closing the modal, click `Done`, then navigate explicitly to:

`ad_accounts?business_id=<BM>&selected_asset_id=<ASSET>&selected_asset_type=ad-account`

Read the real `ID:` and `Owned by:` there. Never classify the stale prior ID as a duplicate creation.

## Blank page or timeout after Create

A blank page, timeout, or visual error after the mutation click does not prove failure. Do not retry immediately. Reload the canonical BM account list and compare real ad-account IDs with the durable checkpoint. If exactly one unknown ID appears, confirm name/owner, record it as committed, and continue without retry. Zero IDs permits one controlled retry after the fixed interval; more than one requires stopping for concurrent-state reconciliation.

## Repeated generic create rejection

A generic `Unable to add ad account` after the mutation click is not proof of a quota or security restriction when the UI still exposes `Add` and `Create a new ad account`. Reconcile side effects first against the union of: all IDs known before the run, IDs discovered in the latest preflight payload, and every ID already checkpointed by the batch. A virtualized payload can show only the newest window, so its visible count is not the Business total.

- If the canonical reload shows exactly one unknown ID, treat the mutation as committed and do not retry.
- If it shows zero unknown IDs, wait the fixed cadence and allow exactly one controlled retry.
- If the same generic rejection repeats and a second reload again proves zero side effect, stop the batch. Do not keep retrying and do not label it a maximum-account limit unless Meta actually displays that gate.
- On stop, report `Criadas X/Y`, `Faltam Z`, the repeated error text, and that both failed attempts had no side effect. Preserve the remaining count in the checkpoint so a later authorized resume starts only after fresh live reconciliation.

## Fixed-cadence and final validation

- Persist sequence, real ad-account ID, internal asset ID, timestamps, owner, assignment count, and access readback after every account.
- Measure cadence from the previous confirmed completion to the next mutation click; sleeping from iteration start is not sufficient proof.
- Virtualized lists may hide older rows. For final verification, search each real ID or navigate each captured internal asset directly, then verify requested count, unique IDs, name, owner, and access.
- In Playwright, pass `waitForFunction` options as the third argument: `page.waitForFunction(fn, null, {timeout: 90000})`. Passing `{timeout: ...}` as the second argument supplies the function argument and leaves the default timeout active.
