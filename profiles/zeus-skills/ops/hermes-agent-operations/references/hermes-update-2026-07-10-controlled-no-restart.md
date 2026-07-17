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

- Run pytest from the Hermes checkout/worktree; a correct suite launched from another cwd fails as “file not found”.
- A static compatibility scan is advisory; `git apply --check`, guard, compile, builds, tests, and real smokes are authoritative.
- Large profile backups can take minutes and exceed 1 GB. Verify existence/size/checksum and retention; do not mistake quiet tar output for a hang.
- Do not claim gateways run the new code until the detached restart and post-restart validation complete.
