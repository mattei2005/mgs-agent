# Hermes MGS update — port canonical patch before live update (2026-06-26)

## Context

Rodolfo asked to continue the safe Hermes update plan after upstream moved from 598 to 724 commits behind.

Live state at review time:

- Live Hermes: `ac83365d9` / v0.17.0
- Upstream: `a28b93909`
- Delta: 724 commits behind
- Live MGS invariants: 20/20 present
- Gateways: Zeus/Atena/Ares/agente legado active

## Durable lesson

When the live local diff no longer applies cleanly to `origin/main`, do **not** force the old diff or run a direct update. Port the MGS runtime customization surface into a fresh canonical patch against the current upstream first, then make the controlled update use that patch instead of replaying stale local diff.

## Safe workflow used

1. Fetch upstream and confirm `HEAD..origin/main` count.
2. Run controlled precheck only:
   - `PRECHECK_ONLY=1 STAMP=<stamp> SEND_DISCORD_REPORT=0 /root/mgs-agent/scripts/run-hermes-update-controlled.sh`
3. Create temporary worktree on `origin/main`.
4. Apply consolidated MGS patch with `git apply --3way` in the worktree.
5. Validate no conflicts and confirm MGS invariants:
   - Discord deterministic thread naming
   - thread auto-add
   - author suffix
   - REPORT-INFRA inline/no-thread guard
   - bot/gateway anti-loop
   - restart auto-resume / recovery checkpoint
   - Codex incomplete/no-content noise filter
   - local-file auto-attach safety gate
   - Discord `delete_message` cleanup support
6. Run `py_compile` on critical files.
7. Run target tests from the worktree using the Hermes venv:
   - `tests/gateway/test_restart_resume_pending.py`
   - `tests/gateway/test_discord_free_response.py`
   - `tests/gateway/test_discord_bot_filter.py`
   - `tests/gateway/test_telegram_noise_filter.py`
8. Generate a new canonical patch from the validated worktree diff.
9. Verify the new patch applies cleanly to a fresh `origin/main` worktree with `git apply --check`.
10. Update the guard/precheck scripts to use the new canonical patch.
11. Run another precheck-only pass and confirm the canonical patch is `OK apply-clean`.

## Validated result in this session

Created:

- `/root/mgs-agent/patches/hermes/mgs-runtime-customizations-2026-06-26.patch`
- SHA256: `2c7ad578f38b3ea312ef63a0805b9bf747ec35823d4675b406063c570f720848`

Validation:

- `git apply --check` on `origin/main`: OK
- `py_compile`: OK
- Target pytest: 138 passed, 2 warnings, 6 subtests passed
- Post-port precheck: canonical patch OK, invariants 20/20 OK

## Script lessons

### `ensure-hermes-mgs-patches.sh`

Add the newly ported canonical patch before legacy per-feature patches:

- `mgs-runtime-customizations-2026-06-26.patch`

Keep legacy patches as invariant/backward-compatible fallback when useful, but the newest canonical patch is the actual update surface.

### `run-hermes-update-controlled.sh`

The precheck canonical patch list should test the newest canonical patch first. If the old live local diff drifts but the canonical patch has been ported and validated, the update path can use:

- `RESTORE_LOCAL_DIFFS=0`

Meaning: do not replay the stale pre-update live diff after update; let the canonical guard patch apply the validated MGS surface. This must only be used after a successful worktree port + `apply --check` + invariant + test validation.

## Pitfall

A precheck may show:

- canonical/new patch applies cleanly; and
- old unstaged local diff drifts.

That is not automatically a blocker anymore if the new canonical patch was generated from the full MGS surface and validated. It **is** still a blocker for the old default path that restores local diffs. Use the explicit `RESTORE_LOCAL_DIFFS=0` controlled path only after validation.

## Reporting requirement

Because this modifies scripts/patches/data inventory, send REPORT-INFRA and update `infra-inventory.json` before saying the port work is complete.
