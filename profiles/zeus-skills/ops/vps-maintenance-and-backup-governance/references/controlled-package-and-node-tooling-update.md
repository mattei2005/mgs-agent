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

Use `--only-upgrade` only when every confirmed target is already installed. For an approved kernel transaction containing new images, modules, headers or tools, enumerate every package with its exact version and simulate `apt-get -s --no-install-recommends install package=version ...` without `--only-upgrade`; otherwise the command can omit the very new components needed for the target kernel. Compare the parsed package→target-version map with the frozen manifest, require separate upgrade/new-package counts and zero removals, and stop on any additional dependency or candidate drift.

### Bounded preflight evidence collection

1. Capture `apt-get -s upgrade` and `apt-get -s full-upgrade` with `subprocess.run(..., capture_output=True, text=True)`; check each return code before parsing. Return the transaction summary and rows matching `^(Inst |Remv |Conf |[0-9]+ upgraded)`, not the full automatic-removal advisory. Keep `Remv` rows visible so filtering cannot conceal destructive scope.
2. Query `apt-cache policy` only for the selected packages and retain installed/candidate versions, selected pocket and phasing. Treat a phased package as actionable only when the ordinary upgrade simulation already selects it on this host; an explicit version install alone can override the deferral and is not proof of routine eligibility.
3. Parse `pro status --format json` into `attached` and the `name`/`status` of ESM Apps, ESM Infra and Livepatch; omit account, contract and machine identifiers. Parse `pro security-status --format json` into the relevant counters under `summary`, and reduce `canonical-livepatch status --format json` to running kernel, support and patch state. This proves coverage without exposing unrelated identity metadata.
4. Select canonical inventory rows by known stable IDs. If an ID is unknown, return only candidate IDs/types first, then retrieve the chosen row with an explicit field allowlist; do not print every record whose title broadly matches VPS, maintenance or backup, because historical receipts can dominate the output without answering the live gate.
5. Freeze service effects alongside the package transaction: collect `needrestart -b`, resolve affected units, record protected gateway PIDs and read the existing needrestart exclusion configuration. Inspect the exact candidate DEBs with `dpkg-deb --ctrl-tarfile`, reading their preinst/postinst/prerm/postrm scripts and the relevant installed predecessor scripts before removal/upgrade hooks run. Resolve conditional calls and variables used by `systemctl`, `deb-systemd-invoke` and `invoke-rc.d`; a `.service` name mentioned in a comment, enablement branch or alias is not proof of a restart. Present confirmed or conditional restart/reexec targets and network/DNS/Tailscale reconnection impact in the confirmation. Keep needrestart-driven restarts separate from package-owned hooks: list-only mode and gateway exclusions do not suppress a package's own service actions.
6. Persist the compact plan/checkpoint with installation, restart, reboot, Hermes activation and deletion states explicitly separated. A completed preflight is evidence for a confirmation gate, not a completed update or permission to execute the critical transaction.

A provider dashboard or control-plane boolean such as `securityUpdate=true` is not a package-security verdict. Freeze `apt-cache policy`, the repository pocket, the source-package changelog, and the matching Ubuntu Security Notice/OVAL result. Classify an update from that evidence: when the candidate is only a normal `jammy-updates`/equivalent bugfix and no advisory maps to it, report it as standard maintenance even if the package name contains words such as `audit` or `security`.

For npm, capture current Node/npm/Corepack **and** the npm `package.json` version, then query the exact target metadata:

```bash
npm view npm@TARGET version engines dist.shasum dist.integrity dist.tarball --json
```

Parse this output defensively: when dotted selectors are requested, npm may return flat keys such as `"dist.shasum"`, `"dist.integrity"`, and `"dist.tarball"` instead of a nested `dist` object. Accept either shape, require all fields, and verify the live Node version satisfies `engines.node` before mutation. Persist the successful metadata response before selecting fields. Normalize a top-level object to one record, or select the unique record whose `version` exactly equals the requested target from a returned list; reject zero or multiple matches before calling `.get()` or indexing nested fields. Do not assume either JSON shape from the npm version or selector syntax. Preserve an already downloaded tarball after a parser failure and resume metadata/hash/integrity verification from retained inputs without replaying an APT transaction or downloading the same artifact again. For historical `.deb` identity checks, query `dpkg-deb -f <file> Package` and `Version` separately; a multi-field query adds labels, so positional values are not bare package/version strings.

## 2. Critical confirmation boundary

