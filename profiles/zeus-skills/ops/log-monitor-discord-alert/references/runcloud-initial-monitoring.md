# RunCloud monitoring: collection, quota and transport

Use for RunCloud connection, expected services, disk and backup-status monitoring. Resolve current targets, cadence, permissions and activation state from the canonical artifacts; this procedure is not an independent source of current production settings.

## 1. Freeze the current contract

1. Read `data/runcloud-alert-config.json`, `data/runcloud-alert-state.json`, the exact root cron entry and the matching runtime artifact in `data/infra-inventory.json`.
2. Reconcile the runner `scripts/monitor-runcloud.py`, watchdog `scripts/monitor-cron-stale-logs.sh`, schedule proof `data/runcloud-alert-schedule-validation.json` and activation receipt `data/runcloud-alert-activation.json`. Use the latest validated checkpoint/report to resolve superseded receipts.
3. Record configured hosts, expected services, health schedule, `backup_cadence_seconds`, `backup_max_age_hours`, timezone, stagger, locks and timeout. Treat memory/load, SSL, SSH-security checks and remote remediation as separate capabilities unless the active contract explicitly includes them.
4. Preserve an exact rollback copy of the affected script/config/scheduler before mutation. Restore only the approved scope, preserving unrelated concurrent changes; do not delete evidence or backups incidentally.

## 2. Budget the full workload before proposing capacity

1. Inventory API consumers across root/system cron, operational Hermes profiles, systemd and application schedulers. Separate recurring consumers from manual inventory/deployment helpers; code references alone do not prove scheduled use.
2. Parse retained monitor logs programmatically. Count emitted request attempts, successful collections and blocked collections separately. Do not equate attempts with provider-billed calls, claim exclusive account attribution, or label undated archives as one billing period.
3. Count connection, health and service requests per host; list pagination; snapshot-history requests per eligible backup; confirmation reads; and retries. A small health cadence can hide a much larger per-backup fan-out.
4. Calculate a full billing-period projection with tools, including a long-month case and headroom for retries, inventory growth and other consumers. Label it a nominal projection, not measured consumption.
5. Compare source choices before recommending a paid add-on or reduced freshness. Present the exact new intervals and detection impact before changing cadence. Distinguish checking backup status from executing backups; reducing the former must not change the latter.

## 3. Handle quota exhaustion without hammering the provider

1. On HTTP 429, inspect the bounded response body and rate-limit headers. The exact message `Monthly API quota limit exceeded.` identifies a monthly block, not a server outage.
2. Stop the entire API collection after the first 429. Do not retry each remaining host or backup endpoint against an account-wide exhausted allowance.
3. Persist only known fields in the existing locked `api_control` state: kind, observation time, HTTP status, quota limit/remaining and retry deadline. Never persist arbitrary response bodies or credential values.
4. Honor the later valid `Retry-After` and `X-RateLimit-Reset`. Parse `Retry-After` as seconds or an HTTP date; reject non-finite and out-of-range timestamps. Do not truncate a monthly wait to a short retry sleep. Without valid headers, the current implementation uses a bounded daily monthly-quota probe or a short transient-rate-limit backoff; test the actual constants before changing them.
5. Before retrieving the RunCloud credential, check persistent cooldown. Blocked cycles must skip both RunCloud API calls and its 1Password lookup while keeping cron and Discord outbox processing operational.
6. Preserve unknown host/backup observations, existing incidents, the last successful backup-check timestamp and pending deliveries. Neither a fresh log nor a deferred cycle proves provider recovery.
7. Allow a fresh probe after the deadline. Clear cooldown only after a real successful API response; announce monitoring recovery only after a complete valid collection. A controlled recovery fixture does not prove that the live provider has recovered.
8. When answering a reset-date question, convert the persisted provider timestamp with timezone-aware tools. Attribute it to the API headers; do not present it as a confirmed billing renewal date without account-level evidence.

## 4. Change cadence end to end

1. Apply `context/cron-scheduling-policy.md`: inventory every scheduler, normalize timezones, expand eight civil dates, classify continuous/dense baselines, inspect resources/durations and require zero non-baseline operational conflicts.
2. Choose the least-contended compatible minute, preserving approved cadence and any deterministic stagger. Historical overlap exceptions are not automatically applicable to a new schedule.
3. Check that the collector actually reads `backup_cadence_seconds`; changing JSON alone does nothing when the implementation hardcodes an interval. Reject invalid interval types/values and test just-before, exact-boundary and explicit-force behavior.
4. Update the stale-log watchdog in the same change. Its tolerance must match the new health interval plus a stated grace period, rather than inheriting a permissive daily fallback.
5. Back up the live crontab, construct a candidate with only the authorized entry/comment changes, inspect its diff and use native `crontab -n` syntax validation before applying. If a preflight fails to open an existing long-path candidate, prove that the live crontab is unchanged and retry with a short relative filename and `cwd` inside protected profile scratch.
6. Apply only if the frozen live crontab still matches. Require exact readback of schedule, enabled runner, timezone, lock, stagger, timeout and delivery target; rerun the global collision audit afterward.
7. Preserve financial schedules and actual backup jobs. Retain superseded configuration/exception evidence and update current inventory and institutional pointers instead of leaving two active cadence descriptions.

