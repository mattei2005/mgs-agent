# Hermes update Discord report + follow-up pitfalls — 2026-06-17

## Context

During a controlled Hermes/VPS update for MGS, the update script performed the technical steps correctly but created user-facing confusion in Discord:

1. `run-hermes-update-controlled.sh` had a stale hardcoded default `MGS_UPDATE_REPORT_THREAD_ID=1516073108535120086` and `SEND_DISCORD_REPORT=1`.
2. A pre-check run posted an update report into that old thread instead of the active Rodolfo/Zeus thread.
3. The gateway restart finalizer was intentionally file-only and did not deliver a final Discord follow-up; Zeus said it would resume/validate but did not proactively post the completion until Rodolfo asked.
4. A separate Hermes news explainer cron posted a Zeus summary in `#alerts-hermes-news` around the same time, making it look related to the update even though it was just a news/tip announcement.

## Durable rules for future Hermes/VPS updates

- Never hardcode a Discord thread ID in update scripts. Discord report delivery must be opt-in per run.
- Default for update scripts should be local artifacts only: `SEND_DISCORD_REPORT=0` and empty `MGS_UPDATE_REPORT_THREAD_ID` unless the current destination is explicitly passed.
- If using a detached/file-only restart finalizer, schedule or perform a separate clean follow-up after validation. Do not say “vou retomar/validar depois” unless a concrete callback/delivery mechanism exists.
- In the final report, separate clearly:
  - update execution;
  - restart finalizer validation;
  - unrelated Hermes news/announcement crons;
  - newly appeared upstream commits after the update.
- When Rodolfo asks whether an announcement/update was “included”, answer by comparing the applied commit range and searching for related commit subjects/docs. Do not infer inclusion from the timing of a news alert.

## Good reporting shape

```text
O que foi aplicado
- Antes: <pre_commit>
- Depois: <post_commit>
- Commits: N
- Gateways: active/reconnected

O que NÃO faz parte desse update
- Hermes news/tip announcement: <channel/time>, cron explain only
- Upstream commits after update: <list>

Follow-up
- Restart finalizer log: <path>
- Validation status: OK/pendente
```

## Cleanup lesson

Controlled update reports/backups can consume several GB quickly. After every update, include a backup inventory and recommended deletion set:

- Keep the main pre-update execution backup and patch archives.
- Delete redundant pre-check backups and post-validation tarballs when a canonical pre-update backup exists.
- Keep text reports/logs where possible; delete only large tarballs when preserving evidence is still useful.
- Do not delete safety backups or older known-good profile backups without explicitly stating the rollback trade-off.