Before touching `/usr`, present:

- exact current and target versions;
- simulated APT transaction;
- npm/Node compatibility;
- rollback location and contents;
- whether services may restart;
- explicit statement that Hermes and reboot are outside scope unless separately authorized.

Do not treat a general “continue maintenance” as permission to add unrelated packages, restart a deferred system service, update Hermes, or reboot.

### Ubuntu Pro attachment is its own system-config gate

Treat `pro attach` as a production system-configuration mutation, not as a harmless login helper: successful browser confirmation can alter APT entitlement/configuration and enable ESM/Livepatch. Obtain the Critical Subset confirmation **before** starting the attach flow. Then:

1. Confirm live `attached=false` before generating a device code.
2. Run `pro attach` in a silent PTY/background process and poll it manually; never enable asynchronous raw-output delivery in an operational Discord thread.
3. Send the short-lived device URL/code only to the authorized owner for immediate use. Do not persist the code, repeat account email from command output, or include either in audit/inventory.
4. Wait for process exit `0`; a browser “feito” is not local validation.
5. Read back `attached=true` and the statuses of `esm-apps`, `esm-infra`, and `livepatch`. Validate Livepatch separately against the running kernel.
6. Inventory and REPORT the attachment before claiming closure.
7. Treat package installation as a second gate: simulate the newly entitled transaction, freeze exact versions and rollback, and obtain the `/usr` confirmation before applying it.

This separation prevents device authorization from silently expanding into package installation or reboot.

## 3. Build rollback before mutation

Create a mode-`0700` set under:

```text
/root/.hermes/secure-backups/vps-maintenance/<timestamp>/
```

Include:

- a tar.gz of `/usr/lib/node_modules/npm` and Corepack when present;
- a non-secret pre-state JSON with Node/npm/Corepack, exact package versions, service states/PIDs, reboot marker, and authorization message ID;
- the exact previous vendor `.deb` downloaded while it is still available.

If the installed vendor version is absent from the current APT index, try one bounded recovery before falling back to a payload archive: obtain the current candidate's pool URI with `apt-get --print-uris download package=candidate`, derive the exact prior-version URI only when the repository naming pattern is unambiguous, require a successful bounded fetch, and validate the downloaded artifact with `dpkg-deb -f previous.deb Version` against the installed version. Never trust URL substitution alone or print credential-bearing repository URLs. If the historical artifact is unavailable or its metadata differs, use the strict payload fallback below. For a multi-package transaction, download historical packages individually or inventory the output directory after a batch failure; `apt-get download` can return nonzero without leaving a usable partial set, so never infer rollback coverage from the requested package list.

If the previous `.deb` is no longer published and the installed payload must be archived from `dpkg-query -L`, treat that list as untrusted archive input. Filter only recognized diversion annotation rows (`diverted by ... to:`, `locally diverted to:`, and `package diverts others to:`) separately from paths; reject every other nonabsolute row. Ubuntu usr-merge packages can emit the third form for `/bin`, `/lib`, `/lib64` and `/sbin`; it is diversion metadata, never an archive path. Exercise backup/hash helpers against the oldest target Python before the fleet run: Python 3.10 lacks `hashlib.file_digest`, so use a bounded streaming digest when supporting Ubuntu 22.04. On a resumed rollback build, require the prior package receipt's checksum plus complete `dpkg-deb --fsys-tarfile` readback before reusing an artifact; a matching control-header version alone cannot certify an untruncated payload. When reconstructing a rollback `.deb` from installed files, parse Debian control headers at the colon even when the value is empty (not only `: `), so continuation lines of `Conffiles:` cannot contaminate the preceding dependency field. Omit status-only fields from `DEBIAN/control`, write conffiles separately, and keep `DEBIAN` mode 0755 inside the protected mode-0700 maintenance root. Require exact Package/Version, extraction roundtrip, regular-file hash and symlink-target equality; label the artifact reconstructed installed payload, never an original repository package. It commonly contains directory sentinels such as `/.`; passing the raw list to `tar -C /` can archive the entire root filesystem. Build the payload list programmatically and require every entry to be a regular file or symlink. Explicitly reject blank paths, `.`, `/`, `./`, `../`, and every directory before invoking `tar`. Validate the resulting member list against the package manifest and cap/check expected bytes before accepting it as rollback evidence. If an accidental archive exceeds the expected package footprint, stop immediately, preserve/quarantine it without deletion, re-check disk, and rebuild from a strict allowlist.

