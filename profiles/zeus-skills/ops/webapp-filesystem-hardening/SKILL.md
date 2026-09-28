---
name: webapp-filesystem-hardening
description: "Use when hardening hosted webapp filesystem permissions."
tags: [webapp, filesystem, permissions, chmod, runcloud, hosting, security, rollback, audit]
related_skills: [vps-maintenance-and-backup-governance, google-drive-agent-automation, hermes-agent-operations]
---

# Web Application Filesystem Hardening

## Purpose

Audit and remediate excessively writable files or directories in a hosted application without breaking PHP-FPM, workers, crons, uploads, caches, static assets, or unrelated applications on the same host. This skill owns the app-level permission transaction; host package maintenance remains in `vps-maintenance-and-backup-governance`.

## Standing rules for Rodolfo

- Before touching a test, staging, or legacy hostname, establish whether it is the operational instance. Never project a result from a test installation onto the production bot or application; name both environments and keep the operational server outside scope unless explicitly authorized.
- Treat a mass permission change as one exact transaction: frozen target set, pre-state backup, restore test, dry-run, canary, batch, post-readback, functional validation, and rollback on any failed acceptance gate.
- Never replace discovered modes with blanket `chmod -R 755/644`. Remove only the unauthorized bit or bits—normally `new_mode = old_mode & ~stat.S_IWOTH`—so executable bits, owner/group write, setgid/sticky bits, ownership, and application-specific exceptions remain intact.
- Keep the application root, its descendants, and the shared parent as separate objects. A parent such as a shared `webapps` directory is a different blast radius and requires its own scope and decision.
- Preserve owner/group exactly unless ownership repair is explicitly part of the authorized scope. Validate the runtime identity first: PHP-FPM pool user, cron/worker user, and actual writable paths must agree.
- For long authorized work, do not narrate internal stages. Report only after full validation or at a real Critical Subset/decision blocker.
- Do not claim the whole application works from HTTP alone. State the validated boundary—web/login/assets/runtime write/crons—and name any untested external integration such as a real Messenger send.
- Treat control-panel names as labels, not topology. A webapp named `*-db` may be a phpMyAdmin frontend rather than a database; distinguish the control-plane webapp, its files/config, the MySQL schema, database users/grants, and current consumers before declaring anything linked, orphaned, removed, or safe to delete.

## Procedure

1. **Identify the real target.** Resolve server, application ID/name, root, public path, hostname, environment role, and operational owner. Reconcile the result with MGS context before deciding that a test copy can affect production.
2. **Audit read-only.** Walk the root without following symlinks. Record each target's relative path, type, mode, uid, gid, size, and `mtime_ns`; record the root separately. Count modes and owners, inspect PHP-FPM/workers/crons, test public and origin HTTP, and note expected writable directories.
3. **Freeze scope.** Serialize a deterministic manifest, hash the logical manifest, and bind the authorization to the root, target count, transition counts, excluded parent, and intended bitwise transformation. Any added/removed path or changed action is new scope.
4. **Capture immediate pre-state.** Immediately before mutation, rescan the exact target set and save current mode/uid/gid/type/size/mtime metadata to a root-only backup outside the application. Verify the backup can be decompressed and exactly reproduces the manifest.
5. **Run a canary.** Pick one representative file whose public response is known. Change only the target bit, confirm byte hash and HTTP behavior, then restore its exact original mode before the batch.
6. **Apply transactionally.** Validate every path before changing it; do not follow symlinks. Apply files first, directories deepest-first, and the app root last. On any exception—including a post-change acceptance failure—restore every saved mode and verify the original writable set before exiting.
7. **Handle live-runtime drift correctly.** If size/mtime validation fails, roll back first. Observe the original application read-only for a bounded window and identify the exact volatile path. Permit only proven runtime volatility, normally a directory `mtime` with stable type and size; keep every other path fail-closed. Never dismiss broad timestamp or content drift as “cache.”
8. **Validate independently.** Require zero unauthorized writable entries; exact final mode/owner counts; owner write/create/read/delete in an expected cache/upload path; public and origin HTTP; login and representative assets; runtime users; cron/worker executions after the change; zero new 5xx and permission errors; and no sentinel residue or service restart unless separately authorized.
9. **Close the record.** Preserve receipt, final validation, backup hash/path, rollback evidence, scope hash, limitations, and parent risk. Update the canonical Sheet through the Service Account with canary/readback, write the closure report, update checkpoint/inventory/audit, publish one REPORT-INFRA, and read back its exact message.

## Missing or moved application

If a previously inventoried root is absent, stop before recreating, reinstalling, or marking it compromised. Reconcile current control-panel/API state, audit log, infrastructure inventory, REPORT-INFRA, Git where relevant, and prior sessions. With no attributable source, report a **concurrent change not yet attributed**, not an anomaly. Ask whether the app was retired or moved only after recoverable sources are exhausted.

Before closing the finding as “application removed,” determine whether the missing target was only an administrative frontend and whether its data plane remains. For phpMyAdmin or database-named webapps, map the current control-panel object, filesystem/config, schema, database user/grants, consumers, network exposure, activity, and backups as separate layers. Control-plane metadata can be stale; live MySQL users/grants and application configuration win for actual dependency state. Do not delete an apparently orphaned schema from naming or a short connection sample—inventory its size and sensitivity, confirm with the owner, then require a protected backup plus isolated restore test before any destructive decision.

## Deep implementation guide

- Load `references/transactional-world-writable-remediation.md` for manifest fields, mode-transition checks, rollback invariants, runtime-volatility handling, and the final validation matrix.
- Load `references/control-plane-database-dependency-mapping.md` when a missing phpMyAdmin/database-named webapp may leave a schema, stale control-plane records, or an ambiguous application dependency.

## Executive response shape

Lead with the binary outcome, then keep six short items:

1. target/environment;
2. exact before → after count;
3. runtime and HTTP/crons validation;
4. backup/rollback state;
5. explicitly untested integrations or residual parent risk;
6. next target or the exact blocker/question.
