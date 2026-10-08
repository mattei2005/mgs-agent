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
6. Check snapshots hourly and basic health at the approved 15-minute cadence. Timestamp interpretation and the backup-age tolerance must remain explicit in the config; a COMPLETED snapshot is not a restore test.
7. Preserve the approved one-per-day 08:28 financial-intake coincidence and 35-second stagger only under its exact authorization. Re-audit eight civil dates before changing the scheduler. Never reclassify financial intake as an infrastructure baseline merely because it has four runs in one hour.
8. Persist outbox intent before POST and returned message ID before GET. Retry only GET after accepted delivery. Known HTTP 4xx rejection may retry POST; 5xx, timeout or uncertain response must reconcile by the unique embed footer and never repost blindly. Cancel an unsent rejected alert if a fresh observation proves it no longer applies.
9. Verify log rotation in the live filesystem rather than assuming a historical `/etc/logrotate.d/mgs-agent` file exists. This monitor owns `config/runcloud-logrotate.conf` and `data/runcloud-logrotate.status`, invoked under its existing lock: daily/1MiB rotation, `copytruncate`, `rotate -1`, no compression or expiry deletion. Archives preserve history; shortening retention or deleting logs needs its separate authorization. Exercise a scratch fixture to prove the archive preserves the original content.
10. Keep the watchdog aware of the explicit minute list: 60-minute log tolerance for this 15-minute monitor. Successful state reads and a fresh log do not prove delivery; require exact Discord GET.

## Validation

- Run the exact production interpreter: `/usr/bin/python3 -B /root/mgs-agent/tests/test_monitor_runcloud.py`.
- Run `--dry-run`; require no production state mutation or post.
- Exercise a real apply cycle, exact cron readback and a real scheduled cycle.
- Validate one informational activation embed without mentions; do not publish fake incidents as smokes.
- Validate fixtures for thresholds, transient/unknown observations, dedupe, failure/retry, ambiguous transport, historical backup failure, archived/private exclusion and watchdog cadence.
- Inventory script/config/state/cron/skill changes; checkpoint and REPORT-INFRA with exact readback. Keep the financial cron unchanged.
