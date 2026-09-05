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

Do not call `packages updated; reboot pending` complete maintenance.

## Package gate before reboot

Require literal candidate versions, exact authorized package count, zero new packages/removals/holds, `dpkg --audit` clean, zero remaining normal APT candidates, expected service-only restarts, gateway PIDs unchanged, and no priority 0..3 journal errors since the maintenance boundary. Preserve the complete install log under the secure maintenance set.

## Durable validator design

Create a self-contained one-shot systemd unit before reboot:

- `After=network-online.target` plus the named gateway/vendor services;
- `Type=oneshot`, bounded timeout and logs under the secure maintenance set;
- enabled for the next multi-user boot;
- no dependency on the active conversation surviving;
- one clean user conclusion and one canonical REPORT-INFRA only;
- disable/remove the one-shot unit after recording the result so it cannot rerun on later boots.

Use the canonical Discord transport `/root/mgs-agent/scripts/discord-bot-post.py` and REPORT helper `/root/mgs-agent/scripts/send-report-infra-embed.sh`; never parse, print or embed the bot token in the validator.

## Post-boot acceptance gates

The validator must prove all of the following from live state:

1. boot ID changed;
2. running kernel equals the frozen expected kernel and `/var/run/reboot-required` is absent;
3. exact package versions match;
4. fresh APT metadata, zero normal candidates, zero holds and clean `dpkg --audit`;
5. `/tmp` is `root:root 1777`;
6. zero failed units and zero priority 0..3 boot journal entries;
7. `needrestart` current/expected kernel agree;
8. gateways, Monarx/security agent, QEMU, cron and auto-commit are active with positive PIDs;
9. gateway readiness includes a fresh Discord-connected marker after each frozen pre-reboot log offset—service `active` alone is insufficient;
10. Hermes launcher and local HEAD remain exactly unchanged when application work is deferred.

Report inaccessible ESM Apps updates as a separate residual; do not fold them into the zero normal APT-candidate gate or silently attach Ubuntu Pro.

## Governance closure

Write an atomic compact result JSON first, then close in this order:

1. append the validation audit readback;
2. update the existing VPS/vendor inventory records and close or fail the checkpoint;
3. disable/remove the one-shot unit, daemon-reload, and verify the unit is absent/inactive;
4. update the validator runtime-artifact entry to `cleaned_after_validation` and append a cleanup audit boundary;
5. send one REPORT-INFRA embed with content empty and evidence that includes the cleanup readback;
6. post one binary-first thread result: `Sim, VPS concluída` only on full pass, otherwise `Não, <first failing gate>`;
7. persist REPORT/thread transport receipts in the result artifact.

Do not publish the final green REPORT before the one-shot unit is actually cleaned. If cleanup fails, keep the result durable, classify `unit_cleanup` as a governance failure, and report red rather than claiming full closure.

## Pre-reboot verification

Before scheduling reboot, require:

- validator `py_compile`;
- `systemd-analyze verify` on the unit;
- isolated module smoke for atomic JSON and inventory mutation using a temporary inventory;
- Discord transport and REPORT-INFRA dry-runs;
- backup SHA256 readback;
- exact package/version readback and zero normal APT candidates;
- unit `enabled` readback;
- validator and inventory committed by the canonical auto-versioning path.

## Pitfalls

- **Keep the active-session preflight physically separate from the reboot-capable finalizer.** A command-policy guard can correctly reject execution of a file that contains `systemctl reboot` even when the caller sets `DRY_RUN=1`, because the dangerous primitive is still present in the referenced executable. Do not retry the same wrapper or weaken the guard. Create a pure verifier artifact with no restart/reboot/stop primitive; let it validate hashes, exact versions, unit enabled/inactive state, boot ID, services, launcher and Git state. Hash that verifier and the finalizer independently in the immutable snapshot. Run only the pure verifier from the active gateway, then schedule the frozen finalizer through a detached systemd timer with enough delay for the user-facing acknowledgement to be delivered. Read back both timer `active/waiting` state and its exact target service before ending the foreground turn.
- After the Critical confirmation, finish and hash the pre-state, validator, unit, pure preflight verifier, and reboot finalizer before dispatch. Use a detached, silent finalizer with a short acknowledgement window plus hard guards (`unit enabled`, protected gateway active, hashes/readback still valid); deliver the user-facing “reboot dispatched” message before the finalizer calls `systemctl reboot`. Never use completion notifications or poll that reboot from the active Discord tool chain.
- A long-running one-shot validator must not unlink its own unit file and call `systemctl daemon-reload` before its final audit, REPORT-INFRA, transport readback, and result persistence finish. Removing or reloading an activating unit can terminate the still-running validator and leave a cached `not-found failed` state after every runtime check has passed. Preferred closure: disable future execution without deleting the active definition; after the validator process exits, use a separate external cleanup unit or foreground reconciliation to remove the file, reload systemd, run `reset-failed`, and prove `LoadState=not-found`, `is-active=inactive`, and zero failed units before marking governance complete.
- Do not reuse dated post-reboot scripts with old thread IDs, legacy Hermes paths, plaintext REPORT formats or stale service lists.
- Do not post a second asynchronous conclusion if a foreground status check already consumed and replaced the pending validator.
- A validator failure is a real open maintenance phase; preserve its artifact and report the first gate rather than smoothing it into success.
