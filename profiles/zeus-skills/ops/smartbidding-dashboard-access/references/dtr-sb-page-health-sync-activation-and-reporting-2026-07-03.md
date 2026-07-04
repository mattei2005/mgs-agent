# DTR → SB Page Health Sync — activation/reporting lessons (2026-07-03)

## Context

During the final activation of the DTR → SmartBidding page-health workflow, Rodolfo clarified that two distinct systems were being conflated in reports:

1. **SB restricted-page monitor** (`monitor-sb-restricted-pages.sh`) reads SmartBidding live and knows `RESTRICTED_UNTIL` date only.
2. **DTR/Bot page-health sync** (`dtr-sb-page-health-sync.sh`) reads DigitalTRChat latest Completed reports and knows actual message status/code/time.

The SB-only report had shown placeholder text such as `hora DTR pendente` / `DTR pendente`, which looked like real DTR data. This is misleading and must not recur.

## Durable rules

### 1. Do not present placeholders as data

If a report is SB-only, label the source explicitly:

```text
Expira SB     Origem
YYYY-MM-DD    SB-only; DTR não lido
```

Do not include columns named `Código erro`, `Hora DTR`, or similar unless DTR was actually queried and parsed in that same run.

### 2. Keep the two cron paths conceptually separate

- SB-only monitor: detects current SB rows with `STATUS=Broadcast` and active `RESTRICTED_UNTIL`.
- DTR sync: logs into Bot/DigitalTRChat, scans latest Completed report per page, updates SB `NOTES`/`RESTRICTED_UNTIL` according to validated rules.

Never assume the SB-only monitor enriched with Bot data unless the code path explicitly calls the DTR checker.

### 3. Unsafe DTR context means skip writes

If DTR account/segurador switching yields repeated/non-unique campaign signatures or otherwise proves that the account context did not really change, mark the user as unsafe and skip automatic writes for that user.

Recommended error marker:

```json
{
  "warning": "account_context_signatures_not_unique",
  "action": "skipped_automatic_writes"
}
```

The report may still mention the user as skipped/manual-review, but must not write `NOTES`, `STATUS`, or `RESTRICTED_UNTIL` from that ambiguous context.

### 4. Katherine Cook readback lesson

A prior readback failure showed `NOTES` persisted while `RESTRICTED_UNTIL` did not clear in the same logical run. The final safe path is to verify the exact row by ID after any clear, and if needed perform/validate a separate single-row clear with readback. Do not mark the sync closed until `RESTRICTED_UNTIL` readback is actually empty/null.

### 5. Activation sequence

Before enabling recurring apply mode:

1. Validate a canary write with live readback.
2. Resolve or explicitly quarantine unsafe context users.
3. Recheck any prior readback_failed rows by exact SB row ID.
4. Install cron with `flock`.
5. Start one immediate apply run only if logs are controlled and summarized later.

## Hermes cron side note

A Hermes cronjob failed because it pointed to a profile-local script path:

```text
/root/.hermes/profiles/zeus/scripts/sb-utility-controlled-tests-readback.sh
```

while the real script lived under:

```text
/root/mgs-agent/scripts/sb-utility-controlled-tests-readback.sh
```

When creating Hermes cronjobs with a script, ensure the script path is either profile-local and exists, or pass the correct project workdir/script path. For one-shot readbacks, verify `cronjob list` and the script path before relying on the scheduled message.
