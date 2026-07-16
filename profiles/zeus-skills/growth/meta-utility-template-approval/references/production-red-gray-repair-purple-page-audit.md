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
5. Reconcile page-row status against Broadcast Template `PAGES` before counting. In the validated MGS mapping, `Broadcast` + `Campaign` rows formed the active page universe; `Ready`, `On-hold`, and `Blocked` rows were attached but excluded from `PAGES`. Do not hardcode that forever: assert the grouped active count equals each live `/broadcast/Messenger[].PAGES` value and stop on mismatch.
6. Required operational fields and presentation order:
   - `PROFILE_NAME` → `Segurador`
   - `PAGE_NAME` → `Página`
   - `BROADCAST_TEMPLATE_NAME` → explicit `Nome do template` column immediately after `Página`
   - `https://facebook.com/{FB_PAGE_ID}` → clickable `Link da página`
   - `USER_LOGIN` or `LOGIN` → `Usuário do bot`
   - `FB_PAGE_ID` → Facebook Page ID
   - `PAGE_ID` → internal PG/Page ID
   - `STATUS`, purple category/reason for audit
7. Independently inspect the latest completed DigitalTRChat campaign report for each candidate page. Record only safe error code/subcode evidence; never export tokens, cookies, access tokens, or full raw responses.
8. Be precise about attribution and vocabulary:
   - purple is a message/template state, not a page-level color returned by SB;
   - `/broadcast/Messenger` aggregates errors by message and does not identify the failing Page ID;
   - “pages linked to templates with purple” is a measurable universe, while “pages that caused purple” is not exact without a per-page DTR/Meta result;
   - a page list mapped from affected templates is an operational suspect list unless corroborated. Even with corroboration, distinguish “same page-level failure observed” from proof that a specific Graph permission is missing.
9. Produce a verified XLSX with:
   - `Resumo`;
   - `Todas páginas roxas` for the complete active universe;
   - a named subset sheet such as `Subconjunto #200` when the request singles out one reason;
   - `Rows não ativas` for attached `Ready`/`On-hold`/`Blocked` rows.
   Include `Nome do template` as a prominent explicit column, clickable Facebook links, filters, frozen header, readable widths, purple category/reason, and a methodology caveat. Reopen the workbook and validate sheet names, row counts, column placement, and hyperlinks before delivery.

## 2026-07-16 observed case

The first answer incorrectly let a reason-specific subset sound like the total purple scope. The corrected live reconciliation was:

```text
Category                         Templates  Purple messages  Active linked pages
#200 pages_utility_messaging             6               51                   17
Application deleted                      1               30                    1
Application lacks permission             2               50                  131
Generic status=error                     1                1                   13
Total                                   10              132                  162
```

- `51` was the number of purple **messages**, not pages.
- The 17 pages belonged only to the six-template `#200 pages_utility_messaging` subset.
- The full purple universe was 132 messages in 10 templates linked to 162 active `Broadcast`/`Campaign` pages.
- Another 96 attached rows were `Ready`, `On-hold`, or `Blocked` and were separated from the active universe.
- Latest DTR reports for all 17 active `#200` rows showed `OAuthException code 100 / subcode 1689001`. This corroborated a page-level failure but was not represented as direct Graph proof of `pages_utility_messaging` state.
- When challenged on a surprisingly small page total, immediately recompute **all purple reason families** before defending the subset count.
