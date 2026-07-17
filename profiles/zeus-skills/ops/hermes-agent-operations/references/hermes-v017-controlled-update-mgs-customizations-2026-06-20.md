# Hermes v0.17 controlled update — MGS customization preservation

Use this as a concrete reference for future large Hermes updates on MGS when the live checkout is hundreds of commits behind and carries local Discord/gateway patches.

## Trigger

Rodolfo asked for a controlled update from Hermes v0.16.0 (`f10f7114f`) to v0.17.0 (`ac83365d9`) and explicitly warned not to lose MGS customizations “igual aconteceu aquela vez”. Precheck showed ~388 commits behind and local Discord/gateway patches drifting against upstream.

## Key lesson

Do not treat a 7-step executive outline as sufficient. For Rodolfo, the task is not complete until there is proof across backups, crons, gateways, auth, tests, patch guards, REPORT-INFRA, inventory and Git hygiene. Avoid vague phrases like “acabou operacionalmente” without a full evidence matrix.

## Safe pattern that worked

1. Run `PRECHECK_ONLY=1 /root/mgs-agent/scripts/run-hermes-update-controlled.sh` first; do not mutate production on initial review.
2. If patch/local diff drift appears, stop before update and create a temporary upstream worktree.
3. Apply the live local Hermes diff to the worktree with `git apply --3way`; resolve conflicts there, not in production.
4. Validate the ported worktree:
   - no conflict markers;
   - `py_compile` for `plugins/platforms/discord/adapter.py`, `gateway/run.py`, `gateway/platforms/base.py`;
   - MGS invariant scan for thread title, auto-add, REPORT-INFRA inline/no-thread, restart checkpoint/idempotency, bot-loop guard, author suffix, delete_message cleanup;
   - targeted pytest for gateway shutdown/restart/Discord/free-response/bot-filter tests.
5. Generate one consolidated patch from the validated port and save it under `/root/mgs-agent/patches/hermes/`.
6. Patch `/root/mgs-agent/scripts/ensure-hermes-mgs-patches.sh` so the consolidated patch applies first, then legacy per-feature patches remain as invariant/fallback checks.
7. Validate the updated guard on both:
   - live checkout with patch already applied;
   - a clean upstream worktree where the guard must apply the consolidated patch from scratch.
8. Only then mutate the live Hermes checkout: backup, reset local tracked changes, fast-forward to pinned upstream commit, apply validated consolidated patch, install deps, run guard/tests.
9. Restart gateways externally with `/root/mgs-agent/scripts/mgs-gateway-restart-safe.sh`, Zeus last.
10. Produce a complete final report: backups, crons, Hermes cron jobs, systemd PIDs/start times, auth/config sanitized, tests, disk, REPORT-INFRA, inventory, rollback assets, dirty Git state and push status.

## Commands shape

```bash
# precheck only
STAMP="precheck-$(date +%Y%m%d-%H%M%S)"
PRECHECK_ONLY=1 SEND_DISCORD_REPORT=0 STAMP="$STAMP" \
  /root/mgs-agent/scripts/run-hermes-update-controlled.sh

# create upstream worktree for porting
repo=/root/.hermes/hermes-agent
port=/root/mgs-agent/reports/hermes-updates/port-$(date +%Y%m%d-%H%M%S)
mkdir -p "$port"
git -C "$repo" diff HEAD > "$port/live-diff-combined.patch"
git -C "$repo" worktree add --detach "$port/worktree" origin/main
git -C "$port/worktree" apply --3way "$port/live-diff-combined.patch"

# after resolving/validating, create consolidated patch
git -C "$port/worktree" diff > /root/mgs-agent/patches/hermes/mgs-runtime-customizations-YYYY-MM-DD.patch

# clean-worktree guard validation
wt=/tmp/hermes-guard-clean-check-$(date +%Y%m%d-%H%M%S)
git -C "$repo" worktree add --detach "$wt" origin/main
BASE=/root/mgs-agent REPO="$wt" LOG=/tmp/guard-clean.log \
  /root/mgs-agent/scripts/ensure-hermes-mgs-patches.sh
```

## Pitfalls found

- `git apply --3way` can report a file as unmerged even when conflict markers are only a small local section; scan for markers and inspect `git ls-files -u`.
- Upstream tests may need assertion updates if the MGS patch intentionally strengthens behavior, e.g. adding the read-only/non-actionable header to recent channel context.
- `npm install` may dirty `package-lock.json`; restore it unless dependency changes are intentional.
- Manual `git push` can fail in non-interactive shell due missing GitHub username; the post-commit auto-push hook can still succeed using 1Password. Verify with `git ls-remote origin refs/heads/main`.
- Do not mix the update commit with unrelated Ares/agente legado dirty files. Stage only the update infra files and run a targeted secret scan before commit.
- If `mgs-autocommit` was paused, restart it and verify active.

## Evidence shape Rodolfo expects

Include, at minimum:

- exact Hermes version, old/new commits, behind/ahead;
- backups created with path and size;
- services active with PID/start timestamps;
- root crons count and health-monitor latest outputs;
- Hermes cron list and patch watchdog status;
- sanitized profile auth/config for Zeus/Atena/Ares/agente legado;
- test counts and guard status;
- REPORT-INFRA and inventory update status;
- Git commit/push status for MGS infra changes;
- remaining non-critical dirty state and whether it affects runtime.
