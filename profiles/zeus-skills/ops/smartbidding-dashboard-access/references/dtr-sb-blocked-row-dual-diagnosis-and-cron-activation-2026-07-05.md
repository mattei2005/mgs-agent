# DTR→SB page-health sync — Blocked dual diagnosis + cron activation (2026-07-05)

## Context

During the DTR→SmartBidding page-health sync activation, 7 FINANCETOPFEED rows under segurador **Barbara Cristina** were incorrectly changed from `Blocked` to `Broadcast` because their public Facebook URLs opened.

Rodolfo corrected the operating model: `Blocked` is a state, not a cause. A publicly reachable Facebook page does not prove MGS has operational access through the segurador/Facebook profile.

## Durable rules

### `Blocked` requires dual diagnosis

For SB Messenger Page rows with `STATUS=Blocked`, never reactivate solely from `https://facebook.com/{FB_PAGE_ID}` returning available.

Classify before any `Blocked → Broadcast` action:

1. **Page blocked/down** — public URL or operational access fails; keep `Blocked`.
2. **Segurador/profile fell** — page may still be public, but MGS lost access through the segurador/Facebook profile; keep `Blocked` until profile access is recovered or the pages are moved.
3. **False blocked / access restored** — only then can the row be reactivated, after validating both page availability and operational segurador/profile access.

Public URL availability is only a diagnostic signal. It separates “page likely public” from “page unavailable”; it is not a reactivation gate.

### Do not append `SEM_COMPLETED` to active restricted rows

If a row already has active `RESTRICTED_UNTIL`, the page may not run/schedule normally. A `SEM_COMPLETED` result during that active restriction can be expected noise, not a new actionable error.

Rule: skip `NOTES` append for `SEM_COMPLETED` when `RESTRICTED_UNTIL >= today`; do not create false failures by trying to save that note.

### Unsafe DTR account context handling

For users where `.account_switch` signatures are not unique across seguradores, do not hard-block the whole user if exact SB row matching is available.

Safer fallback:

- keep a warning: `account_context_signatures_not_unique`;
- process deduped unique SB row IDs only;
- skip duplicate occurrences for the same SB row within that bot user;
- never write when the SB match is ambiguous.

### SB save fallback lesson

Some SB rows reject `NOTES` updates with HTTP 500 even after modal-style payload fixes. Do not keep retrying the same write path indefinitely. Reclassify the row if the note itself is non-actionable under the current state, e.g. `SEM_COMPLETED` on an active restricted row.

## Activation checklist used

Before enabling cron:

1. Patch canonical script rules.
2. Run canary/dry-run on the corrected user/case.
3. Run full dry-run with all active Sheet users.
4. Ensure full dry-run has no fatal errors.
5. Enable root crontab with `flock`.
6. Update CRONS/inventory.
7. Run/observe apply or next scheduled run and report residual write failures separately.

## Operational outcome

Cron enabled at:

```text
30 7,15 * * * flock -n /var/lock/dtr_sb_page_health_sync.lock /root/mgs-agent/scripts/dtr-sb-page-health-sync.sh --apply --quiet-noop >/dev/null 2>&1
```

The cron is quiet on no-op and uses the wrapper script, which sources `.env` with `set -a`/`set +a` and logs to `/root/mgs-agent/logs/dtr-sb-page-health-sync.log`.

## Key pitfall

Do not report “operationally corrected” if a status change was made from an incomplete diagnosis. In this class of task, a wrong automated reactivation must be reverted immediately before continuing with cron activation.
