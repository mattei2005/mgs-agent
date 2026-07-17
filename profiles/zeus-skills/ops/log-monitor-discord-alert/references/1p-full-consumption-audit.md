# Full-system 1Password consumption audit — MGS

Use this reference when a Service Account approaches rate limits or Rodolfo asks for hourly/daily/monthly consumption by automation.

## Mandatory inventory scope

Do not stop at the root crontab. Enumerate all of these before calculating:

1. Root crontab and `/etc/cron*`.
2. Hermes scheduler jobs for **every profile**, especially:
   - `/root/.hermes/profiles/zeus/cron/jobs.json`
   - `/root/.hermes/profiles/atena/cron/jobs.json`
   - `/root/.hermes/profiles/ares/cron/jobs.json`
   - `/root/.hermes/profiles/legacy-agent/cron/jobs.json`
3. Scripts referenced by those jobs, including wrapper → Python/shell dependencies.
4. systemd services/timers and Git hooks.
5. Conditional/lazy alert paths separately from unconditional credential reads.
6. On-demand agent/CLI sweeps separately from scheduled baseline.
7. Current `op` processes; ignore the persistent `op daemon` itself as a periodic consumer.

A root-crontab-only audit can miss the dominant consumers. In the 2026-07-10 audit it missed Zeus Hermes jobs `meta-app-roles-watch` and `b011-dtr-link-watch`, which together represented roughly 97% of the nominal request budget.

## Request accounting

Use current official 1Password documentation for exact multipliers. Conservative defaults:

- ordinary command / `op service-account ratelimit`: 1 request;
- `op item get` by item/vault names: up to 3 reads;
- `op item get` with item ID **and** vault ID: 1 read;
- `op item list --vault <name>`: up to 3 reads.

For each automatic consumer report:

```text
requests/run × runs/hour × 24 × 30
```

Show both:

- **Nominal/conservative projection** from code paths and documented multipliers.
- **Observed runtime projection** from the live rate-limit window.

Do not present one as the other. Locks, scheduler delays, daemon caching and skipped overlapping runs can make observed usage lower than nominal.

## Live projection

From `op service-account ratelimit --format=json`, for the token read window:

```text
elapsed_seconds = 3600 - reset
observed_per_hour = used / elapsed_seconds × 3600
observed_per_day = observed_per_hour × 24
observed_per_30d = observed_per_day × 30
```

Compare both hourly and account-daily limits. The daily limit can fail even when the hourly window looks safe. Project exhaustion time and compare it with the account reset time.

If the token-hour row has `used=0` and `reset=0` because the hourly window just rolled over, do not report an observed rate of zero. Use the account-daily row instead:

```text
elapsed_daily_seconds = 86400 - account_reset
observed_per_hour = account_used / elapsed_daily_seconds × 3600
```

Label this as a daily-window average, not an instantaneous hourly rate. Near the daily reset, it is usually the best live reconciliation source.

Shell pitfall: never pipe JSON into `python3 - <<'PY' ...`; the heredoc owns stdin and the piped JSON is lost. Use `python3 -c`, a temporary file, or pass the JSON path as an argument.

The rate-limit query itself is a request. Keep production monitoring low-frequency; MGS canonical rate-limit monitor cadence is once per hour, with transition-only anti-spam alerts at 50% and critical at 90%.

## Consumer classification

- **Fixed:** credential lookup occurs on every successful run.
- **Conditional/lazy:** credential is fetched only when an alert/recovery or other branch executes. Verify call sites, not just literal `op` strings.
- **Event-driven:** e.g. Git post-commit hook; estimate from actual event counts over 24h and 7d.
- **On-demand:** manual agent tasks, diagnostics and DTR sweeps; exclude from fixed baseline but report potential burst cost.
- **Enabled but ineffective:** scheduler entry is enabled, but the current execution fails before reaching `op`. Count its current effective consumption as zero, report the failure separately, and show the additional projection if restored. Never silently include a broken job in the “as running today” baseline.
- **Autonomous zero-1Password:** scheduled jobs that operate from local OAuth, dedicated SSH/deploy keys, bot credentials already local to the profile, cached browser state, or purely local checks. List these explicitly in a system-wide audit; Rodolfo wants visibility into what Zeus runs autonomously even when it costs zero 1Password requests.

For recurring jobs, distinguish three totals:

1. **Configured nominal:** what all enabled schedules would consume if their intended code paths completed.
2. **Effective current:** only jobs that actually reached the credential path in the inspected period.
3. **Observed account:** live account counter normalized by elapsed time.

A strong reconciliation is when effective current approximately matches the account counter. Explain the residual as conditional alerts, manual/on-demand work, telemetry timing, or the audit probes themselves; do not force exact equality.

## Shared resolver and fail-closed contract — 2026-07-12

Recurring MGS consumers use `/root/mgs-agent/scripts/mgs-op-item-resolver.py` instead of field-by-field `op item get` loops.

Security and cache contract:

- `/root/.cache/mgs/1password-metadata/` contains only vault/item IDs, scoped item titles and DTR usernames; never credential values;
- cache directory is `0700`; JSON and lock files are `0600`; writes are atomic;
- cache schema changes must increment `CACHE_SCHEMA` so older broader caches are rejected immediately;
- use separate bounded locks for item-index and DTR-map refreshes; on lock timeout, a valid schema/vault stale metadata cache may be reused, but secrets are never cached by this resolver;
- `force_refresh` must propagate through the item index; a title that resolves to a deleted/renamed item may refresh the index and retry exactly once—never loop;
- use vault ID + item ID for full-item reads and parse fields in memory.