When a `dpkg-query -L` path is missing from the installed filesystem, do not certify an incomplete reconstruction or silently omit the member. Preserve the failed stage, try the exact previous repository artifact through the bounded historical-URI recovery above, and accept it only after Package/Version plus full payload readback. A missing documentation file is package-payload drift, not proof that rollback coverage is complete.

On usr-merged hosts, distinguish directory sentinels from package-owned symlinks. For canonical root aliases such as `/bin`, `/sbin`, `/lib`, `/lib32`, `/lib64` and `/libx32` listed as ancestor directories by a leaf package, build ordinary private-stage directory scaffolds rather than copying the host's global `usr/*` alias into that package. Copying the alias can first create a dangling private path and then redirect archive members away from the frozen expected member names. Exercise the archive member map against a usr-merge fixture, keep the target manifest fail-closed, preserve failed stages/DEBs and use a distinct corrected stage/output name before resuming validated receipts.

Run maintenance helper scripts with an isolated interpreter (`python3 -I <helper>`) or choose filenames that cannot shadow the Python standard library. A local helper called `inspect.py` can be imported by `dataclasses` during another library import and re-execute its top-level collection; isolate the rerun and reconcile all already-created receipts before repeating any mutation.

When a reconstructed rollback package contains a large embedded runtime, bound compression cost explicitly (for example, `dpkg-deb -Zgzip -z1 --build`) instead of letting default xz compression consume the whole maintenance window. Persist per-package identity/hash/roundtrip receipts as each package completes. After a timeout, verify that no builder/compressor remains, reuse independently validated completed packages, and preserve the incomplete artifact under its original name; build only the missing package to a distinct recovery path. A readable DEB control header is not proof of a complete payload: require the filesystem-tar stream to finish and match every frozen regular-file hash and symlink target.

Generate hashes in shell, then validate:

```bash
sha256sum archive > archive.sha256
sha256sum -c archive.sha256
tar -tzf archive >/dev/null
dpkg-deb -f previous.deb Version
```

Do not print configuration or credential contents.

### Mixed-engine backup and executable-gate safety

- For a cold MariaDB backup, recheck application MEMORY tables with real `COUNT(*)` before the approved stop; exclude `mysql`, `information_schema`, `performance_schema` and `sys` from that application-data predicate. Virtual `information_schema` tables can advertise ENGINE=MEMORY and return metadata rows, so an unfiltered query creates a false nonempty-data blocker. Keep nonempty real application MEMORY state blocking and preserve the failed observation.
- Dispatch a long systemd `Type=oneshot` executor with `systemd-run --no-block` when ownership, not completion, is the intended return point. Without it, the launcher can wait for the oneshot to finish and time out while the real job continues. Reconcile the exact existing unit/PID/result and never repeat the operation from the launcher's timeout alone. For an approved database pause, put bounded production-service recovery in the executor's `finally` and an independent exact-service `ExecStopPost`; validate both success and deliberately failed-copy cases before dispatch.
- Make test/compile gates fail closed across shell or subprocess boundaries: use `set -e`, `&&` or explicit checked return codes before a later upload/dispatch. A failed first command followed by a successful second command is not a passed gate; fix the fixture and reconcile any already-dispatched side effects before continuing.

## 4. Apply APT and npm as separate gates

### APT gate

Install only the exact package/version map exercised by the simulation, with `--no-install-recommends`, noninteractive mode, and `--force-confold` when local conffiles must be preserved. Keep `--only-upgrade` only for an upgrade-only manifest; omit it for explicitly confirmed new kernel components, preserving the same command shape used in their simulation. Never replace the pinned install with an unrestricted `dist-upgrade` merely because that command originally discovered the candidates.

Immediately validate:

