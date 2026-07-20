# Hermes v0.18.2 controlled no-restart update — 2026-07-10

Use this reference when a large Hermes upstream delta must be staged while Zeus/Atena/Ares/agente legado remain online until a separately confirmed activation restart.

## Validated result before activation

- Live repo: `009b42d00` / v0.18.0 → `f8361d29c` / v0.18.2.
- Delta: 271 commits, 434 files.
- Canonical patches `mgs-runtime-customizations-2026-07-07.patch` and `mgs-auto-reasoning-routing.patch` both applied cleanly to the pinned upstream SHA.
- Isolated and live validation: patch guard + py_compile; targeted suite `222 passed, 6 subtests passed`; web and TUI builds passed; CLI smokes Zeus/Atena/Ares/agente legado 4/4.
- Profiles `config.yaml`, `SOUL.md`, and sanitized auth state matched the pre-update backup exactly.
- Update was staged without restarting gateways; running gateway PIDs remained unchanged until explicit activation approval.

## Durable precheck fix: never hardcode an old canonical patch

Failure mode found: `ensure-hermes-mgs-patches.sh` had already promoted the 2026-07-07 runtime patch, but `run-hermes-update-controlled.sh` still tested the 2026-07-05 patch. The precheck therefore reported irrelevant drift even though the current patch and live diff applied cleanly.

Required contract:

1. Discover the newest top-level `mgs-runtime-customizations-*.patch` dynamically.
2. Verify `ensure-hermes-mgs-patches.sh` explicitly references that same artifact.
3. Test that artifact plus separately maintained patches (for example reasoning routing) against pinned `origin/main`.
4. Fail closed when latest artifact and guard disagree.
5. When a new port is created, promote it in the guard before the final precheck.

## Manual no-restart update pattern

Avoid the official `hermes update` path when restart isolation is required; it may autostash and restart gateways despite wrapper-level `RESTART_GATEWAYS=0`.

Validated safer sequence:

1. Run full precheck and create profile backup/evidence.
2. Validate canonical patches in an isolated worktree first.
3. Save tracked/cached local diffs to the report and patch archive.
4. Prefer `git stash push -u` over `git reset --hard`: it preserves tracked and untracked local state reversibly and avoids a destructive reset.
5. Fast-forward live repo with `git merge --ff-only origin/main` pinned to the reviewed SHA.
6. Run the MGS patch guard to reapply the validated local surface.
7. Refresh Python dependencies with `uv pip install --python <venv-python> -e '<repo>[all]'`.
8. Run root `npm ci`, web build, and TUI build when their workspaces exist.
9. Require HEAD=origin, behind=0, expected local patch surface, unchanged gateway PIDs, and zero `gateway run --replace` processes.
10. Re-run targeted tests and per-profile CLI smokes before asking for restart confirmation.

## Bundled skill artifact cleanup

`hermes skills list-modified` may detect a generated `scripts/__pycache__/*.pyc` inside a bundled skill. Classify with `hermes -p <profile> skills diff <skill>` before touching it.

For an artifact-only diff:

1. Rely on the verified profile backup, and move the artifact to a secure rollback directory instead of irreversibly deleting it when deletion requires critical confirmation.
2. Run `hermes -p <profile> skills reset <skill>` without `--restore` to rebaseline the cleaned current copy.
3. Require `No user-modified bundled skills` for root + Zeus/Atena/Ares/agente legado before activation.

## Detached activation finalizer

Restart only after a separate explicit confirmation. Use an external `systemd-run --no-block` finalizer with a lock; Ares/agente legado/Atena first and Zeus last. The active Discord turn must not poll the restart.

Validation details:

- Record pre-restart PIDs and agent-log byte offsets.
- After restart, require every service `active/running`, `ExecMainStatus=0`, fresh PIDs, and no `gateway run --replace` process.
- Systemd journal may not contain Discord readiness markers. Validate fresh `✓ discord connected` / `Gateway running with` lines from each profile's `logs/agent.log`, reading only bytes appended after the saved offset.
- Priority=err journal lines at the restart timestamp are evidence, not automatic failure, when new services are healthy and smokes pass.
- Re-run patch guard, version/behind check, bundled-skill check, and four CLI smokes.
- Update infra inventory and audit before reporting success.
- Deliver the clean result to the originating thread from the detached finalizer; send `[REPORT-INFRA]` only to `#alerts-infra`, never inline in the operational thread.

## Pitfalls

- Run pytest from the Hermes checkout/worktree; a correct suite launched from another cwd fails as “file not found”. Keep multiline target lists in one shell command or use explicit continuations so a bare `pytest -q` does not accidentally collect the parent filesystem.
- A static compatibility scan is advisory; `git apply --check`, guard, compile, builds, tests, and real smokes are authoritative.
- Large profile backups can take minutes and exceed 1 GB. A nominal precheck may still create a multi-GB backup, so record that side effect, checksum it, and recheck disk/retention before staging.
- For a large drifted customization surface, make a temporary commit from the exact live tracked + untracked snapshot, cherry-pick it onto the frozen upstream SHA, resolve only semantic conflicts, and require both path-set equality and byte-for-byte equality before promoting the consolidated patch. Generate the canonical patch as `git diff --binary <target>..HEAD`, then test apply and reverse-apply in a second clean checkout.
- Patch guards must detect the exact broken construct they know how to repair. A broad grep such as any occurrence of `getattr(event, "internal", False)` can match valid upstream code and enter a repair branch whose expected defect is absent. Pair exact predicates with exact post-repair invariants.
- A successful response string is not a successful CLI smoke when the process exits nonzero afterward. `hermes -z` must drain `shutdown_memory_provider(messages)` before `agent.close()` in a `finally` path; otherwise Honcho writer/sync daemon threads can survive until interpreter finalization and produce `SIGABRT`/exit 134 after the answer was printed. Require expected output **and rc=0**, and add a unit test for cleanup order plus a real one-shot smoke.
- Build the next Python environment in isolation. After install, compare sorted `pip freeze` and run `uv pip check`; when active and next environments are identical, do not introduce an unnecessary venv swap.
- `pgrep -af '<pattern>'` can count its own diagnostic command. For zero-process gates such as `gateway run --replace`, inspect `/proc/*/cmdline` or otherwise require the Hermes executable and exact argv tokens.
- A PID mismatch alone is not a restart finding. Reconcile `MainPID` with `ActiveEnterTimestamp`, `ExecMainStartTimestamp`, process `lstart`, audit, inventory, REPORT-INFRA, Git, and session history before classifying concurrent change. Process start timestamps predating the maintenance prove the staged checkout has not been activated.
- Do not claim gateways run the new code until the detached restart and post-restart validation complete.