Fail-closed consumer rules:

- **Dry-run means no side effects:** no Sheets/Discord writes, no operational state save, and no report artifacts. Verify state hashes and artifact counts before/after.
- **Meta App Roles:** sheet reconciliation accepts only app keys successfully checked in the current cycle. A failed app's old snapshot preserves its sheet cells and must never look “fresh.”
- **B011:** use tri-state verdicts `linked`, `unlinked_confirmed`, `unknown`. Only `unlinked_confirmed` may write `X`; `unknown` preserves the cell. Alert infra only after two consecutive inconclusive runs. Keep and use stable item IDs from the DTR map rather than reverting to titles.
- **DTR/SB daily audit:** stop before SB comparison when any 1Password item is missing, any resolver/collector error exists, or `login_ok != targeted_users`. On incomplete execution, do not update issue state or publish operational divergences; emit only an execution-incomplete alert.

Validation pattern:

1. Wrap `/usr/bin/op` with a temporary PATH shim that logs argument shapes only and delegates to the real binary.
2. Run synthetic concurrency and assert N processes collapse to one refresh.
3. Exercise stale lock, force-refresh and renamed-item fixtures deterministically.
4. Run bounded production dry-runs, assert exact `op` call counts, unchanged state hashes, zero writes/posts and no secret output.
5. Remove generated dry-run artifacts before auto-push can commit them; preferably make dry-run skip artifact creation in code.

## Optimization priorities

1. Reduce cadence of heavy full reconcilers before micro-optimizing small monitors.
2. Fetch an item once as JSON and reuse its fields instead of one `op item get` per field.
3. Prefer item and vault IDs where safe and maintainable.
4. Cache only non-secret mappings/IDs; never persist secrets merely to save requests.
5. Stagger heavy jobs to avoid simultaneous bursts.
6. Keep manual on-demand validation available when scheduled cadence is reduced.

### Cardinality trap: full-vault discovery inside every run

Do not count only literal `op` call sites. Derive loop cardinality from live state or a single bounded inventory query:

- number of candidate items scanned;
- number of active/matched items actually needed;
- fields fetched per item;
- fallback fields that add another lookup;
- alert-only credential reads versus healthy-path reads.

A recurring monitor that lists the vault, reads `username` from every candidate item, then reads login fields again for matched items can dominate the account budget even with only a few call sites in source. Prefer:

1. a non-secret `user → item ID` mapping refreshed daily or only when an unknown user appears;
2. one full-item JSON read per active credential per run;
3. vault ID + item ID so a read costs one request instead of up to three;
4. shared non-secret discovery between jobs that scan the same credential family;
5. local bot transport for Discord rather than another 1Password lookup.

### Cold-cache risk versus observed usage

A low live account counter does not clear a high configured nominal budget. The persistent `op daemon` can satisfy repeated name/field reads from local cache, making observed usage far lower than the documented cold-cache ceiling. Report both and treat the configured ceiling as restart/cache-eviction burst risk.

Validated MGS example from 2026-07-12:

```text
Configured nominal ceiling     10,032 requests/day (20.06%)
Observed daily projection         ~124 requests/day (0.25%)
Largest nominal consumers      B011 DTR + Meta App Roles (89.47%)
Post-refactor conservative ceiling   ~751 requests/day (1.50%)
```

The reduction path is structural—full-item reads, IDs, and non-secret mapping reuse—not persistence of all DTR passwords/tokens. Secret caching remains an explicit security decision; the narrow Ares Meta token cache is governed separately by `meta-ads-api-operations`.

## Canonical MGS corrections — 2026-07-10/11

After full-system audit, Rodolfo set the two heavy Zeus monitors to hourly business-window cadence in ET with isolated start minutes:

```text
meta-app-roles-watch  08:04–23:04, uma vez por hora
b011-dtr-link-watch   08:24–23:24, uma vez por hora
```

The 20-minute stagger avoids simultaneous heavy sweeps; Honcho uses `:54` in its four operational windows. Do not restore the old 5/~8-minute cadence without explicit authorization and a fresh request-budget calculation.

Direct Discord transport corrections on 2026-07-11:

- `monitor-service-restarts.sh`, `check-pending-reports.sh`, `monitor-gpt55-oauth-cost.sh`, and `housekeeping-bak-cleanup.sh` use the local Zeus bot and consume zero 1Password requests for alert delivery;
- `monitor-yoast-health-eggbev.sh` uses the bot for Discord and retains only two SSH credential reads per run;
- `monitor-op-rate-limit.py` necessarily performs one hourly 1Password rate-limit probe and alerts with the bot.

## Verification checklist

- Read back every modified scheduler job: enabled, exact schedule, timezone, next run and script.
- Confirm the relevant skill/reference records the new canonical cadence.
- Register Hermes cron jobs in `infra-inventory.json`; root-crontab discovery alone is not sufficient.
- Update cron documentation where applicable, audit log and REPORT-INFRA.
- Do not run a heavy reconciler merely to verify a schedule change; scheduler readback is the correct validation unless execution behavior also changed.
