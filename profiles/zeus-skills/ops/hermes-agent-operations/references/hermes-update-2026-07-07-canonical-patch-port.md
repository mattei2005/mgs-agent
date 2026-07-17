# Hermes update 2026-07-07 — canonical patch port + official update replace collision

## Context

Rodolfo asked Zeus to update Hermes after new commits appeared. Live state was `a05b64d67`, upstream `009b42d00`, `behind=210`. The controlled MGS update precheck found both the canonical patch and the live local diff drifted against `origin/main` in `gateway/run.py` and `plugins/platforms/discord/adapter.py`.

Zeus ported the MGS runtime customization surface in a detached `origin/main` worktree, generated a new consolidated patch, updated the patch guard, then ran the controlled update with `RESTORE_LOCAL_DIFFS=0 RESTART_GATEWAYS=0`.

## Durable lessons

### 1. Treat drift as a port task, not as permission to restore stale live diff

When `pre-local-diff.patch` and the current canonical patch both fail against `origin/main`, do not force `RESTORE_LOCAL_DIFFS=1` and do not rely on `ALLOW_PATCH_DRIFT=1` alone. Port the MGS surface in a temporary upstream worktree first, validate it, promote a new canonical patch, and only then run live update with `RESTORE_LOCAL_DIFFS=0`.

Validated shape:

```bash
WT=/tmp/hermes-port-YYYYMMDD
repo=/root/.hermes/hermes-agent
git -C "$repo" worktree add --detach "$WT" origin/main
git -C "$WT" apply --3way /path/to/pre-local-diff.patch || true
# resolve conflicts, preserving upstream + MGS invariants
git -C "$WT" diff --binary HEAD > /root/mgs-agent/patches/hermes/mgs-runtime-customizations-YYYY-MM-DD.patch
```

Key validation before touching the live checkout:

```bash
git -C "$VERIFY_WT" apply --check /root/mgs-agent/patches/hermes/mgs-runtime-customizations-YYYY-MM-DD.patch
BASE=/root/mgs-agent REPO="$VERIFY_WT" /root/mgs-agent/scripts/ensure-hermes-mgs-patches.sh
/root/.hermes/hermes-agent/venv/bin/python -m pytest -q \
  tests/gateway/test_discord_bot_filter.py \
  tests/gateway/test_discord_free_response.py \
  tests/gateway/test_restart_resume_pending.py \
  tests/gateway/test_display_config.py \
  tests/gateway/test_run_cleanup_progress.py
```

### 2. Update the guard before using it to validate the new clean worktree

If a new canonical patch is created, `/root/mgs-agent/scripts/ensure-hermes-mgs-patches.sh` must reference that patch before verifying a clean worktree. Otherwise the guard may fail on the older canonical patch even though the new patch is correct. The intended order is:

1. Generate `mgs-runtime-customizations-YYYY-MM-DD.patch`.
2. Patch `ensure-hermes-mgs-patches.sh` to apply/check the new patch first.
3. Run `bash -n` on the guard.
4. Verify clean worktree: `git apply --check` + guard + `py_compile` + targeted pytest.
5. Then run the live controlled update.

### 3. Conflict resolution preference for Discord thread-title code

When upstream and MGS both touch Discord auto-thread naming/renaming:

- Preserve upstream fixes that are not in conflict, especially new Discord UI/interaction behavior.
- Keep exactly one Discord thread rename path in `gateway/run.py`: `_is_discord_thread_lane`, `_discord_thread_safe_to_autorename`, `_schedule_discord_thread_title_rename`, `_rename_discord_thread_for_session_title`, `_sanitize_discord_thread_title`.
- Remove older duplicate MGS helper variants such as `_is_discord_auto_thread_lane` / `_schedule_discord_semantic_thread_rename` when the newer safe thread-lane path is present.
- Preserve exact provisional title memory in the adapter (`_remember_auto_thread_initial_title`) and ensure `auto_thread_initial_name` uses the remembered value or `_auto_thread_name_from_message`, not a removed `_derive_auto_thread_name` helper.
- The guard should fail on duplicate title sanitizers/rename functions; duplicate helpers are not harmless.

### 4. `hermes update --yes --no-backup` may still stash/restore and auto-restart gateways

Even inside the controlled script with MGS backup already made and `RESTART_GATEWAYS=0`, the official `hermes update` path can:

- create an internal autostash;
- restore local changes on top of updated code;
- drain/restart manual gateway profiles independently of the wrapper script.

Observed again on 2026-07-07: Ares, Atena and agente legado were left in `activating` with orphan `gateway run --replace` processes. Recovery matched the 2026-07-05 pattern: stop affected services, kill `--replace`, reset-failed, start Ares/agente legado/Atena, validate all services active and `replace_pids=0`. Zeus was not touched.

### 5. Infra-discovery temp files can be accidentally committed by auto-commit

Running `infra-discovery.sh` uses a temporary JSON file near `data/infra-inventory.json`. Auto-commit may race and commit both `data/infra-inventory.json` and a `data/infra-inventory.json.tmp.*` path if the temp exists during the watcher pass. Future hardening should either make `infra-discovery.sh` use a temp outside the repo or add an ignore pattern for `data/infra-inventory.json.tmp.*`.

## Session validation result

- Hermes: `a05b64d67` → `009b42d00`, `behind=0`, v0.18.0 up to date.
- New patch: `/root/mgs-agent/patches/hermes/mgs-runtime-customizations-2026-07-07.patch`.
- Patch sha256: `dd237f99e2b5e792c962797b5ace5bb74a7b353b9bdb2d8595e000abb4a39f51`.
- Targeted tests: `214 passed, 6 subtests passed`.
- Gateways after repair: Zeus/Atena/Ares/agente legado active; `replace_pids=0`.
