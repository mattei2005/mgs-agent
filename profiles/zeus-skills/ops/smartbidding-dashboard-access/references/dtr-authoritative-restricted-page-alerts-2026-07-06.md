# DTR-authoritative restricted page alerts — 2026-07-06

## Durable lesson

For restricted Messenger pages, SmartBidding is not the source of truth for whether a page is newly restricted. DTR/Bot is the source of truth. SmartBidding is the operational destination where `STATUS`, `RESTRICTED_UNTIL`, and `NOTES` are updated after DTR confirmation.

## Correct workflow

1. Load the migration sheet and skip users/seguradores marked with `X` / removed.
2. Load SmartBidding first and build a skip-list of pages already carrying active/future `RESTRICTED_UNTIL`; do not spend DTR time rechecking those pages during the normal twice-daily run.
3. For remaining pages, log into DTR by bot user/segurador and read the latest `Completed` report only.
4. If no message/campaign was sent, ignore for restricted-page alerting.
5. If the latest Completed contains `#2022`, alone or mixed with other errors, treat it as a real restriction confirmed by DTR.
6. Extract the restriction-until date/time from the DTR error description. The parser must support both:
   - English: `until July 31 at 3:24 AM`
   - Portuguese: `até 15 de julho às 23:08`
7. Before writing, check SmartBidding's current row. If `RESTRICTED_UNTIL` is empty/null, apply `STATUS=Broadcast`, `RESTRICTED_UNTIL=<date from DTR>`, and append `#2022` to `NOTES` when absent.
8. Validate SmartBidding readback. Only after readback OK should Discord alert say the Dash was updated.

## Alert wording and layout

The restricted-pages channel alert must be human-readable and explicit that the Dash was updated. Use a continuation-style block with a section similar to:

```text
AÇÃO EXECUTADA NA SMART BIDDING
Status das páginas: Broadcast
Restricted Until: data extraída do último Completed da DTR
Validação: readback SB OK antes do alerta
```

Avoid ugly prose add-ons after an alert. If a correction is needed, delete the ugly message and repost a clean block as continuation.

## Pitfalls learned

- Do not call a page “restrita” from SB-only evidence. SB-only means “restriction state recorded in SB,” not DTR-confirmed restriction.
- If a segurador appears duplicated in DTR, the cron may skip it for safety. A targeted/manual apply can be needed after verifying the exact account context and page ID.
- If `#2022` is present but `RESTRICTED_UNTIL` was not written, check whether the date parser failed on localized text before assuming the page is not actionable.
- On-hold rows with active `RESTRICTED_UNTIL` but no `#2022` in notes can exist historically. If Rodolfo asks, list them first; only append `#2022` when explicitly authorized.

## Verification commands/patterns

- After updates, verify current SB rows by `PAGE_ID`/`FB_PAGE_ID` and confirm `RESTRICTED_UNTIL` + `NOTES` readback.
- For audit/listing requests, generate XLSX reports rather than changing data unless Rodolfo explicitly asks to correct.
