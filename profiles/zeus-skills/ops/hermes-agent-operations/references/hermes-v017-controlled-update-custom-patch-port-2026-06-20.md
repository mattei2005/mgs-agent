# Hermes v0.17 controlled update — MGS custom patch port (2026-06-20)

Use this as a concrete reference for large Hermes updates where the local MGS runtime has custom Discord/gateway patches and upstream is hundreds of commits ahead.

## Trigger

Rodolfo asked to update Hermes when Zeus was ~388 commits behind, with explicit concern: do not lose customizations like a prior incident.

Initial state:

```text
Local Hermes   v0.16.0 / f10f7114f
Upstream       v0.17.0 / ac83365d9
Behind         388 commits
Gateways       Zeus/Atena/Ares/agente legado active
Risk           local Discord/gateway patch surface did not apply cleanly to upstream
```

## What mattered

The safe gate was not “backup exists”; it was proving that MGS custom behavior survives on the new upstream **before** mutating production.

Required behaviors/invariants included:

- Discord deterministic thread title helper.
- Thread auto-add users.
- `REPORT-INFRA` inline/no-thread guard.
- Bot lifecycle/loop-noise suppression.
- Planned restart auto-resume and anti-reexecution checkpoint.
- Post-response AI thread title rename.
- Author suffix in thread titles.
- `delete_message` support for progress cleanup.
- Local-file auto-attach safety gate.
- Codex incomplete/no-content noise guard.
- Read-only recent-channel context header.

## Safe workflow that worked

1. Run `PRECHECK_ONLY=1 /root/mgs-agent/scripts/run-hermes-update-controlled.sh` first.
2. If canonical patches or live local diff show drift, stop before mutation.
3. Pause `mgs-autocommit.service` while generating update artifacts.
4. Create a temp worktree from `origin/main`.
5. Apply the live local diff with `git apply --3way` in the temp worktree.
6. Resolve conflicts manually. In this session the conflict was in `plugins/platforms/discord/adapter.py` around channel-history context formatting; the correct merge preserved both:
   - upstream read-only/non-actionable header; and
   - MGS reply-target context hydration blocks.
7. Run `py_compile` and targeted pytest in the worktree before touching production.
8. Export the validated diff as a consolidated patch:
   - `/root/mgs-agent/patches/hermes/mgs-runtime-customizations-2026-06-20.patch`
9. Patch `/root/mgs-agent/scripts/ensure-hermes-mgs-patches.sh` to apply the consolidated patch first, then legacy per-feature patches as invariant checks/backward-compatible fallback.
10. Validate the guard can patch a clean upstream worktree from scratch.
11. Only then mutate the live Hermes checkout: `git reset --hard`, fast-forward to pinned origin, apply consolidated patch.
12. Reinstall/refresh dependencies, run guard, compile critical files, run targeted tests.
13. Restore `mgs-autocommit.service`.
14. Send `REPORT-INFRA` for script/patch/inventory changes.
15. Restart gateways through detached safe finalizer with Zeus last.
16. Schedule/read post-restart validation instead of polling foreground from the active Zeus turn.

## Validation commands used

Targeted tests that passed before restart:

```bash
python -m py_compile \
  plugins/platforms/discord/adapter.py \
  gateway/run.py \
  gateway/platforms/base.py \
  gateway/config.py \
  tools/terminal_tool.py \
  tools/file_tools.py \
  tools/send_message_tool.py \
  tools/discord_tool.py

python -m pytest -q \
  tests/gateway/test_gateway_shutdown.py \
  tests/gateway/test_restart_resume_pending.py \
  tests/gateway/test_discord_free_response.py \
  tests/gateway/test_discord_bot_filter.py \
  tests/gateway/test_telegram_noise_filter.py
```

Result in session:

```text
155 passed, 6 subtests passed
Hermes v0.17.0, behind=0, Up to date
ensure-hermes-mgs-patches.sh OK
clean-worktree guard OK
```

## Pitfalls / durable lessons

- If `git apply --check` fails for local MGS patch surface, do not use `ALLOW_PATCH_DRIFT=1` as a shortcut. First port and validate in a temp worktree.
- Do not treat legacy patch files as sufficient protection after a large upstream jump. Create or refresh a consolidated patch that applies to the new upstream and make the guard prove it on a clean worktree.
- Conflict resolution must preserve upstream safety improvements, not blindly prefer MGS code. Here the final merge kept the upstream read-only context header and the MGS reply-context blocks.
- Tests may fail because expected strings changed after a correct merge; update tests only when the behavior is intentionally preserved/improved and the production invariant is clear.
- Do not leave `mgs-autocommit.service` stopped after maintenance; stop it during artifact generation, then restore it before final restart/report.
- `REPORT-INFRA` is part of completion when scripts/patches/inventory change.
- Restart should be detached and ordered: Ares/agente legado/Atena first, Zeus last. Do not restart all gateways from the active Zeus foreground turn.
