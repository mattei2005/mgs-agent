# DTR → SB page-health sync — apply-run lessons (2026-07-04)

## Trigger

Use when operating `/root/mgs-agent/scripts/dtr-sb-page-health-sync.py` / `.sh` for live DigitalTRChat → SmartBidding synchronization: `NOTES`, `STATUS`, and `RESTRICTED_UNTIL`.

## Durable lessons from the apply run

### 1. Migration Sheet CSV endpoint

The Google Sheets export endpoint:

```text
/export?format=csv&gid=562940072
```

can return HTTP 400 for the migration/control Sheet even when the sheet is public/readable. Prefer the stable gviz CSV endpoint:

```text
/gviz/tq?tqx=out:csv&gid=562940072
```

This preserves the sheet-first scope gate: include only active bot users and exclude `Removidos acumulado = X`.

### 2. 1Password DigitalTRChat item discovery

DigitalTRChat items can have duplicate titles or spacing variants. Do not retrieve by title alone after a broad match. Discovery should:

1. list candidate items broadly where title contains `digitaltrchat`;
2. retrieve by 1Password item ID, not title;
3. match the revealed `username` field against active users from the live Sheet.

This avoids `More than one item matches "digitaltrchat.com"` and prevents brittle title-prefix misses.

### 3. Full apply is not complete just because many writes succeed

A full apply can successfully write hundreds of rows but still finish `ok=false` because some rows fail SmartBidding save/readback or DTR context safety. Treat the run as partial when either exists:

```text
errors[].update_failed
errors[].warning == account_context_signatures_not_unique
```

Do not enable the recurring cron after a partial apply. First isolate the failed rows, implement/validate a fallback, then rerun/reconcile.

### 4. SmartBidding 500 failure buckets

Observed SB HTTP 500 failures can happen on:

```text
NOTES only
STATUS + RESTRICTED_UNTIL
NOTES + STATUS + RESTRICTED_UNTIL
```

The existing safe sequence is still correct for many rows: save `NOTES` via modal POST, then apply `STATUS`/`RESTRICTED_UNTIL` through `update-many`, with exact readback. For 500 rows, do not assume success; keep them in the report and build a targeted fallback after inspecting the row payload/status.

### 5. Context-unsafe users are intentionally skipped

If `account_context_signatures_not_unique` appears, automatic writes for that bot user must be skipped. This means DTR account switching may be returning repeated/ambiguous context and errors could be assigned to the wrong segurador/page. Report the exact users and handle separately; do not force writes.

## Safe execution pattern

```bash
# Canary first
/root/mgs-agent/scripts/dtr-sb-page-health-sync.sh --apply --limit-users 1 --limit-accounts 1 --limit-pages 5 --max-writes 1

# Full apply only after canary is clean
flock -n /var/lock/dtr_sb_page_health_sync.lock \
  /root/mgs-agent/scripts/dtr-sb-page-health-sync.sh --apply
```

## Completion gate before enabling cron

Cron is eligible only when the latest reconciliation has:

- no `update_failed` rows left unhandled;
- no readback mismatch;
- unsafe DTR context users either fixed or intentionally excluded by a documented rule;
- final JSON/XLSX report generated;
- backups saved;
- infra inventory/reporting updated if scripts/config changed.
