# Read-only calibration + human feedback loop — 2026-06-19

## User correction / operating model

Rodolfo clarified that the current Meta Ads cron phase is **not** for Ares to act on the account and not for a human to keep operating forever. It is a calibration phase:

```text
Current phase              | Meaning
---------------------------|------------------------------------------------
read-only / dry-run         | Ares reads, analyzes, and says what it would do
human action                | Rodolfo executes/declines manually for now
purpose                     | calibrate Ares' decision logic over 4 days
future phase                | controlled write/autonomy only after explicit approval
```

Ares must not ask to enable full write early. Recommend staying in dry-run until rules/state/report format are validated.

## Cron scope clarification

The cron is operation/account-scoped, but reports/actions must be governed by explicit scope and local state:

```text
Layer                  | Correct behavior
-----------------------|------------------------------------------------
Account                | source of read-only data
Active focus           | campaigns/pages currently under management
Excluded/manual holds  | not reactivated or repeatedly recommended
Paused by Ares rule    | stays in state for potential simulated reactivation
Paused by human        | do not re-enter automation unless Rodolfo says so
```

Patricia/Elena example from session:

```text
Page/campaign family | PG ID    | Desired handling during this phase
---------------------|----------|------------------------------------
Patricia Flores      | pg_22069 | paused/saturated; exclude/manual hold unless requested
Elena Santana        | pg_22091 | current active focus for monitoring
```

## Reporting/feedback loop

For every meaningful checkpoint/recommendation during dry-run, prefer a thread in `logs-aquisicao`:

```text
Step | Actor   | Behavior
-----|---------|------------------------------------------------
1    | Ares    | posts checkpoint/recommendations with recommendation IDs
2    | Rodolfo | replies in that thread: feito / ignorar / segurar / pausei / reativei / não mexer
3    | Ares    | records the decision in local state/audit
4    | Ares    | validates status by API in the next read-only pass
```

Recommended report columns:

```text
ID recomendação | Campanha | Status atual | Regra | Ação que eu tomaria | Motivo | Estado local
```

Short response semantics:

```text
Resposta de Rodolfo      | Meaning
-------------------------|------------------------------------------------
feito                    | user manually executed the suggested action
ignorar                  | do not follow that suggestion
segurar 1 checkpoint      | wait until the next checkpoint
pausei                   | user manually paused campaign
reativei                 | user manually reactivated campaign
não mexer nessa campanha | mark manual hold/exclusion
```

## State model to implement

Add/maintain local state so crons distinguish why a campaign is paused:

```text
State value              | Cron behavior
-------------------------|------------------------------------------------
active_in_scope           | evaluate normally
paused_by_ares_rule       | continue monitoring; simulate reactivation when rule says so
paused_by_human           | do not re-activate; only report if explicitly requested
paused_by_saturation      | exclude from routine active recommendations
paused_by_test_or_clone   | ignore until validation/decision
manual_hold               | do not recommend actions unless Rodolfo removes hold
```

## Pitfalls

- Do not say a cron is “for Patricia” just because Patricia appeared in an early report; the current cron reads the operation/account and reports rows that match rules.
- Do not imply inactive/paused campaigns disappear forever; if they are relevant and state says `paused_by_ares_rule`, they must remain monitored for possible reactivation recommendations.
- Do not propose switching to full write while the user is asking to understand/calibrate the dry-run behavior.
- When write is later enabled, stop creating decision threads for every action; instead execute, validate via GET, and post a concise action-completed log.
