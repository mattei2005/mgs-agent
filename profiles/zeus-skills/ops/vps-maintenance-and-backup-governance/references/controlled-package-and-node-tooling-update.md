# Controlled Package and Node Tooling Update

## Purpose

Execute a narrowly authorized VPS package/tooling update without turning a small patch into a broad `dist-upgrade`, an unplanned service restart, or an unverified npm self-update.

Use this after the audit has identified exact APT and global Node targets and Rodolfo has authorized the maintenance scope.

## 1. Freeze exact package identities

1. Refresh APT indexes.
2. Read `Installed` and `Candidate` from `apt-cache policy <package>`.
3. Use the **literal candidate string**, including vendor suffixes such as `-master`, in simulations and installs. Do not shorten `4.3.51-master` to `4.3.51`; APT treats them as different versions.
4. Simulate the exact command:

```bash
apt-get -s install --only-upgrade package=exact-candidate
```

Require the expected package count, zero removals, and no unexpected dependencies. Any candidate or transaction drift changes scope and stops execution.

For npm, capture current Node/npm/Corepack and query the exact target metadata:

```bash
npm view npm@TARGET version engines dist.shasum dist.integrity dist.tarball --json
```

Verify the live Node version satisfies `engines.node` before mutation.

## 2. Critical confirmation boundary

Before touching `/usr`, present:

- exact current and target versions;
- simulated APT transaction;
- npm/Node compatibility;
- rollback location and contents;
- whether services may restart;
- explicit statement that Hermes and reboot are outside scope unless separately authorized.

Do not treat a general “continue maintenance” as permission to add unrelated packages, restart a deferred system service, update Hermes, or reboot.

## 3. Build rollback before mutation

Create a mode-`0700` set under:

```text
/root/.hermes/secure-backups/vps-maintenance/<timestamp>/
```

Include:

- a tar.gz of `/usr/lib/node_modules/npm` and Corepack when present;
- a non-secret pre-state JSON with Node/npm/Corepack, exact package versions, service states/PIDs, reboot marker, and authorization message ID;
- the exact previous vendor `.deb` downloaded while it is still available.

If the previous `.deb` is no longer published and the installed payload must be archived from `dpkg-query -L`, treat that list as untrusted archive input. It commonly contains directory sentinels such as `/.`; passing the raw list to `tar -C /` can archive the entire root filesystem. Build the payload list programmatically and require every entry to be a regular file or symlink. Explicitly reject blank paths, `.`, `/`, `./`, `../`, and every directory before invoking `tar`. Validate the resulting member list against the package manifest and cap/check expected bytes before accepting it as rollback evidence. If an accidental archive exceeds the expected package footprint, stop immediately, preserve/quarantine it without deletion, re-check disk, and rebuild from a strict allowlist.

Generate hashes in shell, then validate:

```bash
sha256sum archive > archive.sha256
sha256sum -c archive.sha256
tar -tzf archive >/dev/null
dpkg-deb -f previous.deb Version
```

Do not print configuration or credential contents.

## 4. Apply APT and npm as separate gates

### APT gate

Install only the simulated package/version with `--only-upgrade`, `--no-install-recommends`, noninteractive mode, and `--force-confold` when local conffiles must be preserved.

Immediately validate:

- exact `dpkg-query` version;
- role-aware runtime validation: resolve actual unit names from package contents, inventory, and live systemd before asserting service health. A package may be a shared library/PHP extension with no `.service` unit; in that case validate the installed payload, expected INI/module wiring where it is intentionally enabled, and the separate vendor agent service instead of inventing `<package>.service`;
- empty `dpkg --audit`;
- zero unexpected APT candidates;
- Zeus/Atena/Ares active;
- gateway PIDs unchanged unless their restart was explicitly authorized;
- no priority 0..3 journal errors since the maintenance boundary.

Record the APT gate before proceeding to npm.

### npm gate

