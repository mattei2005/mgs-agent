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
- for a combined maintenance recommendation before authorizing update, restart, retention change, or deletion.

## Progressive routing

1. For Git/release delta, local patches, editable-package version drift, or dry-run portability, load `references/git-update-delta-and-patch-portability.md`.
2. For backup inventory, retention-scope gaps, archive redundancy, or cleanup classification, load `references/backup-retention-scope-and-redundancy.md`.
3. If execution is authorized, route the actual update/restart to `hermes-agent-operations` and destructive housekeeping/reporting to the applicable MGS operational skill. Do not duplicate those deployment procedures here.

## Audit workflow

1. **Recover the real pendency.** Use current runtime first; use checkpoints/audit/inventory and prior sessions only to explain what was pending. A historical package list never overrides the current APT graph, running kernel, or live service state.
2. **Freeze a coherent observation.** Refresh package metadata and Git refs when allowed, then capture timestamp, running kernel, reboot marker, update candidates, Git SHAs/tag, services, disk, and backup roots. Do not calculate against refs while a fetch is still changing them.
3. **Separate update classes.** Report standard OS/security updates, third-party repositories, inaccessible subscription/ESM fixes, language/package-manager updates, Snaps, and Git application updates independently. Do not call every available package a security update.
4. **Distinguish stable release from moving main.** Name the latest public tag, installed checkout, and current upstream SHA. Count pending commits from the installed checkout and untagged commits since the tag separately.
5. **Measure customization risk.** Count tracked and untracked local files, intersect them with upstream-changed paths, and run a clean-target apply check. Textual overlap is not an actual conflict; a failed apply check names the real port blockers.
6. **Inventory backup storage by operational set.** Count bytes/files/dates/errors at first-level backup sets and separately include update reports, staging/workdirs, hidden secure roots, system-managed backups, and protected archives.
7. **Audit the cleanup implementation, not just its cron.** Read its scan roots, filename patterns, keep-latest logic, and retention. A green dry-run proves only the policy it implements; it does not prove that legacy names or backup directories are covered.
8. **Classify before proposing deletion.** Use exactly three classes: eligible under current policy; eligible only after an explicit retention/policy change; protected or containing unique data. Never blend them into one reclaim number.
9. **Validate retained recovery paths.** Before naming an archive deletable, validate the archives that remain and prove that a supposedly redundant snapshot has no unique state required by the canonical archive.
10. **Quantify the decision.** Calculate exact recoverable bytes and projected filesystem usage; after any authorized cleanup, verify path absence and measure actual reclaimed space.
11. **Report conclusion first.** State whether reboot is required, what can update routinely, what requires a controlled window, exact high-confidence cleanup candidates, protected classes, and the residual governance gap.

## Safety and authorization

- Read-only discovery, index refresh, `git fetch`, archive listing, hash verification, and temporary apply checks do not authorize install, restart, retention changes, or deletion.
- Update, restart, credentials, destructive cleanup, and policy changes follow `AGENT.md` and the Critical Subset confirmation rules.
- Never inspect or print secret contents while sizing or hashing backups. Paths may be named only when that does not expose a credential value.
- Never run `apt autoremove`, delete system-managed `/var/backups`, remove a registered Git worktree with raw `rm`, or shorten backup retention as an incidental part of another cleanup.
- Preserve patches, manifests, hashes, final reports, and compact logs when deleting only bulky staging clones or redundant archives.
- For retired-agent cleanup, interpret broad language at the **dedicated operational-set boundary**: remove dedicated archive/backup roots only; preserve references embedded in mixed backups, Git, audit logs, and shared evidence unless the user separately names that wider purge scope.
- If the owner explicitly chooses to discard a protected snapshot that contains unique state, disclose the unique classes/bytes and require the Critical Subset double-confirmation with exact roots, file count, bytes, irreversible loss, and what historical evidence will remain.
- Before destructive execution, freeze the authorized target list and verify every target exists, is under an allowed root, is neither a symlink nor a mount, and still matches the confirmed file/byte totals. Use exact paths rather than wildcard deletion, record an audit start boundary before removing anything, and record a success/partial-failure boundary afterward.
- Any resulting script/config/data/skill change requires the applicable inventory, audit, validation, and REPORT-INFRA closure.

## Executive reporting shape

Use two sections:

1. **Updates:** closed pendencies, current candidates, service/reboot health, Git release/main distinction, local port risk, recommendation.
2. **Backups:** total by root/set, exact high-confidence deletion paths and bytes, projected disk result, protected/conditional classes, housekeeping coverage gap.

Do not dump thousands of child paths into Discord. Count all files, but list deletion candidates at the exact file or operational-set boundary that would be authorized.

## Completion checklist

- [ ] Current package graph and security classification captured
- [ ] Running kernel and reboot marker agree
- [ ] Failed units and target services checked
- [ ] Latest tag, installed SHA, upstream SHA, and observation time frozen
- [ ] Tracked/untracked local surface and real apply blockers measured
- [ ] Backup roots and staging/report/archive classes counted without double counting
- [ ] Cleanup script scope compared with actual storage
- [ ] Retained archives validated before redundant archive is proposed
- [ ] Retired-agent snapshot checked for unique content before deletion
- [ ] Current-policy, policy-change, and protected queues separated
- [ ] Recoverable bytes and projected disk calculated
- [ ] No install, restart, policy change, or deletion occurred without authorization
