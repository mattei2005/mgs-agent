# DTR/SB Step 1 approved concept + Step 2 neutral classifications — 2026-07-06

## Context

Rodolfo approved the final Step 1 concept for the DigitalTRChat → SmartBidding page-health workflow after correcting how missing campaign data and unsafe-context warnings should be interpreted.

## Approved Step 1 concept

Step 1 is inventory/scope hygiene only. It must not diagnose campaign errors or apply SmartBidding writes.

Correct sequence:

1. Read the migration/control sheet first.
2. Build active scope from sheet rows/users/seguradores.
3. Apply removals (`X`) before opening DTR page/campaign details.
4. Ignore known workflow noise such as Rodolfo/Geizian accounts.
5. Apply Rodolfo-confirmed active overrides when the sheet lags reality.
6. Resolve DigitalTRChat credentials by 1Password `username`, not brittle item title.
7. Log into each active DTR user and enumerate all top-bar seguradores/accounts.
8. Detect duplicate segurador/account names before reading pages. Duplicate active segurador = report and skip automatic page audit; never choose an arbitrary duplicate.
9. Cross-check DTR account names against the sheet within the same bot user.
10. For active, non-duplicate accounts, list pages.
11. Segurador with zero pages is report/ignore, not an operational error.
12. Only active, non-X, non-duplicate accounts with pages become `VALID_FOR_STEP2`.

## Neutral classification: no campaign/message sent yet

A page inside a segurador with no campaign/report/message sent at inspection time is not an error.

Interpretation:

- It only means that, at that moment/day, no gestor had used that page in a sent campaign yet.
- If a gestor later creates/runs a campaign for that page, a future scan will have data to inspect.
- Do not treat this as unsafe context, page failure, SB failure, or action pending.
- Do not write SB `NOTES` for this alone.

Use a neutral label such as:

```text
NO_CAMPAIGN_DATA_YET
SEM_CAMPANHA_ENVIADA
```

Avoid legacy/error-looking labels in user-facing reports, especially `SEM_COMPLETED`, unless explicitly explaining raw internal data.

## Unsafe context rule

The old criterion `context_signatures_unique < accounts` was too sensitive because empty/no-campaign signatures repeated naturally.

Correct blocker:

- Only mark DTR account context unsafe if **non-empty campaign/report signatures** repeat across different accounts/seguradores.
- Empty signatures/no campaign data do not prove context leakage.
- If repeated non-empty campaign IDs/signatures appear across accounts, block automatic writes for that affected user and report the repeated signatures.

## User-facing reporting style

When explaining Step 1/Step 2 to Rodolfo, avoid dense error jargon. Present simple operational buckets:

- Seguro para aplicar
- Diagnóstico/manual
- Neutro/não erro
- Bloqueio real

Translate internal labels into business meaning. Example: say `sem campanha enviada` instead of leading with `SEM_COMPLETED`/`NO_CAMPAIGN_DATA_YET`.
