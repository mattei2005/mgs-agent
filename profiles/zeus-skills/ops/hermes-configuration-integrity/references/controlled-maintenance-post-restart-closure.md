# Controlled Hermes/VPS Maintenance — Post-Restart Closure

Use after a detached safe finalizer has activated a frozen Hermes target and the remaining work is independent validation, durable closure, and one final REPORT-INFRA. Substitute IDs, SHAs, PIDs, expected test totals, and markers from the current authorized maintenance record.

## Required inputs

- Frozen target SHA and expected `origin/main` relationship.
- Canonical runtime patch path, SHA-256, and expected path count.
- Previous gateway PIDs.
- Finalizer reason, unit, log, order, and authorization source.
- Inventory and checkpoint IDs.
- Expected guard/regression totals and one-shot markers.

Do not infer missing values; recover them from audit, inventory, checkpoint, and the authorized task.

## 1. Prove finalizer completion

1. Inspect a bounded tail window of `logs/events-audit.jsonl`; derive the tail line range first rather than loading a multi-megabyte JSONL file broadly.
2. Locate `prepared`, `scheduled`, `started`, one READY event per agent, and `finished` for the exact reason.
3. Open only the named finalizer log. Require READY in the requested sequential order, systemd+Discord readiness per agent, and terminal `DONE`.
4. If `DONE` is absent, inspect the named transient systemd unit. Wait only while it is still running. Do not schedule or perform a second restart merely because the validator arrived early.

### Early user check-in while validation is still running

If the user asks whether the update succeeded before the external validator finishes:

1. Verify the finalizer and live gateways first.
2. Inspect the existing validator job/session rather than launching duplicate guard, regression, or smoke suites concurrently.
3. Report the narrow truth: activation/reconnection passed, but final closure is still running.
4. Wait for the existing validator's terminal result, then issue one consolidated report. Do not call the maintenance complete from READY markers alone.

## 2. Revalidate gateways independently

For every gateway read `ActiveState`, `SubState`, `MainPID`, `ExecMainStatus`, `NRestarts`, and start time. Require:

- `active/running`;
- `MainPID` differs from the recorded pre-restart PID;
- `ExecMainStatus=0`;
- no restart loop;
- an agent-log Discord connection marker later than that gateway's restart/start time.

Finalizer READY is evidence, but it does not replace current live readback. Service names and `hermes --version` banner text are not sufficient runtime provenance: the banner can show a fetched `upstream <sha>` while the wrapper/process still runs an older checkout. Triangulate literal wrapper `readlink`, resolved entrypoint and shebang, service PID command line, active repository `HEAD`, editable import path, and installed metadata version. Any disagreement blocks closure until reconciled.

## 3. Validate the VPS without widening scope

Check the exact package/version requested, `dpkg --audit`, snap refresh status, and `/var/run/reboot-required`. Report reboot/autoremove truthfully. Do not run autoremove, reboot, package upgrades, or cleanup unless separately authorized.

## 4. Validate the frozen target and local patch

Treat Git as authoritative. The cutover-blocking snapshot must contain only runtime-critical immutable inputs: target code/patch, launchers, managed profile config/SOUL, readiness/finalizer helpers, and the exact execution scripts. Back up profile `auth.json`, but do not use its exact bytes as a cutover blocker because OAuth refresh can legitimately rewrite it during an active conversation; instead require existence, parseability, permission sanity, and live `auth status` in preflight/acceptance. Do not include self-improvement-managed skills, reports, inventory, checkpoints, audit logs, or notifier state in that blocking hash set: authorized closure forks can legitimately update those mutable artifacts after preparation and cause a false pre-cutover drift. Fingerprint mutable artifacts separately for reconciliation and REPORT-INFRA, then read them back after closure; their legitimate mutation is not target-runtime drift.

- exact `HEAD`;
- local `origin/main` and `HEAD..origin/main` count;
- ancestry relationship;
- exact patch SHA-256;
- `git apply --reverse --check`;
- exact live patch path set.

A version banner may identify the release correctly while update-status text is cache-shaped. If it conflicts with the graph, report release/version and Git behind count separately. An upstream commit arriving after freeze is not target drift.

### Path-set pitfall: tracked diff can undercount

`git diff --name-only HEAD` excludes untracked files. A 39-path patch can therefore appear as 33 tracked modifications when six patch files are new/untracked. Validate the set instead:

1. Derive unique patch paths from `+++ b/<path>` headers or an equivalent parser.
2. Collect live changed paths with `git status --porcelain=v1 -uall`.
3. Normalize rename syntax if present.
4. Require equal sets, zero missing paths, and zero extra paths.

Never lower the expected patch count based only on tracked diff output.

## 5. Acceptance tests

