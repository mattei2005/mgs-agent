# Durable post-reboot validator pattern

Use this when an authorized package window ends in a host reboot that the active gateway cannot safely validate inside its own Discord turn.

## Pre-reboot freeze

Capture into a mode-`0700` secure maintenance set:

- authorization message and source thread;
- current boot ID, kernel and reboot marker;
- exact package installed/candidate versions and the simulated transaction;
- active Hermes launcher, runtime repo and local HEAD;
- states/PIDs for gateways, security/vendor agents, QEMU, cron and auto-commit;
- each gateway log size as the readiness offset;
- `/tmp` owner/group/mode;
- exact previous vendor `.deb` when available, plus a SHA256 manifest validated before mutation.

For systemd pre-state, never assume that multiple `systemctl show -p ... --value` lines preserve the caller's property order. Query `ActiveState`, `MainPID`, restart count, and exit status separately, or parse named `Property=value` output by key. A swapped PID/state field can make a healthy service snapshot unusable as reboot evidence.

Freeze Hermes by stable runtime identity: canonical launcher target, runtime repository, local HEAD, and release/version prefix. Do not compare the entire `hermes --version` banner across a long preflight—the displayed upstream tip or behind count can change when remote `main` advances even though the active runtime is byte-for-byte unchanged. Treat a later upstream commit as a new update candidate, not pre-reboot drift.

Do not call `packages updated; reboot pending` complete maintenance.

## Package gate before reboot

Require literal candidate versions and exact equality between the confirmed and simulated package/version sets, including separate counts for upgrades and newly installed packages. Allow new kernel components only when their identities and versions were included in the confirmation; require zero unapproved additions, removals or holds. Require `dpkg --audit` clean, no remaining actionable normal APT transaction, expected service-only restarts, gateway PIDs unchanged, and no priority 0..3 journal errors since the maintenance boundary. Preserve the complete install log under the secure maintenance set. Classify phased deferrals under the skill's standing phasing rule instead of forcing them into the transaction.

## Durable validator design

Create a self-contained one-shot systemd unit before reboot:

- `After=network-online.target` plus the named gateway/vendor services;
- `Type=oneshot`, bounded timeout and logs under the secure maintenance set;
- enabled for the next multi-user boot;
- no dependency on the active conversation surviving;
- one clean user conclusion and one canonical REPORT-INFRA only;
- disable the one-shot unit after recording the result so it cannot rerun on later boots; remove its files only through an authorized cleanup boundary, otherwise retain the disabled definition as an explicitly inventoried artifact.

Use the canonical Discord transport `/root/mgs-agent/scripts/discord-bot-post.py` and REPORT helper `/root/mgs-agent/scripts/send-report-infra-embed.sh`; never parse, print or embed the bot token in the validator.

Read back an asynchronous systemd dispatch with bounded convergence, not a single immediate assertion. After `systemd-run --no-block` returns a unit name, poll that exact unit with `systemctl show <unit> -p ActiveState -p SubState -p MainPID -p ExecStart`: require `active/running`, a positive PID and the frozen command for a waiting executor, or inspect its durable result if it already exited. An initial `activating` state is not proof of failed creation. Preserve the returned unit identity and reconcile it before any retry, because creating another executor can duplicate the reboot. Record the dispatch receipt only after this readback; it proves executor readiness, never reboot completion.

Check expected inactivity without a success-only subprocess wrapper. `systemctl is-active <unit>` normally returns status `3` with `inactive`; capture its return code and stdout explicitly when validating that a next-boot unit has not started. Treat `failed`, `unknown`, or a missing unit separately instead of accepting every nonzero code as expected inactivity.

## Post-boot acceptance gates

The validator must prove all of the following from live state:

1. boot ID changed;
2. running kernel equals the frozen expected kernel and `/var/run/reboot-required` is absent;
3. exact package versions match;
4. fresh APT metadata, no actionable normal transaction in either upgrade simulation, zero holds and clean `dpkg --audit`; report verified phased deferrals separately;
5. `/tmp` is `root:root 1777`;
6. zero failed units and zero priority 0..3 boot journal entries;
7. `needrestart` current/expected kernel agree;
8. gateways, Monarx/security agent, QEMU and cron are active with positive PIDs, while every intentionally inactive service matches its frozen authorized expected state;
9. gateway readiness includes a fresh Discord-connected marker after each frozen pre-reboot log offset—service `active` alone is insufficient;
10. Hermes launcher and local HEAD remain exactly unchanged when application work is deferred.

