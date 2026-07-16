# Production red/gray repair and purple page attribution

## Trigger

Use this reference when Rodolfo asks to keep linked SmartBidding Broadcast Templates at a fixed message count, automatically repair red/gray messages, or identify pages behind purple approval errors.

## Repair policy currently agreed

- Operate only on production templates with `PAGES > 0`.
- Exclude names beginning with `Teste` or `NAO USAR`.
- Keep exactly 30 messages; never reuse the obsolete 10/20/30 scaling tracker for this job.
- Preserve green slots, links, page associations, template metadata, and message count.
- Red: replace with a unique same-country/vertical/language copy, then run `Run Approval → Update → Save → readback`.
- Gray: do not act while approval may still be processing. Eligibility ETA is `pages × 30 × 12 seconds`, plus any explicit safety margin. For an eligible stale slot, install a different copy, run approval, wait its new ETA, and allow at most four distinct copies. Persist attempts by immutable template ID + message ID + normalized text hash. Reset on green or verified manual change.
- After four gray copy failures, stop that slot and report template name, page count, slot/message count, and attempts to `#cron-temp-templates` (`1524188896215171222`). Suppress duplicate alerts.
- Purple: never auto-replace in this repair loop. Treat as app/page/segurador connection diagnostics.

## Do not revive the legacy rollout manager in place

The old hourly manager contains obsolete 10/20/30 scaling, a stale tracker, and older gray rules. Freeze its history as legacy/superseded for audit and backups. Build a dedicated fixed-30 repair state instead of deleting historical records.

## Purple-error attribution workflow

1. Fresh-read `/broadcast/Messenger` under the full operational account scope.
2. Parse `MESSAGES[].REJECTED_REASON`. Remember that a reason total is a **message count**, not a page count.
3. Select templates whose reason contains `pages_utility_messaging` or the other purple app errors.
4. Map each affected immutable `BROADCAST_TEMPLATE_ID` to `/campaigns/Messenger` rows.
5. Separate active rows from `On-hold`; Broadcast Template `PAGES` can exclude an attached On-hold row.
6. Required operational fields:
   - `PROFILE_NAME` → segurador
   - `PAGE_NAME` → página
   - `https://facebook.com/{FB_PAGE_ID}` → page link
   - `USER_LOGIN` or `LOGIN` → usuário do bot
   - `FB_PAGE_ID` → Facebook Page ID
   - `PAGE_ID` → internal PG/Page ID
   - `BROADCAST_TEMPLATE_NAME`, `STATUS` for audit
7. Independently inspect the latest completed DigitalTRChat campaign report for each candidate page. Record only safe error code/subcode evidence; never export tokens, cookies, access tokens, or full raw responses.
8. Be precise about attribution: `/broadcast/Messenger` aggregates errors by message and does not identify the failing Page ID. A page list mapped from affected templates is an operational suspect list unless a per-page DTR/Meta result corroborates it. Even with corroboration, distinguish “same page-level failure observed” from proof that a specific Graph permission is missing.
9. Produce a verified XLSX with:
   - `Resumo`
   - active/corroborated pages
   - excluded/On-hold rows
   Include clickable Facebook links, filters, frozen header, readable widths, and a methodology caveat. Reopen the workbook and validate sheet names, row counts, and hyperlinks before delivery.

## 2026-07-16 observed case

- `51` was the number of purple **messages**, not pages.
- Six templates carried `(#200) App does not have pages_utility_messaging permission on the Page`.
- Mapping through `BROADCAST_TEMPLATE_ID` found 17 active linked pages and one additional On-hold row excluded from Broadcast `PAGES`.
- Latest DTR reports for all 17 active rows showed `OAuthException code 100 / subcode 1689001`. This corroborated a page-level failure but was not represented as direct Graph proof of `pages_utility_messaging` state.
- Other purple reason families observed in the same audit were app permission missing, application deleted, and generic `status=error`; these must remain outside the red/gray copy-repair loop.
