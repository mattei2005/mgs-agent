# VPS + Hermes staged maintenance — 2026-07-10

Use this session note as evidence for two reusable maintenance patterns: completing phased VPS updates safely and preventing a stale Hermes patch precheck from producing false drift.

## 1. Completing all VPS updates in isolated batches

When normal `apt upgrade` leaves phased packages pending, do not force everything in one opaque command.

1. Simulate each subsystem with explicit package names and `apt-get -s install --only-upgrade ...`.
2. Require zero removals and zero unexpected new dependencies before execution.
3. Snapshot package versions, gateway states, `dpkg --audit`, reboot flag, Node/npm/Corepack versions.
4. Update explicit batches separately. Validated grouping:
   - Apport/Python diagnostics
   - libheif/image libraries
   - fwupd libraries/runtime
   - Plymouth/boot visuals last
5. After every batch, require `dpkg --audit` clean and Zeus/Atena/Ares/Hera + cron/autocommit active.
6. Keep Node package-manager updates separate from APT:
   - verify target `engines.node` via `npm view`;
   - archive `/usr/lib/node_modules/npm` and `corepack` outside Git;
   - verify archive checksum and readability;
   - update Corepack first, then npm major;
   - validate `corepack --version`, `npm --version`, `npm ping`, `npm exec`, and `npm outdated -g`.
7. Final closure requires: `apt list --upgradable` empty, `npm outdated -g` empty, no held packages, clean `dpkg`, zero failed units, zero new journal errors, and explicit reboot state.

Validated result in this session: 19 APT packages, Corepack 0.34.6→0.35.0, npm 10.9.8→12.0.0, Node v22.23.1 retained, no reboot required.

## 2. Hermes precheck must follow the promoted canonical patch

A hardcoded patch name in `run-hermes-update-controlled.sh` can become stale even when `ensure-hermes-mgs-patches.sh` already promotes a newer runtime patch. In this session, precheck tested `mgs-runtime-customizations-2026-07-05.patch` while the guard's primary patch was `mgs-runtime-customizations-2026-07-07.patch`, producing a misleading drift report.

Permanent fix pattern:

1. Discover the latest top-level `mgs-runtime-customizations-*.patch` deterministically.
2. Fail closed if `ensure-hermes-mgs-patches.sh` does not explicitly reference that same latest patch.
3. Test that latest runtime patch plus separately maintained patches such as `mgs-auto-reasoning-routing.patch` against `origin/main` in an isolated worktree.
4. Do not classify drift from an older superseded patch as current update risk.
5. When creating a new canonical port, promote it in the guard before the final precheck.

Validated v0.18.2 result: current runtime patch and reasoning patch both applied cleanly to upstream `f8361d29c`; patch guard and `py_compile` passed; targeted validation returned 222 passed + 6 subtests.

## 3. No-restart Hermes activation boundary

For updates where gateway activation must be separately approved:

- Prefer reversible `git stash push -u` over `git reset --hard` when the saved local surface can be preserved without destructive cleanup.
- Fast-forward to upstream, apply the canonical guard, reinstall Python deps, run `npm ci`, and build web/TUI while existing gateways retain their old loaded code.
- Validate profiles against the pre-update backup, run CLI smokes for all profiles, and prove no `gateway run --replace` processes exist.
- Report the repository as updated/staged, but do not claim gateways run the new version until the detached safe restart completes.

A bundled-skill diff caused only by `scripts/__pycache__/*.pyc` is a local artifact, not a useful customization. Back it up/move it out, rebaseline intentionally, and verify all profiles return no modified bundled skills before closure.