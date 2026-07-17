# Alerts-infra humanized cron alerts — 2026-06-27

## Trigger

Rodolfo complained that automated alerts arriving in `#alerts-infra` were visually polluted and asked to make them more human/table-oriented.

## Durable pattern

For automated cron/watchdog alerts sent to Discord:

1. Prefer structured Discord embeds with short `content` only for required mention/push.
2. For multiple related events in one run, batch them into one alert instead of one message per item.
3. Put comparable data in a compact monospaced table inside a single embed field.
4. Avoid raw `Cronjob Response`, raw `[REPORT-INFRA]`, stdout dumps, or line-by-line operational logs in Discord.
5. For Hermes `no_agent=true` script-only watchdogs:
   - set cron `deliver` to `local`;
   - make success stdout empty;
   - have the script post its own human-readable webhook embed only on anomaly.
6. If the script lives outside the repo/profile runtime, register it as `runtime_artifacts[]` in `infra-inventory.json` with SHA/size/validation; do not try to git-add profile-local scripts.

## Validated implementation examples

### `monitor-service-restarts.sh`

Problem: restart detection produced one Discord alert per restarted service, causing 4–5 near-identical messages.

Fix pattern:
- collect restart events into a temp JSONL file during service loop;
- after loop, if temp file is non-empty, render one aligned table with columns like `Serviço`, `Start atual`, `Causa provável`, `Ação`;
- send one embed titled `Restarts de serviços detectados` with `Serviços afetados` count and the table field.

### agente legado `drive-auth-watchdog.py`

Problem: Hermes script-only cron delivered stdout directly to Discord as `Cronjob Response` containing raw `[REPORT-INFRA]` text.

Fix pattern:
- update Hermes cron job `deliver` to `local`;
- replace raw prints with direct webhook post from the script;
- embed contains a compact table like `Credencial / Estado / HTTP / Erro` and clear fields `Resumo`, `Impacto`, `Próxima ação`;
- dry-run mode prints JSON payload locally without posting.

## Verification pattern

After patching alert layout, run normal syntax checks plus an ad-hoc behavior verifier rather than claiming full suite green:

- Create a temporary script under `/tmp` with prefix `hermes-verify-`.
- For stateful monitors, backup state, mutate a copy/state to force the alert branch, run with dry-run env, then restore state in `finally`/trap.
- Assert the new marker is present, e.g. `active_enter_batch`.
- Assert old noisy markers are absent, e.g. `RESTART alert enviado para <svc>`.
- For webhook scripts, import the module and call the payload function with fake non-secret data under dry-run/captured stdout.
- Remove the temporary verifier after execution.
- Report as `ad-hoc verification`, not as canonical suite pass.

## Pitfalls

- Do not use `notify_on_complete=true` or `deliver=origin` for script-only watchdogs that can print anything; stdout becomes user-visible noise.
- Do not post a real test alert unless Rodolfo explicitly wants a smoke-test message in the channel.
- Do not let inventory updates reorder/reconstruct the whole `infra-inventory.json`; stage/merge surgically from `HEAD` when there is unrelated drift.
- If a profile-local file is changed, remember it is not versioned by `/root/mgs-agent` unless there is an explicit sync rule; inventory/audit log is the traceability layer.