Run the canonical patch guard and post-upstream regression pack with the live venv and required `BASE`, `REPO`, and `PYBIN`. Require command rc=0 and the operation's expected totals. Keep finite jobs in foreground in Discord operations. The safe-restart exception may run detached only through the canonical finalizer/controller; never attach raw process completion notifications. If Rodolfo explicitly asks to be notified after the detached restart, use a bounded, purpose-built one-shot notifier that reads a terminal `final-status.json` plus live state and emits only a concise executive success/failure message.

## 6. Config checks and exact one-shot smokes

Select profiles with `HERMES_HOME`:

- root: `/root/.hermes`;
- agent: `/root/.hermes/profiles/<agent>`.

For each profile:

1. Validate the exact candidate CLI invocation during preflight with `hermes --help`; do not add legacy or undocumented quiet flags. In Hermes v0.19.0, `-q` is not accepted, so the validated one-shot form is `hermes -z "..."` plus the profile selector where applicable.
2. `hermes config check` must return rc=0.
3. Run `hermes -z` with a profile-specific exact marker.
4. Require both rc=0 and marker presence. Complete stdout with nonzero teardown is not a pass when the closure contract requires rc=0.

Summarize only rc and marker presence; never print auth material.

## 7. Preservation checks

- Compare live and versioned config/SOUL byte-for-byte for every managed agent.
- Verify each required bundled capability by checking its `SKILL.md` in root and agent homes.
- For Atena/Ares MGS Google Workspace compatibility skills, verify the canonical Service Account route remains documented and the retired compatibility entry point still fails closed with its expected rc. Do not treat this deliberate fail-closed rc as a generic smoke failure.

## 8. Durable closure and REPORT-INFRA order

Only after all gates pass:

1. Atomically update inventory to `activated_validated` with finalizer unit/log/order, old and new PIDs, result, and timestamp.
2. Append activation audit and validate both writes by readback.
3. Complete the checkpoint through `mgs-knowledge-control.py checkpoint-upsert`; run knowledge validation and read back the exact checkpoint.
4. Send exactly one final REPORT-INFRA Embed through the canonical helper: empty `content`, no mentions, no thread, and no text duplicate.
5. Parse the returned message ID and perform Discord GET readback. Require destination channel, exact message ID, empty content, one embed, zero mentions, and required fields.
6. Atomically store message ID/readback in inventory and append a dedicated report-readback audit event.
7. Perform final readback of inventory, checkpoint, Git target/behind count, gateways, and VPS package/reboot state.
8. Reconcile writes produced during closure. A validator, inventory discovery pass, or self-improvement hook can create new mirror/inventory diffs after an earlier auto-commit. Compare local HEAD with its remote, identify the exact residual paths, and classify them explicitly:
   - operational drift or missing artifact: block closure;
   - validated documentation/inventory housekeeping under an auto-versioning policy: report as pending automatic consolidation, not as a runtime failure.
9. Confirm the one-shot validator has terminated or been removed from the active schedule before saying no background work remains. Never claim a fully clean repository from an earlier status snapshot if a closure fork could still write afterward.

10. Require every terminal controller path to write a machine-readable `final-status.json`: `activated_validated`, `activation_failed_rolled_back`, `activation_failed_rollback_incomplete`, or `activated_validated_closure_pending`. A notifier must not infer completion from partial logs.
11. On rollback, atomically restore inventory provenance to the runtime actually active after rollback: checkout path, `HEAD`, metadata version, literal wrapper target, gateway state, rollback result, and timestamp. Preserve the target trial results in a separate field; never leave target paths labeled active after a successful rollback.
12. A fully green independent stage after rollback proves release readiness, not production activation. Keep checkpoint/inventory state explicitly `not_completed` until a later authorized cutover passes live validation.
13. When a bounded notifier is explicitly requested, inventory and report its script/job ID, set a finite repeat count, verify that it reads final status and live state rather than raw logs, and confirm the job is completed/disabled or removed after delivery so no stale recurring notifier remains.

If any gate fails, persist the real failed stage and distinguish a validator-invocation defect from a target-runtime defect. Send one failure REPORT-INFRA and state containment. Execute only the reversible pointer/runtime rollback that was explicitly authorized in the maintenance contract; never improvise a destructive rollback. If the bad gate was only an invalid CLI invocation, validate the corrected exact command against the independent stage without restarting, but require fresh authorization before another production cutover.

## Executive output

Report only VPS state; Hermes version/target/behind count; patch count/reverse-check; guard/regression totals; config/smoke totals; gateway order and old→new PIDs; inventory/checkpoint closure; final REPORT-INFRA message ID/readback; and any bounded residuals. Separate frozen-out upstream commits, development-only dependency advisories, and pending auto-versioning housekeeping from runtime blockers. Do not include raw traces or credentials.
