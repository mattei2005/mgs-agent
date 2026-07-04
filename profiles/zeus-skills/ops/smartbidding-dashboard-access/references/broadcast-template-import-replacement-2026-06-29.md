# Broadcast Template Import/Replacement — 2026-06-29

## Context

Rodolfo trained Zeus on the Smart Bidding Messenger Broadcast Template import flow while replacing US-CC-EN templates with an approved Utility message bank.

The class-level lesson: template replacement is a state-changing operation and must be treated as a controlled import with backup, exact link preservation, parent-modal save, and API validation.

## UI flow that persisted correctly

For one target template in `Accounts > Messenger > Broadcast Template`:

1. Filter/open the target template.
2. Click the blue `N Messages` button.
3. Open the `Import` tab.
4. Click `Erase all`.
5. Click `Upload` and choose the prepared CSV.
6. Confirm the Import tab shows `Uploaded messages: <expected>` and `Total messages: <expected>`.
7. Click `Update` in the Messenger Messages modal.
8. Back on `Edit Messenger Broadcast`, click the blue `Save` button.
9. Re-query `/broadcast/Messenger` and validate the template has the expected message count and first/last text+link match the CSV.

Critical: clicking `Update` after upload is not enough. The parent `Edit Messenger Broadcast` modal must also be saved. In the session, after upload+Update but before parent Save, the UI showed `187 Messages` in the modal but the persisted API state was wrong. Re-running with parent `Save` fixed it.

## Backup rule

Before `Erase all` or upload:

- Pull the target template from authenticated `/broadcast/Messenger`.
- Save raw template JSON.
- Save import-format CSV (`MESSAGE ID`, `TEXT`, `DESCRIPTION`, `IMAGE`, `CTA 1`, `LINK 1`, `CTA 2`, `LINK 2`, `TEXT 2`).
- Validate the backup has the expected current message count. If the live state already looks wrong (e.g. only 1 test message), stop and report; do not claim it is a good backup of the old production state.

## Exact link-sequence rule

When preparing replacement CSVs for existing templates:

- Use the approved message text/CTA bank.
- Use the `LINK_1` sequence from the specific target template.
- Preserve the exact order and exact URL strings, including repeats, `-2` variants, query params, and single-link AV/YM templates.
- Repeat the full source sequence as needed until all approved messages have a link.
- Do not infer or normalize a `1..15` sequence unless the user explicitly asks. Rodolfo corrected this: “1 a 15” was only an example; the actual template sequence wins.

## Validation pattern

After every import:

- Re-query authenticated `/broadcast/Messenger`.
- Parse `MESSAGES` JSON.
- Assert `len(messages) == expected_count`.
- Compare first and last `TEXT` and `LINK_1` with the CSV.
- For bulk jobs, validate each target independently; if the modal becomes unstable, restart a fresh headed/Xvfb browser per template.

## Approval status fields

Inside each message object in `MESSAGES`:

- `APPROVED > 0` = green/approved.
- `REJECTED > 0` = red/rejected.
- `INVALID_FORMAT > 0` = invalid format.

Use these backend fields instead of relying on screenshots when classifying approval result rows.
