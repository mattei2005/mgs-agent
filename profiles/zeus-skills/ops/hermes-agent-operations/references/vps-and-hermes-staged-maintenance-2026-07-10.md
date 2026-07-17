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
5. After every batch, require `dpkg --audit` clean and Zeus/Atena/Ares/agente legado + cron/autocommit active.
6. Keep Node package-manager updates separate from APT:
   - verify target `engines.node` via `npm view`;
   - archive `/usr/lib/node_modules/npm` and `corepack` outside Git;
   - verify archive checksum and readability;
   - update Corepack first, then npm major;
   - validate `corepack --version`, `npm --version`, `npm ping`, `npm exec`, and `npm outdated -g`.
7. Final closure requires: `apt list --upgradable` empty, `npm outdated -g` empty, no held packages, clean `dpkg`, zero failed units, zero new journal errors, and explicit reboot state.

Validated result in this session: 19 APT packages, Corepack 0.34.6→0.35.0, npm 10.9.8→12.0.0, Node v22.23.1 retained, no reboot required.

### Freshness and OpenSSH safety gates

A statement such as “the VPS has no updates” is a timestamped package-index snapshot, not a durable fact. Before giving a categorical answer:

1. Record the check timestamp and inspect `apt-daily`/package-list freshness. If the user asks for the current state and policy permits metadata refresh, refresh first; otherwise state explicitly that the result uses the current cache.
2. If a later check differs, reconcile repository metadata timestamps before calling the earlier result wrong: 1Password and Ubuntu security indexes can publish or refresh hours after the first audit.
3. For OpenSSH upgrades, simulate exact packages and require `0 newly installed, 0 removed`; never mix `apt autoremove` into the security batch.
4. Before install, require `sshd -t`, active `ssh.service`/`ssh.socket`, port 22 listening, clean `dpkg --audit`, package versions, service PIDs, and a mode-0600 archive of `/etc/ssh` with checksum. Preserve local conffiles (`--force-confold`) unless an explicit config migration was reviewed.
5. On Ubuntu socket activation, the package transition can leave `ssh.socket` listening while `ssh.service` is inactive and `/run/sshd` absent. A bare post-install `sshd -t` then exits 255 even though port 22 remains available. Correct once by starting `ssh.service`; systemd recreates `RuntimeDirectory=sshd`. Then rerun `sshd -t`, verify service + socket + port 22, package versions, `dpkg --audit`, gateways, pending packages, and reboot state. Report both the initial failure and the corrected validation.
6. Store verbose APT output in a protected report/log. Human operational threads receive only the executive result; structural evidence and anomalies go to `#alerts-infra`.

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