For a service intentionally held inactive, inspect both `ActiveState` and `UnitFileState` before reboot. An enabled unit that is merely stopped will start again during boot; preserve the authorized inactive state by disabling or otherwise persistently gating startup inside the exact confirmed scope, then require inactive/PID `0` after boot. Never encode a blanket “all services active” acceptance rule when the canonical expected-state registry says otherwise.

For SSH health after reboot, resolve service versus socket activation before requiring a daemon PID. With `ssh.socket` enabled and active/listening on port 22, `ssh.service` may correctly remain inactive/PID 0 until the first connection. A premature `sshd -t` can also fail only because `/run/sshd` is intentionally created by the service's `RuntimeDirectory=sshd` at socket activation. Validate a real port-22 listener, then use one bounded local read-only SSH-banner probe to exercise the existing activation path and rerun `sshd -t`; never create the runtime directory manually or restart/reconfigure SSH merely to satisfy the verifier. Test closed socket, missing/invalid banner and invalid-config cases as failures. If a status request takes over a still-running validator after its runtime receipt exists, stop only that validator before replacing its verdict, reconcile any report already sent, preserve its historical receipt/dispatch hashes, and do not replay package installs or exhausted external-network retries.

For gateway runtime identity under a UV-backed virtualenv, do not compare only `/proc/<pid>/exe` with the venv path: the kernel resolves that symlink to UV's shared base interpreter and creates a false mismatch. Require the process command line to start with the exact frozen `<runtime>/.venv/bin/python`, followed by the canonical Hermes launcher and the expected `-p <agent> gateway run` arguments; pair this with the fresh Discord marker and active PID.

For one-shot Hermes smokes, do not require the expected answer marker to be the first or final non-empty combined-output line. Depending on the upstream CLI lifecycle, a benign status line such as `1Password: applied N secret(s)` can appear before or after the answer. Require exit code zero, exactly one marker in the complete output, remove only an explicit allowlist of non-secret status lines, and require the remaining substantive lines to equal exactly `[marker]`.

A priority error emitted in the current boot remains a failed post-boot health gate even when older journals prove that the underlying defect predates the maintenance. Separate **causality** from **acceptance**: label it pre-existing for attribution, preserve the failed gate for current health, investigate read-only, and open a new exact manifest for any system-file, ACL, service or package repair. Never absorb that repair into the earlier reboot authorization or rewrite the reboot result as fully green.

Report inaccessible ESM Apps updates as a separate residual; do not fold them into the zero normal APT-candidate gate or silently attach Ubuntu Pro.

Before making LVFS metadata availability a VPS-completion gate, inspect `fwupdmgr get-devices --json` and each device's `Flags`. If no guest-visible device has an `updatable*` flag, classify firmware metadata as not applicable to this guest's update transaction, preserve any HTTP failure as a non-blocking external residual, and never describe that classification as a successful refresh. KVM by itself is not enough to waive the gate: a VM may expose an updatable UEFI dbx device. Require a successful device inventory and test both no-updatable-device and updatable/updatable-hidden cases; keep the gate blocking when applicability is unknown or a supported update path exists.

## Governance closure

Use a two-process boundary: the validator proves runtime health and exits; a separate cleanup/closure process runs only after that exit. When native same-session continuation is also armed, persist the validator unit, result path and bounded wait in the checkpoint before dispatch. On resumption, wait for that exact validator to exit and consume its atomic final receipt before updating the same inventory/checkpoint, announcing completion or starting the next maintenance phase; gateway reconnection can precede validator completion and otherwise creates parallel closure writers. If the validator is missing, times out or exits without a final receipt, reconcile its logs and partial effects rather than replaying the package transaction or reboot. Close in this order:

1. the validator writes an atomic compact result JSON, appends the validation audit readback, updates the existing VPS/vendor inventory records, and closes or fails the checkpoint;
2. the validator disables future execution without unlinking its active unit definition, records `validated_pending_cleanup`, and exits;
3. after confirmed validator exit, take the authorized closure branch: an external cleanup unit ordered `After=<validator>.service`, or foreground reconciliation, removes the exact authorized unit file, reloads systemd and proves `LoadState=not-found`/inactive; if deletion was not authorized, retain the definition and prove disabled/inactive with PID `0`. Reset only the exited validator's failed state when needed and require zero failed units in either branch;
4. update the runtime-artifact entry to `cleaned_after_validation` or `validated_disabled_retained` according to the actual branch, close this phase in the checkpoint, and append its audit boundary. Do not describe retention as deletion or cancel a separately requested cleanup. The tracked inventory points to the secure result artifact for later transport receipts instead of embedding a volatile `thread_post: pending` object;
5. synchronize the validator script, inventory and checkpoint through the canonical auto-versioning path; require scoped Git clean, the auto-versioning service in its authorized expected state, and local `HEAD == origin/main`;
6. send one REPORT-INFRA embed with content empty and evidence that includes runtime, cleanup and Git readbacks;
7. post one binary-first thread result: `Sim, VPS concluída` only on full pass, otherwise `Não, <first failing gate>`;
8. persist REPORT/thread transport receipts and final state atomically in the secure result artifact without creating a new repository write after the Git gate. If inventory policy requires duplicating those receipts, perform a final readback reconciliation and canonical sync before marking the inventory entry completed; never leave a completed entry with a nested transport status of `pending`.

Do not publish the final green REPORT before the one-shot unit's authorized closure branch is validated and the canonical Git gate passes; disabled/inactive retention is valid only when no separately requested deletion remains pending. If cleanup or Git synchronization fails, keep the result durable, classify the exact governance failure, and report red rather than claiming full closure. If a status request finds `result.overall=true` but the final-status or transport receipt is absent, classify it as **runtime validated, governance pending**: reconcile the unit and failed-state readbacks, finish inventory/audit/Git/REPORT once, and do not rerun already-passed expensive smokes or regression suites unless live drift is observed.

## Canonical Git closure without manual commits

When inventory/checkpoint writes must be committed before the final green report, use the existing auto-commit watcher rather than a manual `git commit`:

1. inspect the watcher's active state, event mask, batch threshold, quiet window and maximum wait; first wait boundedly for the existing batch, polling `git status --porcelain -- <owned-paths>` and then fetching the remote to verify `HEAD == origin/main`. Scope the clean-path gate to this maintenance's files so unrelated concurrent work does not become its cleanup scope;
2. only if the normal batch cannot close and the watcher intervention is within the current authority, stop the persistent watcher cleanly, start the same canonical watcher temporarily with a one-batch threshold, and trigger it with a byte-identical atomic rewrite of an already-authorized dirty file;
3. prove the file hash is unchanged, wait for the scoped paths to become clean, then terminate the temporary watcher;
4. allow the watcher/coprocess lock to release before restarting the persistent service; retry the start in a bounded loop and require `active/running` with a positive PID—`systemctl start` returning zero is insufficient because an inherited `flock` can make the new watcher exit successfully but remain inactive;
5. fetch the remote ref and require the relevant paths clean plus local `HEAD == origin/main` before REPORT-INFRA or the user-facing green result.

If this gate cannot close safely, preserve the result as governance-pending. Do not bypass the canonical path with a manual commit or declare success from local `HEAD` alone.

When the watcher's batching window exceeds a foreground tool's runtime, split observation into bounded calls below that runtime and persist one absolute convergence deadline outside the watched repository. On timeout, read the existing result, owned-path status and watcher state before continuing only the remaining wait; do not replay inventory writes, recreate executors or reset the full batching allowance. Recheck a selective skill mirror after its producer has run, because the source can be committed while the newly synchronized reference starts a later batch.

A scoped clean-path gate can pass before the asynchronous post-commit push finishes. After it passes, fetch and compare `HEAD` with the remote in a bounded convergence window (for example 90 seconds), preserving the concrete exception or ahead/behind evidence. Do not publish a blocked result from a single comparison during that window. If a false Git blocker already fired but runtime checks passed, reconcile the push receipt, reset only the exited validator's failed state, close inventory/checkpoint and send a resolved REPORT in foreground; do not rerun the reboot or already-passed smokes.

## Immutable dispatch checksums and final evidence

