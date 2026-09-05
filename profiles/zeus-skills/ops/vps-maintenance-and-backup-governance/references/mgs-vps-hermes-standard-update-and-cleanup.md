# MGS Standard — VPS + Hermes Update and Cleanup

## Purpose

This is the canonical contract whenever Rodolfo asks to update, review, verify, or clean the MGS VPS and Hermes in the same initiative. It standardizes execution order, authorization gates, cleanup semantics, and the executive answer so the result does not vary by session.

Use the specific VPS/Hermes references for implementation details; this document owns the combined lifecycle and reporting shape.

## Fixed operating policy

1. **Plan first.** Begin with a live read-only audit and present one concrete plan before any package install, runtime cutover, restart, reboot, or deletion.
2. **Stable release by default.** Compare the active Hermes upstream base with the latest official release tag. Post-release commits on moving `main` are reported separately and are not activated unless Rodolfo explicitly requests a development-main port.
3. **Critical gates stay exact.** Modifying `/usr`, `/etc`, `/boot`, rebooting, or deleting files requires the `AGENT.md` confirmation with exact current→target state. Scope drift, including reduction or volatile-cache drift, invalidates the confirmation.
4. **Small, reversible, sequential.** VPS package maintenance closes before Hermes activation when the phases depend on each other. Reboot and gateway cutover use durable external validators; Zeus is never restarted from its own active foreground chain.
5. **No success by implication.** `packages installed`, `new boot healthy`, `Hermes staged`, `Hermes activated`, and `cleanup complete` are independent acceptance states.
6. **Cleanup follows update provenance.** Remove update-created residue, not normal working caches that will refill. A valid result may be `no deletion needed`.
7. **One final truth.** Close with live readback, inventory/audit/checkpoint, Git synchronization, and one canonical REPORT-INFRA. The user-facing answer always uses the same status fields below.

## Phase 0 — Intake and ledger

Create a checkpoint and phase ledger covering:

- VPS package/tooling audit;
- exact update plan and Critical confirmation;
- package application;
- reboot preparation and post-boot acceptance when required;
- Hermes release/delta review;
- Hermes backup, patch port/staging, activation and runtime validation when a release is pending;
- post-update cleanup audit;
- destructive confirmation/execution only when real targets exist;
- governance and reporting closure.

Overall completion requires every requested phase to be `completed_validated`, `not_needed_validated`, or explicitly deferred/cancelled by Rodolfo.

## Phase 1 — Live preflight

Freeze one coherent observation after refreshing APT metadata and Hermes Git refs:

### VPS

- OS and running kernel;
- installed/expected kernel and reboot marker;
- `apt-get -s upgrade` and `apt-get -s full-upgrade` candidates;
- standard security versus ESM/third-party candidates;
- holds and `dpkg --audit`;
- Snap refresh list;
- Node, npm, Corepack and global npm outdated state;
- `needrestart -b` current/expected kernel and services;
- failed units;
- Zeus, Atena, Ares, auto-commit, cron, Monarx/security and QEMU states/PIDs;
- `/`, `/boot`, EFI disk/inodes.

### Hermes

- canonical launcher and real active repo;
- active Hermes version, local port HEAD and clean/dirty state;
- latest official release tag/SHA;
- active upstream base versus release tag;
- moving-main SHA and post-release commit count separately;
- patch reverse-check/guard surface;
- config/auth/profile-mirror readiness;
- retained rollback runtime and latest validated profile archive.

Never compare the legacy checkout with upstream and call that the active Hermes delta. Resolve from `/root/.local/bin/hermes` and inventory first.

## Phase 2 — Standard plan shown to Rodolfo

The plan always states:

- exact VPS packages/tool versions current→candidate;
- whether package service restarts or host reboot are expected;
- exact current→expected kernel;
- Hermes state: `update pending`, `already latest stable`, or `development main available but out of stable scope`;
- backup/rollback paths to be created or retained;
- activation order and expected interruption;
- cleanup policy: only artifacts created by this update;
- validation and REPORT-INFRA closure.

If Hermes is already on the latest stable release, do not stage or cut over the moving main. Mark the Hermes update phase `not_needed_validated` and still run integrity/config/auth/smoke checks.

## Phase 3 — Critical confirmation

Use one confirmation after the plan whenever possible, but enumerate each Critical Subset action explicitly:

- packages that modify `/usr` with exact versions/transaction;
- system unit/config files under `/etc` when required;
- host reboot current→expected kernel;
- Hermes production launcher/runtime activation and gateway restart;
- any exact deletion manifest with target-set SHA.

A confirmation never covers later targets or changed fingerprints. A volatile cache that changes before execution proves current use; block without mutation rather than chasing repeated hashes.

## Phase 4 — VPS maintenance

1. Build/validate rollback for the exact transaction.
2. Apply only the simulated package/version set.
3. Validate exact versions, APT/full-upgrade candidates zero, holds zero, clean dpkg, services and journals.
4. Treat Snap, npm/Corepack and vendor packages as separate gates.
5. Interpret `needrestart` by named fields; do not rely only on `/var/run/reboot-required`.
6. If reboot is required, prepare a pure foreground verifier and a separate reboot-capable detached finalizer.
7. Post-boot require new boot ID, expected kernel, no reboot marker, clean APT/dpkg/needrestart, zero failed units, fresh Discord readiness for all gateways, security/QEMU/cron/auto-commit active, and unchanged Hermes when its phase is deferred.

