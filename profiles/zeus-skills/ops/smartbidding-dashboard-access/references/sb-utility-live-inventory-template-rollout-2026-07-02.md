# SB Utility live inventory + template rollout lessons — 2026-07-02

## Why this exists

Rodolfo corrected Zeus during the Utility Template rollout: any question or action about the Smart Bidding dashboard must be answered from the **live dashboard/API runtime**, not from old CSVs, JSON snapshots, or cached audit files. Snapshots are acceptable only as backups/rollback evidence or if Rodolfo explicitly allows them.

## Live inventory rule

For SB template/page inventory:

1. Open SB through headed Playwright/Xvfb with the persisted storage state.
2. Select `Messenger` in the dashboard.
3. Capture live `/broadcast/Messenger` for template rows.
4. Capture live `/campaigns/Messenger` for Page rows.
5. Compute page counts by joining:

```text
Broadcast Template NAME == Page BROADCAST_TEMPLATE_NAME
```

Do **not** trust the `PAGES` field in `/broadcast/Messenger` alone. It can be stale or not match Page runtime. Example correction: `teste-4-us-cc-es-all-201-zero-width-2chars-approval` showed `PAGES=1` in broadcast raw, but live Page table had `0` matching rows.

## Full Page scope rule

The Page table can load an incomplete scope if only `Digital trust` children are selected. The incomplete capture observed:

```text
45 sites / 2,443 Page rows
```

The full MGS scope for this rollout required adding the Digital trust 2 children as well and returned:

```text
53 company/site params / 3,237 Page rows / 101 Broadcast Templates
```

Known Digital trust 2 child company params used in the full live query:

```text
digital-trust-2_cliquet
digital-trust-2_openzed
digital-trust-2_openzedfinanzas
digital-trust-2_wantabrand
digital-trust-2_wantabrandfinance
digital-trust-2_wavesbee
digital-trust-2_zuout
digital-trust-2_zuoutfinanzas
```

If a live Page capture returns 2,443 rows or shows `45 sites`, it is incomplete for MGS-wide inventory. Select/append Digital trust 2 children and refresh/re-query before answering.

## Correct reporting shape for template inventory

When Rodolfo asks for all templates with pages and message count, report from live runtime:

```text
Template | Pages live from Page BROADCAST_TEMPLATE_NAME | Messages live from Broadcast MESSAGES length
```

Label zero pages as `0`, not `-`, if the live Page join confirms no matching rows.

## Utility 10-message conversion pattern

For templates not yet converted to Utility:

1. Read exact target template from live `/broadcast/Messenger`.
2. Backup full template JSON and CSV before writing.
3. Build exactly 10 messages in Utility-style copy.
   - For CC templates: use approved Utility winners as the seed structure and translate/adapt to country/language.
   - For non-CC templates: write equivalent neutral status/update messages fitting the vertical.
4. Preserve target template links exactly by slot:

```text
new message 1 uses old LINK_1 from old message 1
new message 2 uses old LINK_1 from old message 2
...
new message 10 uses old LINK_1 from old message 10
```

Do not synthesize, normalize, or rotate URLs.

5. POST the full template payload back to `/broadcast/Messenger` with only intended fields changed (`MESSAGES`, and `NAME` only if renaming was requested).
6. Re-read live `/broadcast/Messenger` and validate:
   - template exists under final name;
   - `len(MESSAGES) == 10`;
   - first 10 links match preserved source slots.
7. Trigger approvals for each template through the same authenticated dashboard/API route used by the Run Approvals button. Validate HTTP 2xx and retain audit output.

## Approval ETA

Ciro rule:

```text
ETA = pages × active_messages × 8 seconds
```

For the 10-message Utility phase:

```text
ETA = pages × 80 seconds
```

Use live Page counts, not broadcast `PAGES`, for the ETA. Templates with 0 live pages have no meaningful approval ETA until a Page is attached.

## Naming / NAO USAR

If Rodolfo asks to retire a template while preserving it, rename with `NAO USAR -` and still apply the requested message reduction/approval action if explicitly instructed. Example:

```text
Openzed - US-CC-EN/EN - AV - g003-d Isliago 2 mensagens
→ NAO USAR - Openzed - US-CC-EN/EN - AV - g003-d Isliago 2 mensagens
```

## Pitfalls from this session

- Do not answer SB inventory from `sb-broadcast-messenger-raw-latest.json`, old CSVs, or schedule snapshots when Rodolfo asks about the dashboard.
- Do not mix `/broadcast/Messenger.PAGES` with Page-table counts without saying which source was used; for ops decisions, Page-table live wins.
- Do not assume `sem pages no inventário` means permanently no pages; re-check live.
- Do not treat `Update`/API write as enough for approval; also trigger Run Approvals / approval endpoint and store the result.
- When dashboard UI selection is incomplete, direct authenticated API with the full company parameter list can be used, but it still counts as live if executed against SB at task time.
