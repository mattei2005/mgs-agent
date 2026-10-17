# RunCloud — initial read-only monitoring

Use for RunCloud alerts in the dedicated channel. Resolve actual operational values from `data/runcloud-alert-config.json`, never from this reference or an old email.

## Canonical artifacts

- Runner: `/root/mgs-agent/scripts/monitor-runcloud.py`.
- Config: `/root/mgs-agent/data/runcloud-alert-config.json`.
- State/outbox: `/root/mgs-agent/data/runcloud-alert-state.json`, mode 0600.
- Schedule proof: `data/runcloud-alert-schedule-validation.json`.
- Delivery receipt: `data/runcloud-alert-activation.json`.
- Tests: `tests/test_monitor_runcloud.py`.
- Initial rollback: `backups/runcloud-alerts-1557826145578127361/crontab.before`; restore only the approved cron scope, preserving later unrelated changes.

## Operational boundaries

1. Keep initial scope to connection, expected services, disk and active scheduled backups on the explicitly configured Inc hosts. Memory/load, SSL, SSH/security and remote remediation are separate later phases, not implied active coverage.
2. Use one canonical 1Password read per cycle for the existing RunCloud API token; never cache the token on disk. Deliver through existing Zeus bot auth without creating a webhook or another secret.
3. Obtain app-to-server bindings from projected `/webapps` objects. Never persist or print pullKey1/pullKey2. Alert backups by numeric ID only, not private domain labels. Preserve distinct backup IDs even when labels match.
4. Treat RunCloud connection/online as provider predicates; they do not prove public website behavior. A disconnected agent is not evidence of a down host. Expected services are explicit per host; intentionally stopped services are not incidents.
5. Confirm critical observations by another GET. Warnings require consecutive observations; unavailable observations break a candidate streak and never close a published incident. An older failed backup superseded by a completed snapshot is historical, not active failure.
6. Rodolfo1561035336010829825 supersedes the original15-minute health/hourly-snapshot cadence: inspect basic health every2hours using `4 0-23/2 * * *` Eastern and inspect backup status with `backup_cadence_seconds=86400`. This changes only inspection, never backup execution. Preserve `backup_max_age_hours=36`; a COMPLETED snapshot is not a restore test. The collector must use the configured cadence rather than a hardcoded3600seconds.
7. The former08:28 financial-intake coincidence1557826145578127361 is historical: the reduced schedule no longer needs it. Preserve the35-second stagger and keep financial schedules unchanged. Re-audit eight civil dates before any scheduler change; use zero non-baseline operational collisions and the least-contended baseline-compatible minute.
8. Persist outbox intent before POST and returned message ID before GET. Retry only GET after accepted delivery. Known HTTP 4xx rejection may retry POST; 5xx, timeout or uncertain response must reconcile by the unique embed footer and never repost blindly. Cancel an unsent rejected alert if a fresh observation proves it no longer applies.
9. Verify log rotation in the live filesystem rather than assuming a historical `/etc/logrotate.d/mgs-agent` file exists. This monitor owns `config/runcloud-logrotate.conf` and `data/runcloud-logrotate.status`, invoked under its existing lock: daily/1MiB rotation, `copytruncate`, `rotate -1`, no compression or expiry deletion. Archives preserve history; shortening retention or deleting logs needs its separate authorization. Exercise a scratch fixture to prove the archive preserves the original content.
10. Keep the watchdog aware of the exact current schedule: `4 0-23/2 * * *` has a3-hour log-age threshold, superseding the original60-minute tolerance. Successful state reads and a fresh log do not prove provider availability or delivery; require the exact collection state and Discord GET when a message was sent.

## API quota diagnostic boundary

- On HTTP 429, inspect the sanitized response body and `Retry-After`/rate-limit headers before treating the failure as transient. `Monthly API quota limit exceeded` with zero remaining requests is a monthly quota block, not proof of a server outage. Stop interactive retries, preserve unknown observations and open incidents, and validate public websites or approved guest probes independently. Do not clear an incident from a fresh log alone, bypass the quota with another identity, change billing, or promise recovery before quota availability is verified. Keep any proposed scheduler/consumer change separate from the read-only diagnosis.
- The monitor persists `api_control` in its existing locked state: honor the later valid `Retry-After` (seconds or HTTP date) and `X-RateLimit-Reset`, never cap a monthly wait at30seconds, and stop all endpoints after the first429. Until the deadline, retain the unavailable incident and skip both the API and its 1Password lookup; cron/outbox remain active. With missing/invalid headers use a24-hour monthly probe or60-second transient backoff. Clear the control only after an actual successful API response; full monitoring recovery still requires a complete valid collection. Exercise `tests/test_runcloud_quota.py` plus the original suite before deployment.
- Budget the complete account, not a single cycle: three server checks use nine nominal calls per healthy cycle, and listing snapshots for93 active backups can push a full cycle to108calls. The former15-minute health/hourly-backup model exceeded the10,000 monthly quota by design; the current approved2-hour health/daily-backup-status model projects6,417 nominal calls over31days before retries or other consumers. Distinguish observed request attempts from provider-billed successful usage; historical logs do not prove exclusive attribution or one billing-period total. Present coverage/detection impact before changing the current approved cadence; quota containment is not permission to reduce freshness silently.

## Validation

- Run the exact production interpreter: `/usr/bin/python3 -B /root/mgs-agent/tests/test_monitor_runcloud.py`, `tests/test_runcloud_quota.py` and `tests/test_runcloud_cadence.py`.
- Validate crontab with native `crontab -n` before applying. Use a short relative candidate filename with `cwd` inside protected profile scratch: this host's crontab truncates long absolute input filenames. On preflight failure, prove the live crontab is unchanged before retrying; never apply an unvalidated candidate.
- Run `--dry-run`; require no production state mutation or post.
- Exercise a real apply cycle, exact cron readback and a real scheduled cycle.
- Validate one informational activation embed without mentions; do not publish fake incidents as smokes.
- Validate fixtures for thresholds, transient/unknown observations, dedupe, failure/retry, ambiguous transport, historical backup failure, archived/private exclusion and watchdog cadence.
- Inventory script/config/state/cron/skill changes; checkpoint and REPORT-INFRA with exact readback. Keep the financial cron unchanged.
