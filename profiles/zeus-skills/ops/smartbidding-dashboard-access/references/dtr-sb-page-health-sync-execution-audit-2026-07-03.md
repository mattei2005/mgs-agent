# DTR → SB Page Health Sync — Execution Audit Lessons (2026-07-03)

Context: Rodolfo validated a DTR→SmartBidding plan for page-health/restriction sync, then later asked whether the plan was actually executing correctly. The audit found that parts were correct, but the cron had been activated before final reconciliation and the script still had an unsafe edge case.

## Durable lessons

1. **Do not activate recurring apply cron until final reconciliation is clean.**
   The validated sequence is: canary → lote/apply with readback → consolidate final JSON/XLSX → resolve readback/context warnings → REPORT-INFRA/inventory → only then enable cron. If any readback failure or context warning remains, cron must stay paused/commented.

2. **On-hold and Blocked are hard gates for `#2022`.**
   A page with latest Bot/DTR `#2022` is not enough to force SmartBidding `STATUS=Broadcast`.
   - `On-hold + #2022`: do not apply `RESTRICTED_UNTIL` or reactivate automatically; update/report notes only as appropriate.
   - `Blocked + #2022`: only set `STATUS=Broadcast` / `RESTRICTED_UNTIL` if `https://facebook.com/{FB_PAGE_ID}` opens normally. If unavailable/ambiguous, keep `Blocked` and report.

3. **Non-unique DTR account context means no automatic writes.**
   If account/segurador switches produce repeated/global signatures, mark the user as unsafe (`skipped_automatic_writes`) and skip writes for that user. It is better to under-apply than to write based on a fake segurador dimension.

4. **Clearing `RESTRICTED_UNTIL` uses the modal save route, not `update-many`.**
   `PUT /campaigns/Messenger/update-many` can return success but ignore `RESTRICTED_UNTIL=null`. To clear, use `POST /campaigns/Messenger` with the complete editable row payload and `RESTRICTED_UNTIL=null`, then read back the row.

5. **Avoid duplicate logging with wrappers.**
   `dtr-sb-page-health-sync.sh` already pipes through `tee -a` internally. A cron line that also appends `>> same.log` duplicates output. For script wrappers that manage their own log, cron should redirect to `/dev/null` or a separate cron wrapper log.

6. **REPORT-INFRA path.**
   For MGS infra reports, use `/root/mgs-agent/scripts/send-report-infra-embed.sh` (webhook route). Do not manually POST to Discord bot API for #alerts-infra; it can 403 even though the canonical webhook works.

7. **Hermes cron script path pitfall.**
   Hermes `cronjob` script paths resolve under `~/.hermes/profiles/zeus/scripts/` unless workdir/script handling is explicitly arranged. If the real script lives in `/root/mgs-agent/scripts/`, create a tiny wrapper under the Hermes profile scripts directory or schedule the real script through system cron.

## Audit checklist before claiming “executing correctly”

- Check live process state and kill/stop if a logic audit finds a rule violation.
- Compare current script logic against the exact validated thread rules, especially `On-hold`, `Blocked`, and context warnings.
- Verify crontab state: apply cron should be commented/paused until the final report is clean.
- Run a small dry-run after patching (`--user ... --limit-pages ...`) and verify `ok=true` with zero writes.
- Send REPORT-INFRA via the canonical embed script for script/cron/data changes.