Before install, download the registry tarball to a temporary directory and verify it against the published shasum. Prefer the standard self-update first:

```bash
npm install -g npm@TARGET --no-audit --no-fund --no-progress
```

Use the manual verified-tarball replacement path only if the standard self-update fails; report both attempts. After success require:

- `npm -v` and npm `package.json` both equal the target;
- Node/Corepack unchanged unless included in scope;
- `npm ping` succeeds;
- a real `npm exec` smoke succeeds;
- `npm outdated -g --depth=0 --json` returns `{}`;
- gateways and the security service remain active.

## 5. Interpret needrestart without scope expansion

Run `needrestart -b` after the package work.

- Kernel current and no `/var/run/reboot-required` means no reboot is required.
- A deferred unrelated service such as `systemd-logind.service` is a **documented residual**, not permission to restart it.
- If that service was not named in the confirmed scope, report it and obtain separate authorization before restart—especially when SSH/user sessions may be affected.
- Do not call a clean package transaction failed solely because a separate deferred service remains.

## 6. Close a separately authorized deferred service safely

When Rodolfo separately authorizes a deferred service restart such as `systemd-logind.service`:

1. Freeze the service state/PID, `loginctl list-sessions`, protected gateway/security PIDs, failed units, reboot marker, and current `needrestart -b` output.
2. Record an audit start boundary with the exact authorization message ID.
3. Restart only the named service; do not bundle gateways, user managers, logout, or reboot.
4. Validate the service is active with a new PID, the current administrative session remains usable, Zeus/Atena/Ares and security-service PIDs are unchanged, failed units remain zero, and no warning/critical journal entries appeared.
5. Re-run `needrestart -b`. Acceptance for the service is **zero `NEEDRESTART-SVC` rows**. Remaining `NEEDRESTART-SESS` rows are stale userspace sessions, not a failed service restart or reboot requirement; they normally clear on logout/reconnection. Do not force logout or restart the root user manager without separate scope.
6. Clear the deferred-service residual in the existing runtime baseline, preserve the stale-session note, record audit readback, and publish REPORT-INFRA.

## 7. Close an authorized reboot as a durable phase

When the package gate leaves `/var/run/reboot-required`, the VPS phase remains open until a new boot is proven healthy.

1. Before reboot, record the current boot ID, active Hermes launcher/version, exact package versions, `/tmp` owner/mode, failed units, and gateway states. When Hermes is deferred, assert its launcher will remain unchanged across boot.
2. Use an external/durable post-reboot validator rather than relying on the active gateway turn to survive its own host reboot. The validator must be self-contained, must not activate deferred application work, and must check the new boot ID against the recorded one.
3. Post-boot acceptance requires: changed boot ID; absent reboot marker; exact package versions; `root:root 1777` on `/tmp`; zero APT candidates, holds, `dpkg --audit` findings, failed units, and priority 0..3 boot errors; current kernel agreement in `needrestart`; cron/security agent active; Zeus/Atena/Ares active with positive PIDs and fresh Discord-connected log markers; deferred Hermes launcher/version unchanged.
4. Do not let a scheduled validator become a duplicate asynchronous conclusion. If Rodolfo asks for status before it runs, inspect the live host first, pause/remove the pending validator, complete the checks in foreground, and deliver one canonical result. If it already ran, read its actual output before replying.
5. Persist a compact validation artifact, update the existing inventory entries rather than duplicating them, close the checkpoint, append audit readback, and send one canonical REPORT-INFRA embed. Remove any one-shot validator after foreground completion.
6. Communication is binary-first: `sim, VPS concluída` only after all post-boot gates pass; otherwise `não, <single remaining gate>` before details. Never describe `packages updated; reboot pending` as complete maintenance.
7. Prefer a durable one-shot systemd unit that is enabled before reboot, writes into the validated maintenance backup, waits for fresh gateway readiness, posts one clean conclusion, and disables/removes only itself after persisting result/audit/inventory. Validate both the result artifact and cleanup (`unit not-found/inactive`) on the next foreground readback; a cached `Result=success` alone is insufficient.
8. Filter agent-log and journal evidence by the **new boot boundary** (boot ID or boot timestamp). Arbitrary tail windows contain historical ERROR/Traceback markers and can create false post-reboot alarms even when `journalctl -b` is clean.
9. On a second-pass audit, classify residuals instead of collapsing them into “VPS dirty”: normal APT candidates/reboot markers are OS maintenance; Ubuntu Pro/ESM-only fixes are an entitlement decision; a deferred Hermes port is application lifecycle; failed DTR/SB writes are application operations. Report each owner/scope separately and do not expand the authorized maintenance scope.
10. Parse `pro security-status --format json` defensively from `summary`: schema variants can expose `packages` as a list and omit a `services` object. `num_standard_security_updates`, `num_esm_apps_updates`, `reboot_required`, and `summary.ua.attached` are the stable decision fields; never make a clean/dirty claim from an assumed nested shape.

