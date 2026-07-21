---
name: hermes-configuration-integrity
description: "Audit Hermes configuration drift and preservation across profiles after updates, migrations, reloads, cron validation reports, or suspected personalization loss. Use for read-only verification before proposing any repair."
tags: [hermes, configuration, drift, profiles, mirrors, updates, audit, mgs]
---

# Hermes Configuration Integrity

## Purpose

Prove whether Hermes profile customizations changed, distinguish intentional migration from later drift, and report the result without exposing credentials or confusing a successful cron response with an anomaly.

## Triggers

Load this skill when:

- a post-update or post-reload cron result appears in an operational thread;
- the user asks whether personalizations/configuration were altered;
- live profile config may differ from its versioned mirror or validated candidate;
- a schema migration, model change, compression change, or deprecated-key cleanup occurred;
- a green patch guard must be separated from actual config preservation;
- a controlled Hermes port must prove that every local runtime path was retained or explicitly absorbed upstream before live staging;
- a detached Hermes/VPS maintenance finalizer completed and needs post-restart gateway, patch, smoke, inventory, checkpoint, and REPORT-INFRA closure.

## Audit workflow

1. **Classify the message.** Determine whether it is a failure alert, a successful one-shot completion, or a recurring watchdog result. Inspect the job registry and original thread evidence; do not infer danger from the generic `Cronjob Response` heading.
2. **Freeze the comparison set.** Identify live configs, versioned mirrors, the validated post-change candidates, and the pre-change backup. Do not compare only against upstream defaults.
3. **Compare complete files first.** Use SHA-256/byte equality and parsed-YAML equality. Full-file equality is the preservation proof; selected key reads are explanatory evidence only.
4. **Diff pre-change versus current safely.** Read archived configs in memory, flatten leaf paths, redact credential-like paths, and enumerate only actual changed keys. Separate intentional migration changes from later drift.
5. **Resolve runtime values correctly.** Select each profile with its actual `HERMES_HOME`; do not assume `HERMES_PROFILE` changes the config resolver. Run `hermes config get <key> --json` for safe, non-secret keys.
6. **Verify the customization surface.** Check the canonical patch with reverse-apply validation and run the current MGS guard when authorized. A green patch guard does not replace config-file equality.
7. **Interpret update prechecks by evidence, not process exit alone.** A diagnostic `PRECHECK_ONLY` wrapper may return `rc=0` after collecting evidence even when its internal patch/local-diff checks recorded `DRIFT`. Require clean `pre-upstream-patch-check.txt`, `pre-local-diff-upstream-check.txt`, and read-only invariants before calling the update gate green. Report `diagnóstico concluído, update bloqueado` when collection succeeded but drift remains; never promote readiness from `DONE precheck only` or the existence of `final-report.md` alone.
7a. **Audit port preservation path-by-path.** Freeze one target SHA; manifest tracked, staged, and untracked files; require a verified rollback stash; and classify every path absent from the final patch as explicitly upstream-equivalent with commit and test evidence. Prove the final artifact in a second clean checkout with apply/reverse checks, path-set equality, byte identity, and a `module.__file__` probe from the intended cwd. Follow `references/controlled-update-port-preservation.md`.
8. **Verify live services.** Confirm `active/running`, `ExecMainStatus=0`, and restart counters. Use current runtime evidence, not only the old cron summary.
8a. **Close detached maintenance only after independent post-restart proof.** Reconcile the exact finalizer reason and terminal `DONE`; require changed PIDs plus fresh Discord markers; validate frozen Git target, full tracked+untracked patch path-set equality, guards, per-profile rc=0 exact-marker smokes, mirrors, capabilities, and fail-closed routes. Then atomically close inventory/checkpoint, send one final Embed, GET-readback the Discord message, and store its ID. Follow `references/controlled-maintenance-post-restart-closure.md`.
9. **Check attribution before calling drift anomalous.** Reconcile audit log → infrastructure inventory → REPORT-INFRA → Git → session/thread history.
10. **Leave no test residue.** Recheck Git status after guards. Restore any deterministic test-cache marker without touching production config; do not report a clean audit while the verification itself left drift.
11. **Verify procedural persistence when asked.** If the user asks whether a lesson was saved for future checks, read back both the live skill and its versioned MGS mirror. State whether the rule was newly written in the current task or already existed and was only confirmed. Separately verify any cron, detector, or announcement generator: a rule in a skill does not prove that an independent script-only automation was changed or even consumes that skill.
12. **Report conclusion first.** State: intentional changes, preserved personalizations, later drift status, current health, and one residual risk or unrun gate if applicable.

## Safety and reporting

- Never print config secrets, tokens, cookies, OAuth material, or credential-bearing diffs.
- Read-only verification does not authorize repair, restart, or rollback.
- If a repair is needed, route it through the normal MGS authorization and Critical Subset gates.
- Do not rerun a large regression pack merely to explain a successful cron message when byte identity, resolved config, current guard, and service health already answer the question.
- If the verification causes no durable change, say so explicitly; do not create an unnecessary REPORT-INFRA.

## Supporting reference

- Detailed comparison patterns, redaction rules, profile resolver pitfall, and cleanup checks: `references/post-reload-personalization-audit.md`.
- Frozen-target port preservation, upstream-equivalent retirement, editable-venv import proof, npm 12 review, and rollback-stash validation: `references/controlled-update-port-preservation.md`.
- Detached finalizer verification, tracked+untracked patch set equality, exact rc=0 profile smokes, atomic closure, and single-Embed Discord readback: `references/controlled-maintenance-post-restart-closure.md`.

## Completion checklist

- [ ] Cron message classified correctly
- [ ] Live/candidate/mirror files compared completely
- [ ] Pre-change diff enumerated safely
- [ ] Per-profile resolved values read with correct `HERMES_HOME`
- [ ] Patch/customization guard verified
- [ ] Pre-port paths retained or explicitly proven upstream-equivalent
- [ ] Clean-checkout imports proven from the intended cwd
- [ ] Rollback stash includes and hash-matches tracked plus untracked paths
- [ ] Services checked live
- [ ] Detached finalizer and external validator both reached terminal success; no duplicate validation suite was launched
- [ ] Final REPORT-INFRA message ID and Discord GET readback stored
- [ ] Attribution reconciled before anomaly language
- [ ] Verification residue and post-closure background writes reconciled; any auto-versioning housekeeping labeled separately from runtime drift
- [ ] No configuration or credential changed during the audit
