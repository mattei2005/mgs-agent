# Full-system 1Password consumption audit — MGS

Use this reference when a Service Account approaches rate limits or Rodolfo asks for hourly/daily/monthly consumption by automation.

## Mandatory inventory scope

Do not stop at the root crontab. Enumerate all of these before calculating:

1. Root crontab and `/etc/cron*`.
2. Hermes scheduler jobs for **every profile**, especially:
   - `/root/.hermes/profiles/zeus/cron/jobs.json`
   - `/root/.hermes/profiles/atena/cron/jobs.json`
   - `/root/.hermes/profiles/ares/cron/jobs.json`
   - `/root/.hermes/profiles/hera/cron/jobs.json`
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

The rate-limit query itself is a request. Keep production monitoring low-frequency; MGS canonical rate-limit monitor cadence is once per hour, with transition-only anti-spam alerts at 50% and critical at 90%.

## Consumer classification

- **Fixed:** credential lookup occurs on every run.
- **Conditional/lazy:** credential is fetched only when an alert/recovery or other branch executes. Verify call sites, not just literal `op` strings.
- **Event-driven:** e.g. Git post-commit hook; estimate from actual event counts over 24h and 7d.
- **On-demand:** manual agent tasks, diagnostics and DTR sweeps; exclude from fixed baseline but report potential burst cost.

## Optimization priorities

1. Reduce cadence of heavy full reconcilers before micro-optimizing small monitors.
2. Fetch an item once as JSON and reuse its fields instead of one `op item get` per field.
3. Prefer item and vault IDs where safe and maintainable.
4. Cache only non-secret mappings/IDs; never persist secrets merely to save requests.
5. Stagger heavy jobs to avoid simultaneous bursts.
6. Keep manual on-demand validation available when scheduled cadence is reduced.

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
