---
name: vps-maintenance-and-backup-governance
description: "Audit and govern MGS VPS maintenance: OS and third-party updates, Git-based application deltas with local patches, reboot/service readiness, backup-storage inventory, retention gaps, and safe cleanup classification before any destructive action."
tags: [vps, maintenance, updates, apt, git, hermes, backups, retention, disk, audit, mgs]
related_skills: [hermes-agent-operations, hermes-configuration-integrity, log-monitor-discord-alert]
---

# VPS Maintenance and Backup Governance

## Purpose

Produce a grounded maintenance decision for the MGS VPS without confusing package-index refreshes, untagged Git development, local customization drift, backup integrity, backup redundancy, or cleanup-policy eligibility. This skill governs the **audit and decision boundary**; actual Hermes deployment/restart still follows `hermes-agent-operations`, and monitor implementation still follows `log-monitor-discord-alert`.

## Triggers

Load this skill when Rodolfo asks:

- what remains to update on the VPS, Hermes, or adjacent runtime components;
- whether a previous kernel/reboot/update pendency is closed;
- for every backup class, disk usage, retention status, or deletion candidates;
- why housekeeping reports no candidates while disk usage remains high;
- whether an old pre-update archive, staging checkout, worktree, or retired-agent snapshot is redundant;
- whether public SSH can be restricted without breaking legitimate access or outbound MGS workloads;
- for a combined maintenance recommendation before authorizing update, restart, retention change, deletion, or SSH hardening.

## Progressive routing

1. For Git/release delta, local patches, editable-package version drift, or dry-run portability, load `references/git-update-delta-and-patch-portability.md`.
2. For backup inventory, retention-scope gaps, archive redundancy, or cleanup classification, load `references/backup-retention-scope-and-redundancy.md`.
3. For an authorized exact APT/vendor package plus npm/Corepack maintenance window, required reboot closure, or confirmed retirement of an invalid quarantined backup, load `references/controlled-package-and-node-tooling-update.md` before touching `/usr` or deleting the quarantine; it defines literal candidate versions, rollback, gate separation, durable post-boot validation, exact-target cleanup, and inventory closure.
4. For inventory generators that assemble large JSON, atomic-write design, `jq` argument-size failures, or Git auto-push races involving temporary artifacts, load `references/inventory-generation-and-autopush-safety.md`.
5. For public SSH exposure, missing key-based access, dynamic administrator IPs, provider firewalls, or lockout-safe sequencing, load `references/lockout-safe-ssh-hardening.md` before recommending any authentication or firewall mutation.
6. Route Hermes deployment/restart to `hermes-agent-operations` and monitor implementation to `log-monitor-discord-alert`. Do not duplicate those procedures here.
7. For an authorized host reboot that must outlive the active gateway turn, load `references/durable-post-reboot-validator-pattern.md`; it defines the pre-state freeze, one-shot systemd validator, fresh Discord-readiness evidence, governance closure, transport dry-runs, and binary-first completion contract.
8. When an audit surfaces Ubuntu Pro, ESM Apps/Infra, Livepatch, a device-code attach flow, or the boundary between subscription attachment and package installation, load `references/ubuntu-pro-esm-classification-and-owner-consent.md`; it defines coverage classification, supervised PTY attachment, local readback, separate authorization gates, and post-install closure.
9. For exact destructive target manifests followed by an exhaustive backup/orphan scan, load `references/full-vps-cleanup-inventory.md`; it defines inode-aware reclaim estimates, protected browser/Drive-backed state, tracked-file Git range closure, moving-upstream scope separation, per-filesystem coverage, post-deletion acceptance, and fail-closed housekeeping dry-runs.

## Audit workflow

