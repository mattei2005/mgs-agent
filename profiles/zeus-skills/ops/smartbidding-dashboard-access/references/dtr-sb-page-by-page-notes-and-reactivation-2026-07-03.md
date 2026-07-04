# DTR → SB page-by-page audit — NOTES, restricted reconfirmation, and reactivation rules (2026-07-03)

## Trigger

Use when auditing DigitalTRChat/Bot page reports and syncing SmartBidding Messenger Page fields (`NOTES`, `STATUS`, `RESTRICTED_UNTIL`) for MGS.

## Naming convention fixed by Rodolfo

- **Dashboard da SB** = `https://app.smartbiddingdigital.com` and backend `https://api.jbfdigital.com.br/campaigns/Messenger`.
- **Dashboard do Bot** = `https://digitaltrchat.com/` and derived DigitalTRChat pages/XHR endpoints.

Keep these names separate in reports. Do not blur SB-only restricted state with Bot-derived error-code evidence.

## Correct Bot scan route

The reliable Bot route is page-by-page:

1. Read active bot users from the live migration Sheet (`gid=562940072`), excluding `Removidos acumulado = X`.
2. If tomorrow the `X` is removed, the user re-enters scope automatically on the next run; state must not permanently exclude them.
3. Log into each active Bot user from the Sheet.
4. Enumerate all top-bar seguradores/accounts.
5. Switch segurador and validate the context actually changed before using that segurador label.
6. Enumerate real page options from the page selector.
7. For each page option, query campaigns using `search_page_id=<page option value>`.
8. Use only the newest `Completed` campaign/report for the page.
9. Classify the Sent Response/status from that latest report only.

Never classify pages from a global campaign list with empty `search_page_id`. HTTP 200 from account switch is not proof that the dataset changed.

## NOTES update rule

Rodolfo clarified that `NOTES` should be populated for error/status codes, not for successful sends:

- If latest Bot report is `Sent`: **do not update `NOTES`**.
- If latest Bot report is anything other than `Sent`: append only a short code/status to `NOTES`.
- Do not delete existing `NOTES` content.
- Do not duplicate a code already present in `NOTES`.
- Apply this across **100% of pages found in the Bot scan**, regardless of current SB status (`Broadcast`, `Campaign`, `On-hold`, `Blocked`, etc.).

Canonical appended values:

```text
#2022
#10
#100
#551
PERMISSION
TOKEN
APP_DELETED
OTHER
SEM_COMPLETED
```

For multiple codes, append together in short form, e.g. `#2022 - #551` or `#10 - #100`.

Example:

```text
before: 01 - SEGURADOR - Pendang Novi - EN - XYVLOV
after:  01 - SEGURADOR - Pendang Novi - EN - XYVLOV - #2022
```

## Reconfering current SB restricted pages

Before/while applying new restrictions, reconfirm pages already marked restricted in SB:

1. Pull SB pages where `STATUS=Broadcast` and `RESTRICTED_UNTIL >= today`.
2. For each, validate in the Bot using the same page-by-page route (`search_page_id`, latest Completed).
3. Report buckets:
   - confirmed `#2022`;
   - `#2022 + other codes`;
   - other error without `#2022`;
   - `Sent`;
   - `SEM_COMPLETED`;
   - no reliable Bot match.
4. If reconfirmation proves a page is no longer restricted, update SB accordingly rather than leaving stale restricted state.

## RESTRICTED_UNTIL application rule

Apply/keep `RESTRICTED_UNTIL` only when the latest Bot report contains `#2022`, including mixed codes.

- Set/keep `STATUS=Broadcast` for operational `#2022` rows.
- Set `RESTRICTED_UNTIL` to the same date shown in the Bot report.
- Do not apply `RESTRICTED_UNTIL` for `#10`, `#100`, `#551`, permission, token, app deleted, `OTHER`, `SEM_COMPLETED`, or `Sent` without `#2022`.
- Validate every write by re-reading SB and checking `STATUS`, `RESTRICTED_UNTIL`, `PAGE_ID`, `FB_PAGE_ID`, and `USER_LOGIN`.

## Status reactivation rules

Rodolfo corrected two important edge cases:

### On-hold

- Do **not** automatically reactivate `On-hold` pages based on a Bot `Sent` result.
- By Ciro's rule, an `On-hold` page should not send broadcast, so a `Sent` result is not a reliable signal to flip `On-hold` to `Broadcast`.
- For `On-hold`, update `NOTES` only when a non-`Sent` code/status is found; otherwise leave status unchanged unless Rodolfo explicitly approves reactivation.

### Blocked

- Do **not** reactivate `Blocked` just because Bot data says `Sent`.
- To decide whether a `Blocked` page is no longer blocked, open `https://www.facebook.com/{FB_PAGE_ID}`.
- If Facebook shows normal page content, it can be moved to `Broadcast`.
- If Facebook shows `This content isn't available right now`, deleted/unavailable content, login/access wall, or ambiguous failure, keep `Blocked` and report.
- Example blocked URL from Rodolfo: `https://www.facebook.com/942756295585572` shows Facebook unavailable-content screen and should remain blocked.

## Canary before bulk writes

Before bulk production:

1. Run one-user dry-run and export Excel with columns:
   - `link da pagina`
   - `nome da pagina`
   - `segurador`
   - `data`
   - `codigo dos erros`
2. Validate page counts and context signatures per segurador.
3. Canary one SB write for `NOTES` append and, if applicable, `RESTRICTED_UNTIL`.
4. Confirm readback preserves existing `NOTES`, appends only the code, and does not duplicate.
5. Only then proceed with batch.

## Reporting lesson

When Rodolfo asks whether a count came from SB or Bot, answer the source directly:

- SB restricted count = SB fields (`STATUS`, `RESTRICTED_UNTIL`).
- Bot error-code classification = Bot latest Completed report.

If prior wording conflated them, correct it explicitly before proceeding.