## 5. Evaluate a hybrid SSH/API design before requesting new access

This section is a read-only readiness procedure and rollout acceptance contract, not evidence that an SSH collector is already deployed.

1. Inspect the current consumer's code to establish whether it uses provider HTTPS calls, direct SSH, or both. A developer's screenshot is a proposal/setup claim; a stored key is not proof that the agent uses it.
2. Resolve the exact authorized host/login items through `scripts/mgs-op-with-service-account.sh`. Filter item metadata before output, and keep credential values in memory. Do not ask Rodolfo to generate or paste credentials before checking whether existing authorized access already supports discovery.
3. Run a bounded read-only probe on each configured host. Preserve `StrictHostKeyChecking=yes` and the canonical pinned known-hosts file. With an existing password-based helper, pass the password through an inherited pipe to `sshpass -d`, not argv, logs or a plaintext temporary file. Do not weaken host verification or create an access path to make a probe pass.
4. Collect only readiness evidence: actual user/home, readability of disk and service state, installed unit names, and `authorized_keys` existence/mode/entry count/hash. Never print key material. Map provider service aliases to real guest units; an installed PHP version or template unit is not automatically an expected running service.
5. Separate predicates: guest service state, disk and local logs can be read without the RunCloud API; provider connection state and managed backup completion/storage records may still require it. A local backup file does not prove successful offsite delivery. Preserve these distinctions in alerts.
6. If a dedicated production key is needed, freeze a separate credential-installation proposal: exact hosts/users, dedicated monitor identity, private-key storage, allowed read-only operations, public-key additions and preserved existing access. Do not reuse a developer's identity or an unrelated narrowly scoped key by implication; RSA is an option, not the definition of SSH access.
7. Keep discovery separate from the production credential gate. For an owner asking what they must do, explain the verified readiness and request only the exact remaining confirmation; do not delegate agent-owned setup steps to them.
8. Before claiming restricted access is active, require successful allowed probes and rejection of arbitrary commands, shell/PTY and forwarding as applicable to the approved design. Do not silently fall back to a broader privileged credential when a restricted command is denied. These are acceptance requirements, not permission to install unconfirmed keys or alter SSH/firewall policy.
9. Cut over only after the collector, credential path and failure semantics are tested. Preserve the approved hosts, intervals, locks, outbox and provider-only backup checks unless separately changed. Keep SSH authentication/connection failure distinct from evidence that a target service is stopped.

## 6. Preserve collection and delivery semantics

- Obtain app-to-server bindings from projected `/webapps` objects; never persist deployment/pull keys or raw webapp objects. Alert backups by numeric ID without private domain labels.
- Treat provider online/agent-connected flags as provider predicates, not proof of public website behavior. Independently validate public availability when required.
- Confirm critical provider observations with another GET when quota permits. Warnings require consecutive observations; unavailable observations break candidate streaks and never resolve a published incident.
- An older failed backup superseded by a completed snapshot is historical, not an active failure. Preserve explicit timestamp interpretation and the configured age tolerance; a completed snapshot is not a restore test.
- Persist outbox intent before POST and returned message ID before GET. After accepted delivery retry GET only. Reconcile ambiguous POST outcomes by the unique footer/nonce instead of reposting blindly; cancel unsent rejected alerts only when fresh evidence invalidates them.
- Deliver with the existing Zeus bot, without a recurring webhook-secret lookup. Require exact Discord GET for actual messages; do not publish fake incidents as smoke tests.
- Verify the live log-rotation configuration and retained history. Exercise a scratch fixture for rotation; shortening retention or deleting logs is a separate operation.

## 7. Test and close

1. Exercise the deployed interpreter with `tests/test_monitor_runcloud.py`, `tests/test_runcloud_quota.py` and `tests/test_runcloud_cadence.py` before promotion. Run new regressions against the old implementation first, then rerun all relevant suites on the candidate and deployed files.
2. Cover monthly versus transient 429, finite/date-based deadlines, persistent cooldown across processes, zero API/credential calls while blocked, unknown-state preservation, configured backup intervals, watchdog tolerance and delivery deduplication/readback.
3. Run `--dry-run` and prove production state is unchanged. Exercise the exact installed command, including its lock, stagger, timeout and log redirection; inspect resulting state as well as exit status. A deliberate nonzero status while quota is unavailable is not a failed containment fix or successful collection.
4. Distinguish manual execution of the installed command, native scheduler readback and an actually observed future scheduler tick. Never report one as the other or create an extra production job just to simulate scheduling evidence.
5. Reconcile inventory, canonical configuration, schedule validation, checkpoint, procedural learning and REPORT-INFRA. Report deployment success separately from any provider block; name an owner decision only when one truly remains.
