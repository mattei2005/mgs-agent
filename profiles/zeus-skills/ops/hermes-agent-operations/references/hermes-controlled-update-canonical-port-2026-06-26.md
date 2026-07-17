# Hermes controlled update — canonical patch port pattern (2026-06-26)

## Context

During a controlled Hermes update, upstream moved from `a28b93909` to `0f81b0d45` while the pre-update port work was in progress. The live Hermes checkout was initially hundreds of commits behind, with MGS local runtime customizations touching:

- `gateway/run.py`
- `plugins/platforms/discord/adapter.py`
- `gateway/platforms/base.py`
- gateway/Discord/restart tests

The safe path was to avoid applying the old live local diff directly to upstream. Instead, port a fresh canonical patch in a detached worktree, validate it, then let the live update use that canonical patch as the source of truth.

## Durable workflow

1. Fetch upstream and confirm current behind count.
2. Run the controlled script in precheck mode first:

```bash
PRECHECK_ONLY=1 STAMP="pre-live-final-$(date +%Y%m%d-%H%M%S)" SEND_DISCORD_REPORT=0 \
  /root/mgs-agent/scripts/run-hermes-update-controlled.sh
```

3. If canonical patch check fails or the live local diff has drift, do not update live yet.
4. Create a detached worktree at `origin/main` and apply the consolidated MGS patch with `--3way`.
5. Generate a new canonical patch from the staged worktree diff, e.g.:

```bash
git -C "$worktree" diff --cached > /root/mgs-agent/patches/hermes/mgs-runtime-customizations-YYYY-MM-DD.patch
```

6. Validate the new patch against a clean upstream worktree:

```bash
git -C "$check_wt" apply --check /root/mgs-agent/patches/hermes/mgs-runtime-customizations-YYYY-MM-DD.patch
python -m py_compile \
  "$check_wt/plugins/platforms/discord/adapter.py" \
  "$check_wt/gateway/run.py" \
  "$check_wt/gateway/platforms/base.py"
```

7. Run targeted gateway tests in the worktree before touching live Hermes. The validated target set from this session:

```bash
PYTHONPATH="$worktree" /root/.hermes/hermes-agent/venv/bin/python -m pytest -q \
  tests/gateway/test_restart_resume_pending.py \
  tests/gateway/test_discord_free_response.py \
  tests/gateway/test_discord_bot_filter.py \
  tests/gateway/test_telegram_noise_filter.py
```

8. Update `ensure-hermes-mgs-patches.sh` so the new canonical patch is applied first and legacy patches become invariant/backward-compatible checks.
9. Update `run-hermes-update-controlled.sh` so the canonical upstream patch check uses the new patch.
10. For the live update, if the old live local diff is known-drifted and the new canonical patch is validated, run with:

```bash
RESTORE_LOCAL_DIFFS=0 RESTART_GATEWAYS=0 STAMP="live-update-$(date +%Y%m%d-%H%M%S)" SEND_DISCORD_REPORT=0 \
  /root/mgs-agent/scripts/run-hermes-update-controlled.sh
```

`RESTORE_LOCAL_DIFFS=0` means: do not reapply the stale pre-update live diff; let the canonical patch guard restore the validated MGS surface.

## Validation gates used

- `git rev-list --count HEAD..origin/main` becomes `0` after update.
- `hermes --version` says `Up to date`.
- MGS patch guard passes.
- `py_compile` passes for Discord adapter, gateway run, platform base/config, terminal/file tools.
- Targeted pytest set passes; in this session: `138 passed, 2 warnings, 6 subtests passed`.
- Codex auth remains present in Zeus/Atena/Ares/agente legado without printing secrets.
- Gateways remain `active`; restart is handled separately.

## Pitfall: profile config comparison after upstream schema/default migrations

The old profile backup comparison failed because Zeus `config.yaml` gained new upstream defaults/schema keys. That is useful evidence but not necessarily a regression. Treat config byte-diff as:

- `FAIL` only if MGS critical invariants changed or disappeared: `model.provider=openai-codex`, `model.default=gpt-5.5`, `compression.threshold=0.85`, auth presence, SOUL preservation.
- `WARN` if the only change is upstream-added/default config keys and the critical invariants still match.

Do not report the update as failed solely because upstream added benign config defaults.

## Pitfall: upstream can move while porting

If upstream receives new commits after the port worktree was created, re-run the pre-live precheck immediately before live update. In this session the behind count changed again before execution; the new canonical patch still applied cleanly, so the update proceeded.

## Reporting standard

For this class of update, report separately:

- code on disk updated vs. gateways restarted;
- patch port validation vs. live update validation;
- any WARN from config schema/default migration;
- exact report directories and patch SHA;
- whether restart is still pending.