- exact `dpkg-query` version;
- role-aware runtime validation: resolve actual unit names from package contents, inventory, and live systemd before asserting service health. A package may be a shared library/PHP extension with no `.service` unit; in that case validate the installed payload, expected INI/module wiring where it is intentionally enabled, and the separate vendor agent service instead of inventing `<package>.service`. Run library smokes with the explicit interpreter/loader that consumes the updated package, not the auditor's inherited virtualenv, because those can resolve different installations. For Debian system-Python packages, use `/usr/bin/python3 -I`; an OAuthlib smoke can instantiate `WebApplicationClient` with a synthetic client ID and assert a locally generated authorization URI using an `.invalid` destination, without credentials or network requests. For shared libssh packages, load each confirmed SONAME separately with `ctypes.CDLL("libssh.so.4")` and `ctypes.CDLL("libssh-gcrypt.so.4")` in that fresh process. Treat these as package usability checks only: successful loading in a new process does not prove that existing daemons have loaded the replacement libraries or eliminate a separately required restart/reboot;
- empty `dpkg --audit`;
- the applied package/version map matches the approved transaction with no extra dependencies or removals. Store approved-transaction predicates under `lot_checks` and refreshed repository observations under `host_currency_checks`; derive lot success only from `lot_checks`, never from `all()` over a mixed check dictionary. Refresh indexes and simulate both upgrade paths independently. When new out-of-scope candidates appear, preserve the completed lot, record their exact before/after versions and prepare a separate confirmation; keep whole-host maintenance open without reinstalling or relabeling the approved lot as failed. Exercise the validator with both cases before use: exact approved versions plus new unrelated candidates must yield lot-pass/host-pending, while any approved-version mismatch must fail the lot. If a mixed validator already emitted failure, retain that original receipt and issue a separately identified classification correction supported by the existing per-check evidence; do not silently rewrite the failed observation or turn its negative host-currency checks green;
- Zeus/Atena/Ares active;
- gateway PIDs unchanged unless their restart was explicitly authorized;
- no priority 0..3 journal errors since the maintenance boundary.

For MariaDB upgrades over an existing database, retain a strict journal failure rather than replaying the installation merely to clear it. The exact pair `mysql.user table already exists!` / `Run mysql_upgrade, not mysql_install_db` can come from the package postinst's deliberately tolerated `mariadb-install-db` branch, whose `ERR_LOGGER` sends even those diagnostics to `daemon.err`. Classify that pair only when the messages, `mariadb-server.postinst` identity, exact executor unit and priority all match, the installed postinst hash equals the inspected candidate, the tolerant existing-database branch is verified, APT returned zero, every approved version and functional check passed, and the native read-only `mariadb-upgrade --check-if-upgrade-is-needed` explicitly reports that no upgrade is needed within the same 10.11 branch (its observed return code is 1). Do not infer failure from an older `mysql_upgrade_info` patch version alone, force a schema upgrade, suppress runtime-daemon errors or waive any additional message. Preserve the original raw journal/verdict, write a separate attribution and fresh health readback, and supersede only the verdict. If the strict checker exited nonzero solely for that verified pair, reset only its already-exited failed unit and prove zero remaining failed units without another production restart. Exercise positive, wrong-source, unknown-message, unhealthy-version and real-upgrade-needed cases before using the classifier.

When freezing or comparing service state, do not parse multiple `systemctl show -p ... --value` properties by positional line order; systemd may emit them in a different order than requested. Query each property separately, or retain `Property=value` names and parse by key. Resolve `Type` and `SubState` before asserting PID health. Require `ActiveState=active` and a positive `MainPID` for long-running daemons before comparing their PIDs; a successful `Type=oneshot` unit with `RemainAfterExit=yes` may correctly be `active/exited` with PID zero. Socket units intentionally have no daemon MainPID: validate active/listening state and actual socket ownership instead. Canonicalize service aliases so one process reached by both a D-Bus alias and its real unit is not counted as two independent consumers. After a Type=simple restart, poll boundedly for the exact executable/version, not just active state: the new PID can briefly still resolve to systemd before it execs Node. Record that convergence before declaring drift or triggering rollback.

For a `nodejs` vendor-package update, inspect the embedded tooling immediately after APT: compare `node --version`, `npm --version`, npm `package.json`, and `corepack --version` with the frozen pre-state before declaring the package gate green. Vendor packages can replace a previously self-updated npm with an older bundled version even when the APT simulation lists only `nodejs`.