1. Maintain an immutable rollback manifest and a separate dispatch snapshot for the frozen verifier, finalizer, unit, pre-state and any continuation helper. Generate both with shell checksum tools and validate each before scheduling.
2. Keep regenerating preflight results, dispatch receipts, post-boot results, transport receipts and append-only executor logs outside the immutable dispatch manifest. A verifier that rewrites its own timestamped result would otherwise invalidate the snapshot without any production drift.
3. Finish source edits, compilation and isolated tests before freezing executable hashes. Any later executable edit requires regenerating the snapshot and rerunning the relevant gates before dispatch; an earlier green snapshot is not evidence for newer code.
4. After the last post-boot and transport write, seal the complete retained evidence with a separate component manifest and top-level seal. Exclude those seal files from their own inputs, use regular-file identity rather than following arbitrary symlinks, and validate the component count plus both checksum layers. Preserve the original dispatch snapshot as historical evidence instead of rewriting it to match a later boot.

## Pre-reboot verification

Before scheduling reboot, require:

- validator `py_compile`;
- `systemd-analyze verify` on the unit;
- isolated module smoke for atomic JSON and inventory mutation using a temporary inventory;
- Discord transport and REPORT-INFRA dry-runs;
- backup SHA256 readback;
- exact package/version readback and no actionable normal APT transaction in either upgrade simulation;
- unit `enabled` readback;
- validator and inventory committed by the canonical auto-versioning path.

## Pitfalls

- **Keep the active-session preflight physically separate from the reboot-capable finalizer.** A command-policy guard can correctly reject execution of a file that contains `systemctl reboot` even when the caller sets `DRY_RUN=1`, because the dangerous primitive is still present in the referenced executable. Do not retry the same wrapper or weaken the guard. Create a pure verifier artifact with no restart/reboot/stop primitive; let it validate hashes, exact versions, unit enabled/inactive state, boot ID, services, launcher and Git state. Hash that verifier and the finalizer independently in the immutable snapshot. Run only the pure verifier from the active gateway, then schedule the frozen finalizer through a detached systemd timer with enough delay for the user-facing acknowledgement to be delivered. Read back both timer `active/waiting` state and its exact target service before ending the foreground turn.
- After the Critical confirmation, finish and hash the pre-state, validator, unit, pure preflight verifier, and reboot finalizer before dispatch. Require the detached executor to read back the actual final handoff from the expected bot in the exact source thread, after the owner's confirmation, and independently prove the originating turn is no longer active; a timer delay or progress message alone does not prove safe shutdown. Bound this wait and withhold reboot if either predicate remains uncertain. Recheck `unit enabled`, protected gateway health, immutable hashes and the pure preflight immediately before dispatch. Read back the timer's `active/waiting` state and exact target service, then end the foreground turn without polling the reboot or enabling raw completion notifications.
- For handoff completion and native continuation, resolve the deployed session store's canonical routing source first. When `state.db::gateway_routing` is primary, read the exact profile/session scope and key from SQLite or the native SessionStore; `sessions/sessions.json` is a legacy mirror and can retain an old `active_turn_token` after the turn ended. Never clear a token or weaken the safety gate to compensate. Fail closed on a missing/ambiguous canonical row, prove that the delivered handoff belongs to the expected bot and source thread, and test stale-mirror/inactive-primary, genuinely active-primary and missing-row cases. Preserve the failed dispatch artifacts and prepare a separately fingerprinted retry under the same authorization.
- A long-running one-shot validator must not unlink its own unit file and call `systemctl daemon-reload` before its final audit, REPORT-INFRA, transport readback, and result persistence finish. Removing or reloading an activating unit can terminate the still-running validator and leave a cached `not-found failed` state after every runtime check has passed. Preferred closure: disable future execution without deleting the active definition; after the validator process exits, use a separate external cleanup unit or foreground reconciliation to remove the file, reload systemd, run `reset-failed`, and prove `LoadState=not-found`, `is-active=inactive`, and zero failed units before marking governance complete.
- Do not reuse dated post-reboot scripts with old thread IDs, legacy Hermes paths, plaintext REPORT formats or stale service lists.
- Never copy a provisional transport state into a completed inventory record. Store receipts in the secure final result, or reconcile the tracked inventory after readback; otherwise a successful post remains falsely `pending` in the canonical inventory.
- Do not post a second asynchronous conclusion if a foreground status check already consumed and replaced the pending validator.
- A validator failure is a real open maintenance phase; preserve its artifact and report the first gate rather than smoothing it into success.
