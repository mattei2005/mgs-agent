# Hermes MGS active patch surface — 2026-06-17 cleanup

Root of `patches/hermes/` now contains only patches referenced by the MGS guard/update scripts.
Historical snapshots and experimental/obsolete patches were moved to `archive/20260617-cleanup/`.

## Active root patches

- `discord-deterministic-thread-rename-auto-add-users.patch`
- `planned-restart-auto-resume-active-sessions.patch`
- `restart-recovery-checkpoint-idempotent.patch`
- `discord-post-response-thread-title-rename.patch`
- `discord-new-thread-ai-title-once.patch`
- `discord-thread-title-deduplicate-safe-autorename.patch`
- `discord-bot-gateway-lifecycle-loop-guard.patch`
- `discord-report-infra-no-auto-thread.patch`
- `discord-thread-title-author-suffix.patch`

## Guard policy

- `ensure-hermes-mgs-patches.sh` validates active patches by direct reverse/apply when possible and by explicit invariants when upstream context drift makes exact patch application unreliable.
- `run-hermes-update-controlled.sh` now checks both canonical patches and the saved live local diffs against `origin/main` before mutation.
- If the live local diff does not apply cleanly to `origin/main`, update fails closed before touching the live checkout. Manual port is required.
- Runtime-critical invariants include thread titles/author suffix, auto-add users, anti-loop bot noise, Codex noise filtering, REPORT-INFRA no-thread guard, restart recovery, local-file auto-attach safety, and Discord cleanup_progress delete support.

## Archive

`archive/20260617-cleanup/MOVE-MANIFEST.json` lists every patch moved out of root during cleanup.
