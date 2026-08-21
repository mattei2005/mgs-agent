# Checkpoint store CPU spikes and lock contention

Use when `htop` shows repeated `git add -A` / `git pack-objects`, gateway logs show `checkpoints/store/indexes/<hash>.lock`, or checkpoint stores repeatedly exceed `checkpoints.max_total_size_mb`.

## Diagnose

1. Identify the process owner and command from `ps`/`journalctl`; distinguish the Hermes checkpoint store from `/root/mgs-agent` auto-commit.
2. Read the active profile's `checkpoints` config and compare `max_total_size_mb` with `git --git-dir=<store> count-objects -vH` plus `du -sh <store>`.
3. Map project hashes from `store/projects/*.json` without reading checkpoint contents.
4. Time `git add -A` only with a copied temporary `GIT_INDEX_FILE`; do not mutate the production per-project index for benchmarking.
5. Inspect `_take`, `_enforce_size_cap`, `_prune`, and the tool-executor checkpoint call path. In v2, per-project indexes do not protect shared objects/refs/gc or a same-project multi-command transaction.

## Failure classes

- `git add -A` near 100% in `htop` usually means one logical CPU; it is not whole-host saturation on a multi-vCPU VPS.
- Repeated `<index>.lock` errors mean concurrent checkpoint transactions reached the same per-project index.
- If the packed floor already exceeds `max_total_size_mb`, every new checkpoint can enter size-cap enforcement and `git gc`, creating repeated `pack-objects` CPU/I/O spikes even when pruning cannot reach the configured cap.
- A new advisory lock file under `CHECKPOINT_BASE` must be reserved in `_migrate_legacy_store`; otherwise first initialization moves it into `legacy-*`, breaking mutual exclusion and creating phantom legacy archives.

## Corrective pattern

1. Serialize the whole `_take` transaction with a profile-local, cross-process advisory lock: init/read-tree/add/write-tree/update-ref/prune/gc all remain inside one lock.
2. Keep the lock fail-safe and bounded; checkpoint failure stays non-fatal.
3. Use only guaranteed runtime dependencies. A standard-library POSIX `fcntl.flock` / Windows `msvcrt.locking` implementation avoids optional-package import failures.
4. Set each MGS profile's `checkpoints.max_total_size_mb` above the observed irreducible packed floor. Preserve retention and checkpoint enablement; do not delete checkpoint history as an incidental fix.
5. Mirror live profile config to `/root/mgs-agent/profiles/<agent>-config.yaml`.
6. Generate a supplemental patch from the verified live diff, include it in `ensure-hermes-mgs-patches.sh`, and explicitly add it to `run-hermes-update-controlled.sh` pre-upstream patch coverage.

## Validation

- `py_compile` on source and tests.
- Real concurrent test with several independent `CheckpointManager` instances and a barrier: exactly one snapshot, duplicate workers skip, zero `index.lock` errors.
- Full checkpoint/tool-executor/config/prune tests.
- Canonical MGS patch guard passes.
- Supplemental patch reverse-checks on the live port and apply-checks against current `origin/main` using a temporary index.
- Live config and versioned mirrors read back as the same numeric type/value.
- Do not claim active runtime until gateways have restarted through the safe detached flow; source/config on disk can be validated while the running gateway still holds the old imported module/config.

## MGS incident evidence (2026-08-20)

Zeus and Ares stores were above the 500 MiB cap (about 617 MiB and 532 MiB packed). The full-tree `git add -A` benchmark was short (~0.74s on `/root/mgs-agent`); the recurring problem was concurrent checkpoint transactions plus size-cap-triggered pack/gc. The accepted correction added whole-transaction serialization and raised the MGS cap to 1 GiB without deleting history.