1. **Recover the real pendency.** Use current runtime first; use checkpoints/audit/inventory and prior sessions only to explain what was pending. A historical package list never overrides the current APT graph, running kernel, or live service state. A scheduled or detached update is still pending until the finalizer log/result, canonical launcher, target service start times, and required report/readback agree; reconcile those sources before repeating any earlier success claim.
2. **Freeze a coherent observation.** Refresh package metadata and Git refs when allowed, then capture timestamp, running kernel, reboot marker, update candidates, Git SHAs/tag, services, disk, and backup roots. Do not calculate against refs while a fetch is still changing them.
3. **Separate update classes.** Report standard OS/security updates, third-party repositories, inaccessible subscription/ESM fixes, language/package-manager updates, Snaps, and Git application updates independently. Do not call every available package a security update.
4. **Distinguish stable release from moving main.** Name the latest public tag, installed checkout, and current upstream SHA. Count pending commits from the installed checkout and untagged commits since the tag separately.
5. **Measure customization risk.** Count tracked and untracked local files, intersect them with upstream-changed paths, and run a clean-target apply check. Textual overlap is not an actual conflict; a failed apply check names the real port blockers.
6. **Inventory backup storage by operational set.** Count bytes/files/dates/errors at first-level backup sets and separately include update reports, staging/workdirs, hidden secure roots, system-managed backups, and protected archives.
7. **Audit the cleanup implementation, not just its cron.** Read its scan roots, filename patterns, keep-latest logic, and retention. A green dry-run proves only the policy it implements; it does not prove that legacy names or backup directories are covered.
8. **Classify before proposing deletion.** Use exactly three classes: eligible under current policy; eligible only after an explicit retention/policy change; protected or containing unique data. Never blend them into one reclaim number.
9. **Validate retained recovery paths.** Before naming an archive deletable, validate the archives that remain and prove that a supposedly redundant snapshot has no unique state required by the canonical archive.
10. **Quantify the decision without hardlink inflation.** Report both the naive allocated sum and an inode-aware reclaim estimate that credits file blocks only when every hardlink is inside the target set. Keep overlapping review roots non-additive. After any authorized cleanup, verify path absence and treat the measured `df` free-space delta as the authoritative observed result.
11. **Cover every persistent filesystem explicitly.** Scan `/`, `/boot`, and `/boot/efi` separately whenever they are different devices; prune pseudo-filesystems and mount crossings, record errors per filesystem, and never infer whole-VPS coverage from the root filesystem alone.
12. **Report conclusion first.** State whether reboot is required, what can update routinely, what requires a controlled window, exact high-confidence cleanup candidates, protected classes, and the residual governance gap.

## Phase boundary: VPS first, application runtime later

When Rodolfo says **“VPS primeiro; Hermes depois”**, treat that as a hard operational boundary, not merely an ordering hint:

1. Complete the VPS phase through package validation, required reboot, and post-boot readback before beginning any Hermes port or deployment work.
2. Before that closure, Hermes activity is limited to proving the currently active launcher/version is unchanged. Do not create or promote a port patch, install a candidate venv, run application builds/smokes, or modify Hermes deployment/guard scripts.
3. Distinguish status precisely:
   - `packages updated; reboot pending` = VPS maintenance is **not complete**;
   - `new boot validated; reboot marker cleared; services healthy` = VPS phase complete.
4. If the user asks “deu certo ou não?”, answer the binary state first in one sentence, then name the single pending gate. Do not bury the answer inside a long Hermes/update narrative.
5. A later request to defer Hermes immediately freezes any staged Hermes artifact as inactive evidence only. Verify the canonical launcher still points to the old runtime and do not activate, clean up, or extend the staged port without a new scope.

## Safety and authorization

