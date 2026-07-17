# Company OS — Phase 5 Zeus SOUL alignment (2026-06-07)

## Trigger

Use after Phase 4 contextual review is closed and Rodolfo says to continue into Phase 5 agent adjustments.

## Safe execution pattern

1. Load `mgs-company-os-architecture`; if editing Hermes/profile behavior, also load the relevant Hermes operations skill.
2. Treat the first Phase 5 gate as **Zeus only** unless Rodolfo explicitly expands scope.
3. Locate both the live profile SOUL and versioned mirror:
   - Live: `/root/.hermes/profiles/zeus/SOUL.md`
   - Versioned mirror: `/root/mgs-agent/profiles/zeus-soul.md`
4. Create timestamped rollback backups for both files before patching.
5. Confirm live and versioned SOUL are identical before patching; after patching, keep them identical.
6. Patch minimally: add a clear `MGS OS — fonte gerencial principal` section near the top, without deleting the old SOUL context.
7. Include canonical source references: `company-os.md`, `areas.md`, `agent-map.md`, `routes.md`, `sources-of-truth.md`, `permissions-matrix.md`, `team.md`, `sites.md`, `data/sites.json`, `docs/CRONS.md`.
8. Encode precedence explicitly:
   - `data`/runtime/logs/WordPress/crontab/services win for live technical state.
   - `context`/MGS OS wins for managerial structure, areas, routes, responsibilities, and agent limits.
   - SOUL governs posture, channel, safety, and behavior but must not contradict MGS OS.
9. Update stale agent/model wording while there:
   - Replace `futuramente Ares` with current MGS agents: Atena, Ares, agente legado, future agents.
   - Remove stale model identity like `Claude Sonnet`; use active profile wording, normally GPT-5.5/OpenAI-Codex unless Rodolfo approved otherwise.
10. Update `docs/mgs-os-restructure-plan.md` to mark Zeus as concluded and Atena as the next recommended gate.
11. Append an audit event to `logs/events-audit.jsonl`.
12. Validate: `git diff --check`, secret scan over added lines, stale-term scan, live/versioned `cmp`, audit marker, auto-push log, `HEAD == origin/main`, repo clean.

## Scope boundaries

Do not change crontab, tokens, runtime/systemd, permissions, cleanup/migration, or Discord thread title during the initial Zeus alignment gate.

## Reporting shape

Report as a compact table with: phase/status, live profile, versioned mirror, plan file, backup, secret scan, audit log, auto-push, HEAD=origin, repo state. Then list what changed and what was not touched.