## 8. Reconcile canonical services and inventory

Do not guess unit names. Resolve operational services from `data/infra-inventory.json` and live systemd readback; for example, the active MGS auto-commit unit may differ from an assumed name.

Cron/control-plane reconciliation has two common traps:

- `log_stat.exists=false` is not automatically a failed job. A crontab may redirect stdout to `/dev/null` while the called wrapper writes its own canonical log internally. Read the cron command and wrapper before classifying the absence.
- With `set -euo pipefail`, a wrapper that pipes a child through `tee` can exit immediately when the child returns nonzero, before its intended `PIPESTATUS`, `END rc=...`, or cleanup lines run. A final `START` without `END` therefore requires reading the child’s structured result and checking whether its failure is infrastructure, authentication already recovered, or an application write that awaits retry. Do not call the whole VPS unhealthy from the missing footer alone.

When Monarx changes:

- update the existing `monarx-security-agent` inventory entry rather than adding a duplicate;
- reconcile all Monarx package versions against `dpkg-query`;
- use APT history to attribute versions changed earlier by the weekly vendor cron.

Update the existing VPS runtime baseline with npm/Corepack, rollback path, validation gates, residuals, and authorization IDs. Finish with audit readback and canonical REPORT-INFRA.

## 9. Retire a quarantined invalid backup only after VPS closure

An interrupted or oversized archive is not rollback evidence. Keep it quarantined until the package transaction, reboot when required, and post-boot gates are all complete. Cleanup is a separate destructive boundary:

1. Obtain the Critical Subset double-confirmation with the exact directory, current file/directory counts, exact bytes, irreversible result, retained valid backup, and projected disk usage.
2. Immediately before deletion, canonicalize the target and require an exact allowed path; reject symlinks, mounts, parent drift, nested symlinks, or changed counts/bytes. Never use a wildcard or delete the maintenance parent.
3. Revalidate the retained backup first (`sha256sum -c` for every manifest entry). Record an audit-start event with the confirmation message ID and the frozen target set.
4. Delete only the frozen directory. On any exception, write a partial/failure audit boundary and stop; never imply full reclamation.
5. Validate target absence, measure actual reclaimed bytes from filesystem free space, re-run the retained backup hashes, and confirm package/reboot/service health is still green.
6. Preserve the pre-cleanup validation artifact as historical evidence; write a separate cleanup-result artifact. Update the existing inventory/checkpoint entry with the deletion receipt, then send one canonical REPORT-INFRA embed and validate Discord readback.

Report authorized bytes and actual reclaimed bytes separately: filesystem accounting may differ slightly from logical directory size.

## Acceptance summary

A successful narrow maintenance reports:

- exact before/after versions;
- APT pending `0`, npm outdated `{}`, clean dpkg, no holds;
- gateway PIDs and security service state;
- rollback integrity;
- kernel/reboot status;
- deferred services separately;
- Hermes explicitly unchanged when outside scope.