- Read-only discovery, index refresh, `git fetch`, archive listing, hash verification, and temporary apply checks do not authorize install, restart, retention changes, or deletion.
- Update, restart, credentials, destructive cleanup, and policy changes follow `AGENT.md` and the Critical Subset confirmation rules.
- Never inspect or print secret contents while sizing or hashing backups. Paths may be named only when that does not expose a credential value.
- Never run `apt autoremove`, delete system-managed `/var/backups`, remove a registered Git worktree with raw `rm`, or shorten backup retention as an incidental part of another cleanup.
- Preserve patches, manifests, hashes, final reports, and compact logs when deleting only bulky staging clones or redundant archives.
- Inventory/render generators running inside an auto-versioned repository must create component work directories outside the Git tree (prefer `/run` for short-lived root jobs, otherwise `/tmp`) and place only the final validated file in the repository via atomic rename. Large JSON components must be passed to `jq` through files such as `--slurpfile`, not serialized into many `--argjson` command-line arguments where `ARG_MAX` can fail.
- After a generator failure, reconcile Git/auto-push before moving or removing temporary artifacts. A concurrent auto-commit can make a formerly untracked temp directory tracked; restore/reconcile first, preserve a hash-validated copy, and apply Critical Subset confirmation before deleting tracked artifacts.
- For retired-agent cleanup, interpret broad language at the **dedicated operational-set boundary**: remove dedicated archive/backup roots only; preserve references embedded in mixed backups, Git, audit logs, and shared evidence unless the user separately names that wider purge scope.
- If the owner explicitly chooses to discard a protected snapshot that contains unique state, disclose the unique classes/bytes and require the Critical Subset double-confirmation with exact roots, file count, bytes, irreversible loss, and what historical evidence will remain.
- Before destructive execution, freeze the authorized target list and verify every target exists, is under an allowed root, has zero process references, is not a mount, and still matches the confirmed type/fingerprint/file/byte totals. A tree target must not be a symlink; an explicitly listed launcher may use a separate `delete_symlink` action after expected-target readback. Use exact paths rather than wildcard deletion, bind authorization to the target-set hash, record an audit start boundary before removing anything, and record a success/partial-failure boundary afterward. Any newly discovered path belongs to a new scope and requires a new manifest and confirmation.
- For a separately authorized deferred-service restart, freeze active sessions and protected service PIDs first. Acceptance requires the named service active, gateway PIDs unchanged, zero `NEEDRESTART-SVC` rows, and no new warning/critical logs. Remaining `NEEDRESTART-SESS` rows normally clear on logout/reconnection and do not justify forced logout, user-manager restart, or reboot.
- Any resulting script/config/data/skill change requires the applicable inventory, audit, validation, and REPORT-INFRA closure.

## Executive reporting shape

Use two sections:

1. **Updates:** closed pendencies, current candidates, service/reboot health, Git release/main distinction, local port risk, recommendation.
2. **Backups:** total by root/set, exact high-confidence deletion paths and bytes, projected disk result, protected/conditional classes, housekeeping coverage gap.

When Rodolfo asks **only what remained after a cleanup**, answer strictly from a fresh post-cleanup inventory: omit every deleted class/path, avoid before/after narration, and show only current bytes plus whether each residue is removable, conditional, or protected. Keep overlapping roots explicitly non-additive. If he asks which dates remain, summarize current files in date/age ranges with file counts and allocated bytes instead of listing already removed history or every child path.

For residual backup review, distinguish exact duplicates of the live state from historically unique content. A file that duplicates the live state is not individually removable when it belongs to an archive/checksum/restore set whose integrity would be broken. For temporary storage, measure age from the newest descendant in each top-level entry and check live process references before classifying it as abandoned.

A provider-level whole-VPS snapshot may replace overlapping bulky local pre-update archives only after the snapshot is created outside the VPS, provider/account access is read back, and restoration capability is proven. Keep offsite backup as a separate failure domain and retain current local rollback/archives until that gate passes; never substitute a tar of `/` stored on the same VPS and never retire verified recovery paths merely because the snapshot was proposed.

Do not dump thousands of child paths into Discord. Count all files, but list deletion candidates at the exact file or operational-set boundary that would be authorized.

## Completion checklist

- [ ] Current package graph and security classification captured
- [ ] Any scheduled/detached finalizer reconciled against live launcher, services, logs, and report readback
- [ ] Running kernel and reboot marker agree
- [ ] Failed units and target services checked
- [ ] Latest tag, installed SHA, upstream SHA, and observation time frozen
- [ ] Tracked/untracked local surface and real apply blockers measured
- [ ] Backup roots and staging/report/archive classes counted without double counting
- [ ] `/`, `/boot`, and `/boot/efi` scanned separately where device boundaries require it; pseudo-filesystems pruned; errors recorded
- [ ] Cleanup script scope compared with actual storage and dry-run exits zero without mutation
- [ ] Retained archives validated before redundant archive is proposed
- [ ] Retired-agent snapshot checked for unique content before deletion
- [ ] Current-policy, policy-change, and protected queues separated
- [ ] Naive allocated bytes and inode-aware reclaim estimate both reported; overlapping review roots kept non-additive
- [ ] After deletion, exact targets are absent and observed `df` delta is recorded as authoritative
- [ ] No install, restart, policy change, or deletion occurred without authorization