- If the authorized Node target is correct but bundled npm regressed, record the intermediate tooling state and branch on the approved manifest: when a separate exact npm target is already confirmed, proceed directly to that target in the npm phase; otherwise recover the **exact compatible pre-state version** within the original rollback scope. Do not reinstall the old npm merely as an intermediate step before an already-approved npm upgrade, silently accept a regression, or select the registry's newest release by implication. Restore Corepack to its frozen version unless its own change was explicitly included.
- For a pre-state npm recovery, fetch metadata for that exact version, require compatible `engines.node`, download it with `npm pack`, verify the published SHA-1 and SHA-512 integrity plus a locally recorded SHA-256, then use the standard global install and rerun `npm ping` plus a real `npm exec` smoke.
- Detect live users of the system Node runtime through each process's resolved `/proc/<pid>/exe`. Do not substring-match `ps` command lines for `/usr/bin/node`, because the probe command itself can contain that text and create false consumers. Scope the post-update assertion to the exact confirmed binary/inode family, including its `(deleted)` predecessor; a concurrent Playwright/vendor SDK can launch its own older embedded Node during the check and is a separate finding, not proof that the confirmed system package failed.
- Before reloading an old MCP stdio consumer within the authorized maintenance scope, freeze its exact PID, executable/inode, argv and parent gateway PID; prove a harmless native read succeeds and inspect the deployed transport's child-recovery implementation. If child reload is covered and native recovery is supported, revalidate that identity immediately before sending one targeted `SIGTERM` to the child only, then wait boundedly for termination/reconnection. Never use broad `pkill` or restart the parent gateway. Read back the replacement PID, `/proc/<newpid>/exe --version`, unchanged gateway PIDs and a successful native read before declaring the consumer updated. A first stale-transport error requires bounded native recovery, not a gateway restart, direct-API bypass or blind repeated signals; if the child cannot safely reload, retain it as an activation residual for the separately authorized restart/reboot.

Record the APT gate before proceeding to npm.

### Isolated Node runtime and release-admission safety

For an approved same-branch Node executable patch pinned by many service/CLI paths, stage and verify the official archive and exact candidate executable separately, then preserve the existing pathname when avoiding an unapproved systemd/config migration. Record the actual new binary version/hash and the intentionally historical prefix explicitly; never claim the entire old distribution tree was upgraded. Freeze source, dependencies, service/config hashes and bounded row-hash financial fingerprints; exercise the candidate with a database connection explicitly read-only before any write. Retain the original executable, configuration/code archive and validated custom dump; only replace the named executable atomically under existing admission/legacy/remote-file locks. On failure restore only that exact owned executable, never unrelated code, data or a third-party change. Treat each retry as a distinct journaled attempt after exact rollback readback.

If a long-lived reader repeatedly reacquires the canonical flock admission barrier and a nonblocking writer times out, identify the real holder and its current operation before acting. A bounded queued exclusive acquisition on the very same kernel lock can preserve the admission protocol without stopping the worker, changing its schedule or editing the persistent guard. Require the canonical safe publication state, legacy locks and remote fence/lock checks after admission; never bypass an active lease or treat a wait timeout as authorization to kill its owner.

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
- when npm itself is an authorized update target, `npm outdated -g --depth=0 --json` returns `{}`;
- for a Node-only package update, npm/Corepack equal the frozen pre-state instead; report any newer npm release as a separate out-of-scope residual rather than failing the Node gate or expanding scope automatically;
- gateways and the security service remain active.

## 5. Interpret needrestart without scope expansion

Run `needrestart -b` after the package work.

- Treat `/var/run/reboot-required` as supporting evidence, not the sole reboot gate. Some valid kernel transactions install the expected kernel without creating that marker. Parse the named `NEEDRESTART-KCUR`, `NEEDRESTART-KEXP`, and `NEEDRESTART-KSTA` fields: when current and expected kernels differ and `KSTA=3`, the reboot phase remains required even if the marker is absent. Record the discrepancy explicitly and validate the new kernel after boot; do not rerun the package transaction merely to manufacture a marker.
- Kernel current and no `/var/run/reboot-required` means no reboot is required only when `NEEDRESTART-KCUR` and `NEEDRESTART-KEXP` also agree.
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
- freeze the live versions of `monarx-agent`, `monarx-protect`, and `monarx-protect-autodetect` before mutation even when only one is an authorized target; an inventory version is not a before-state. If historical inventory is stale, reconcile the other packages from timestamped dpkg/APT history and label the correction separately rather than attributing a previous vendor-cron upgrade to the current transaction;
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
- all approved package versions installed, clean dpkg and no holds; report the fresh global APT pending count separately, with any new out-of-scope transaction awaiting its own gate. Claim whole-host package currency only when host-eligible candidates are zero, and complete VPS maintenance only after every requested activation/reboot phase passes;
- npm target current with `npm outdated {}` when npm was in scope, or exact pre-state npm/Corepack restored with any newer release classified separately when only Node was in scope;
- gateway PIDs and security service state;
- rollback integrity;
- kernel/reboot status;
- deferred services separately;
- Hermes explicitly unchanged when outside scope.
