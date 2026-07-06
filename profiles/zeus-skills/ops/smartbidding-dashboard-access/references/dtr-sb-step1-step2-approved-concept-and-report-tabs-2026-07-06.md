# DTR/SB Step 1–2 approved concept + reporting lessons — 2026-07-06

## Context

Rodolfo approved the final Step 1 concept for the DigitalTRChat ↔ SmartBidding page-health workflow and corrected the interpretation of pages with no campaigns/messages.

## Approved Step 1 concept

Step 1 is **inventory/scope hygiene only**. It must not diagnose campaign errors or perform writes.

Order:

1. Read the live migration/control sheet first.
2. Build scope from sheet rows/user/segurador metadata.
3. Apply `Removidos acumulado = X` before opening DTR pages or campaigns.
4. Ignore known workflow noise such as Rodolfo/Geizian accounts.
5. Apply Rodolfo-approved active overrides when the sheet is behind.
6. Resolve DTR credentials by 1Password `username`, not brittle item title.
7. Log into each active DTR user and enumerate every top-bar segurador/account.
8. Detect duplicate segurador/account names before reading pages; do not choose one arbitrarily.
9. Cross-check DTR segurador against the sheet within the same bot user.
10. Classify single active segurador with no pages as report/ignore, not an operational error.
11. Only `VALID_FOR_STEP2` should move into campaign/report diagnosis.

## Final Step 1 classifications

```text
VALID_FOR_STEP2                 active user + valid segurador + page exists
IGNORED_X_SKIP_PAGES            sheet says removed/X; X wins everything
IGNORED_NOISE_SKIP_PAGES        Rodolfo/Geizian/noise for this workflow
OUT_OF_SCOPE_SKIP_PAGES         DTR account not active in the sheet/overrides
REPORT_DUPLICATE_SKIP_PAGES     duplicate active segurador; manual decision needed
NO_PAGES_REPORT_IGNORE          active segurador exists once but has no pages
CREDENTIAL_MISSING              no 1Password match by username
AUTH_OR_CONNECTION_ERROR        real DTR login/page-selector failure
```

## Critical correction: no campaign/message sent is neutral

A page inside a valid segurador that has no campaign/message sent at the time of inspection is **not an error** and **not unsafe context**.

Interpretation:

- It only means no gestor had used that page in a sent campaign yet at that moment/day.
- If a gestor later creates/runs a campaign, a future scan will have data to inspect.
- Do not create NOTES, restrictions, warnings, blockers, or “context unsafe” labels from this alone.

Use a neutral label:

```text
NO_CAMPAIGN_DATA_YET / SEM_CAMPANHA_ENVIADA
```

## Unsafe context rule correction

Do **not** treat empty campaign signatures as repeated/unsafe context. Empty signatures are common for pages without campaigns.

Only block as unsafe context when there are **non-empty campaign/report signatures repeated across different accounts** under the same DTR user. That suggests account switching may be returning the same real campaign context under multiple seguradores.

## Step 2 dry-run report categories

When reporting Step 2 results to Rodolfo, split into plain operational buckets before discussing apply:

```text
Sem campanha enviada            neutral; no data yet, not error
Sent / OK                       latest report indicates normal send
Páginas com erro real           actual error codes from DTR latest report
Sem match no SB                 DTR page could not be matched to SB row
Ações planejadas em dry-run     rows where script would write if apply=true
```

This reduces confusion; do not lead with raw internal labels like `SEM_COMPLETED` or `unsafe_context_users` unless they are still materially valid.

## Google Sheet delivery lesson

For Rodolfo-facing review, creating category tabs in the target Sheet is preferred over sending a dense single Excel. Use one tab per bucket with the same detailed columns from the `Paginas` report. Validate tab row counts by reading/exporting each tab after upload/paste.

Example tabs used:

```text
Sem campanha enviada
Sent OK
Paginas com erro real
Sem match no SB
Acoes dry-run
```

Keep tab names ASCII if it helps API/browser stability (`Paginas`, `Acoes`), but labels in messages can keep Portuguese accents.
