# Meta Business hourly scheduled ad-account batch — 2026-09-06

## Scope

Rodolfo authorized 40 additional ad accounts in Business Portfolio `Digital Trust` (`155263197283282`), one account per hour starting in the 04:00 ET hour. Defaults remained `001`, `America/Los_Angeles`, `USD`, `My business`, Rodolfo with Full access, and no payment method.

This reference records the reusable scheduler design and the validation boundary. It is not proof that all 40 future writes completed.

## Schedule allocation

A global eight-date audit covered root crontab, `/etc/crontab`, `/etc/cron.d`, systemd timers, and enabled Hermes jobs for Zeus, Atena and Ares.

- Minute `00` conflicted with multiple operational jobs, including two hourly jobs.
- Minute `01` conflicted with the Ares CPV daily report.
- Minute `04` was the first minute in the requested hour with zero non-baseline operational collisions and zero Meta Library browser/profile-lock conflicts.
- A deterministic 20-second stagger separated the browser mutation from unavoidable dense baselines.

The selected schedule was `4 * * * *`; the first eligible write was 04:04:20 ET.

## Finite recurring-job pattern

Because the hourly cron existed before 04:00, its 03:04 tick was intentionally silent. The job used a finite repeat budget containing:

- one pre-start silent tick;
- 40 requested write opportunities;
- five bounded recovery ticks.

The durable state—not the repeat budget—enforced `target=40`. Each tick could create at most one account, and ticks after completion had to emit nothing.

## Runner gates

The deterministic runner used:

- canonical root-level data state so infrastructure discovery inventories it;
- atomic state writes;
- a dedicated run lock;
- the protected Meta Library browser-profile lock;
- `not_before`, `next_due_at`, and a minimum elapsed-time guard;
- one mutation maximum per scheduler tick;
- unique Ad Account ID and internal asset ID readback;
- direct navigation to the captured asset;
- semantic `People` tab readback for exactly one assigned person and Rodolfo Full access;
- fail-closed handling for login/passkey, security, maximum-account, ambiguous IDs and access divergence.

A generic mutation rejection with proven zero side effect may schedule one controlled retry on a later hourly tick. A second rejection or any unresolved side effect blocks the batch.

## Setup validation completed

- Python, Node and shell syntax checks passed.
- Live Meta preflight confirmed the exact Business and creation form with no maximum gate.
- Pre-start wrapper smoke produced zero stdout bytes and left the state hash unchanged.
- Cron readback confirmed schedule, finite repeats, script-only mode, delivery target and enabled state.
- Post-write collision audit remained at zero non-baseline operational conflicts and zero shared browser-lock conflicts.
- Checkpoint, audit, infrastructure inventory and REPORT-INFRA were written and read back.

## Validation boundary

At setup close, the batch was `scheduled` with `0/40` created. Do not call the lane fully operational until the first natural scheduler tick creates one account and the live ID/owner/People/Full-access readback passes. Subsequent completion must be reported from durable state, not inferred from consumed cron ticks.