## Phase 5 — Hermes maintenance

### Already latest stable

- keep launcher/runtime unchanged;
- run config checks for root + Zeus/Atena/Ares;
- validate operational Codex auth for Zeus/Atena/Ares without printing tokens;
- run patch guard, post-upstream regression and real 3/3 one-shot smokes;
- report moving-main commits only as post-release development work.

### Stable release pending

1. Freeze active upstream base and official release target.
2. Create validated profiles backup and preserve one known-good rollback runtime.
3. Review/port the complete local MGS patch surface in an inactive candidate.
4. Require clean Git, `fsck`, reverse patch checks, compile, patch guard, regression and profile/config/auth checks.
5. Activate through the safe detached flow in explicit order, with Zeus last.
6. Post-activation require launcher/head/version exact, new gateway PIDs, fresh Discord markers, mirrors, operational auth, guard/regression and real smokes.
7. If any gate fails, rollback to the frozen runtime and report the actual state.

### Mandatory benefits explanation after a Hermes version change

Whenever the active Hermes release actually changes, the final response must explain what the newly activated version brought. This is part of completion, not an optional follow-up.

Use the official release notes plus the exact installed-version Git/release range and report:

- previous version/tag → new version/tag and applied commit count;
- new capabilities and workflow improvements;
- reliability and bug-fix impact;
- security and credential/redaction improvements;
- performance, caching, compression, context-window or cost changes;
- config/schema/migration changes and whether MGS action is required;
- practical impact for Zeus, Atena, Ares, crons, Discord and the VPS;
- what is active in the MGS runtime now versus Desktop-only, another platform, opt-in, or out of scope;
- any advertised feature that was reverted or did not ship;
- what did not change, especially MGS patches, providers, auth and operating policy.

Validate model/context claims with the live resolver and selected provider route rather than copying a direct-API number into Codex OAuth. Benefits must describe only the version actually activated; moving-main commits outside the selected stable release are reported separately and never presented as installed benefits.

If no Hermes version change occurred, write `Benefícios da atualização: não aplicável — já estava na última estável`; do not repeat old release highlights as though they were newly installed.

## Phase 6 — Post-update cleanup

The cleanup question is: **what did this update create that is now redundant?**

### Delete only after exact confirmation

- inactive staging/worktrees created by the update;
- superseded candidate `venv-next` environments;
- duplicate update archives beyond the validated latest-per-class policy;
- downloaded package payloads after the rollback window;
- transient build/test directories created by the update;
- obsolete detached finalizers/timers/units after their result is persisted;
- stale Git worktree metadata through Git-native cleanup;
- rollback runtimes older than the one minimum retained rollback.

### Preserve by default

- ordinary UV/pip/npm/compiler caches that support current work;
- required Playwright revisions and persistent browser profiles;
- Whisper/Hugging Face models;
- live profiles, sessions, state DBs and checkpoint stores;
- active Hermes runtime plus one rollback runtime;
- latest validated profile/update archive and latest safety backup;
- previous kernel immediately after a kernel update;
- Git packs with no proven garbage;
- logs/journals governed by system retention.

General cache cleanup is exceptional: disk around/above the MGS warning threshold (~75%), confirmed corruption, retired tool/version, or explicit owner request with a stable hardlink-aware manifest. If no material update-created residue exists, close as `no deletion needed`.

## Phase 7 — Definition of fully updated

Say **“VPS atualizada”** only when:

- APT upgrade and full-upgrade candidates are zero;
- standard security/ESM classification is explicit;
- Snap/npm/tooling gates are closed;
- running and expected kernel agree;
- reboot marker and `needrestart` agree;
- failed units are zero;
- all named operational services are active.

Say **“Hermes atualizado”** only when:

- active upstream base equals the selected official stable release target;
- launcher/runtime/version/head are exact and clean;
- MGS patch guard and regression pass;
- configs/mirrors and operational auth pass;
- 3/3 agent smokes pass.

If already on the latest stable release, say **“Hermes já estava na última estável; integridade validada”**, not that a version update occurred.

Say **“limpeza concluída”** only when either:

- exact confirmed targets were removed and absence/disk/runtime readback passed; or
- the audit proved `no deletion needed` and no deletion phase remains pending.

## Fixed executive response shape

Every plan/status/final answer uses these labels in this order:

- **Resultado:** success, partial, blocked, or already current.
- **VPS:** packages/tooling/kernel/reboot state.
- **Hermes:** installed release, selected target, tests and post-release main distinction.
- **Benefícios da atualização:** mandatory when the Hermes version changed; previous→new, practical MGS impact, active-vs-out-of-scope features, and required action. If unchanged, `não aplicável — já estava na última estável`.
- **Backups:** created, retained, validated and deleted — explicitly say `none` where applicable.
- **Limpeza:** removed bytes/targets or `no deletion needed`; never omit whether deletion happened.
- **Serviços:** Zeus/Atena/Ares and supporting services.
- **Pendência:** exactly one next gate, or `nenhuma`.
- **Evidência:** compact paths/commit/report IDs without raw logs or credentials.

Binary answer comes first. Never let a green Hermes phase imply VPS/cleanup success or vice versa.

## Standard recommendation

When disk is healthy and only recurring caches remain, recommend stopping. The goal is a recoverable, current, low-drift system—not the smallest possible filesystem after every update.
