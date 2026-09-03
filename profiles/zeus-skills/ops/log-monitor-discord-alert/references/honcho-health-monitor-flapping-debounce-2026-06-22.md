# Honcho health monitor flapping debounce — 2026-06-22

## Context

The Honcho managed memory/copilot monitor was posting repeated Discord pairs in `#alerts-infra`:

1. `Honcho MGS indisponível`
2. `Honcho MGS restabelecido`

The visible pattern was every cycle or two, with mixed affected agents (`zeus`, `atena`, `ares`, `legacy-agent`) and technical details like `unavailable / none / timeout`.

Root issue: the monitor treated transient partial failures/timeouts as a full operational outage, then posted a green recovery as soon as the next cycle passed. That made noise look like incident churn.

## Durable pattern

For auxiliary-service monitors where the dependency is helpful but non-critical (Honcho copilot, status helpers, memory copilots):

- Do **not** alert CEO on first partial timeout.
- Separate **critical outage** from **partial degradation**.
- Critical outage should mean one of:
  - all monitored agents/checks fail in same run;
  - explicit `cold_storage`;
  - explicit action required such as `manual_resume_app_honcho_dev`.
- Add debounce: require at least 2 consecutive critical checks before push alert.
- Keep partial failures in logs/state, not Discord push, unless they persist enough to become operationally meaningful.
- Send green `restabelecido` only if an alert was actually active (`alert_active=true`). Otherwise, partial fail → OK should stay silent.

## Implementation shape used

In `/root/mgs-agent/scripts/monitor-honcho-health.sh`:

- `HONCHO_ALERT_THRESHOLD=${HONCHO_ALERT_THRESHOLD:-2}`
- `HONCHO_COPILOT_TIMEOUT_SECONDS=${HONCHO_COPILOT_TIMEOUT_SECONDS:-90}` for slower but still bounded checks.
- State fields:
  - `consecutive_failures`
  - `alert_active`
- Normalize raw failures into `ACTUAL_FAIL_COUNT`, then derive alertable `FAIL_COUNT` only when critical.
- Log suppressed partial failures:
  - `PARTIAL_FAIL suppressed actual_failures=1/4 reason=not_full_outage_not_cold_storage`
- Alert only when `NEW_CONSECUTIVE_FAILURES >= HONCHO_ALERT_THRESHOLD`.
- Recovery embed only when previous state had `alert_active=true`.
- If Rodolfo reports ongoing alert fatigue, keep debounced Discord alerting rather than log-only by default: `HONCHO_DISCORD_ALERTS=${HONCHO_DISCORD_ALERTS:-1}` with `HONCHO_ALERT_THRESHOLD=2`. First critical failure only updates state/log; push is sent only if the next 15-min cron still sees Honcho critically unavailable. If the CEO explicitly wants silence, set `HONCHO_DISCORD_ALERTS=0` as a temporary mute.

## Persistent billing block circuit breaker

When every monitored agent is classified as `billing_blocked / manual_billing_honcho` and the alert is active, repeated health calls cannot repair the dependency and only create noise. The monitor must fail closed before reading 1Password or calling Honcho:

- scheduled runs log `BILLING_BLOCKED` and exit zero without external calls;
- billing/top-up remains manual and is never attempted by the monitor;
- after manual regularization, an operator runs exactly one probe with `HONCHO_BILLING_RECHECK=1`;
- only a healthy override probe clears `alert_active`, resets `consecutive_failures`, and restores ordinary scheduled checks;
- validate with a fixture that the blocked branch makes zero external calls and that the override branch can recover state.

## Validation checklist

After patching:

1. `bash -n scripts/monitor-honcho-health.sh`
2. `python3 -m json.tool data/honcho-health-state.json` and inventory JSON if updated.
3. Mock partial failure: 1 of 4 agents returns `unavailable` → no alert; state remains OK/silent.
4. Mock full outage twice: 4 of 4 agents fail twice → alert on 2nd run.
5. Real cron/run: confirm latest log shows either OK or `PARTIAL_FAIL suppressed`, with:
   - `consecutive_failures=0`
   - `alert_active=false`
   - `last_alert_sent=null`

## Pitfall

Do not rely only on anti-spam windows. Anti-spam prevents repeated red alerts, but it does not stop the red/green flapping pattern if recovery messages are sent after every transient fail. Track `alert_active` and only resolve an alert that was truly active.
