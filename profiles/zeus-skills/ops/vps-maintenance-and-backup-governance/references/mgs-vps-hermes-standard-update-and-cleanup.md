# MGS Standard — VPS + Hermes Update and Cleanup

## Purpose

This is the canonical contract whenever Rodolfo asks to update, review, verify, or clean the MGS VPS and Hermes in the same initiative. It standardizes execution order, authorization gates, cleanup semantics, and the executive answer so the result does not vary by session.

Use the specific VPS/Hermes references for implementation details; this document owns the combined lifecycle and reporting shape.

## Fixed operating policy

1. **Plan first.** Begin with a live read-only audit and present one concrete plan before any package install, runtime cutover, restart, reboot, or deletion.
2. **Target semantics follow Rodolfo's standing MGS policy.** `Atualizar tudo`, `não deixar commit pendente`, invoking the controlled VPS + Hermes plan, or equivalent selects the latest fetched `origin/main` SHA—even when it is post-release development without a newer public tag. Stable-only applies only when Rodolfo explicitly limits the scope to the latest stable release. If the thread began as a version/commit-gap review, carry that target intent into the follow-up execution instead of silently narrowing it to the public tag. Freeze the target for the port; require zero known upstream commits at the final activation gate. A commit published only after a validated cutover is a new update, not a hidden pendency in the completed run.
3. **Critical gates stay exact.** Modifying `/usr`, `/etc`, `/boot`, rebooting, or deleting files requires the `AGENT.md` confirmation with exact current→target state. Scope drift, including reduction or volatile-cache drift, invalidates the confirmation.
4. **Small, reversible, sequential.** VPS package maintenance closes before Hermes activation when the phases depend on each other. Reboot and gateway cutover use durable external validators; Zeus is never restarted from its own active foreground chain. Before scheduling a detached finalizer that will restart Zeus, deliver the current user-facing reply first, then schedule the silent external job; never leave Rodolfo believing he must answer merely to let an already-authorized cutover continue.
5. **No success by implication.** `packages installed`, `new boot healthy`, `Hermes staged`, `Hermes activated`, and `cleanup complete` are independent acceptance states.
6. **Cleanup follows update provenance and the owner’s explicit retention target.** Normally remove update-created residue, not working caches that will refill. When Rodolfo requires only the latest Hermes/VPS maintenance backup, that explicit override replaces the default multi-rollback retention for that operational class: retain the active runtime plus one latest validated backup, freeze every older backup/runtime/launcher in one exact manifest, and keep the task open until the separately confirmed deletion passes readback. Never widen this shorthand to system, site, browser-session, or credential backups unless he names those classes.
7. **One final truth.** Close with live readback, inventory/audit/checkpoint, Git synchronization, and one canonical REPORT-INFRA. The user-facing answer always uses the same status fields below.

## Phase 0 — Intake and ledger

Create a checkpoint and phase ledger covering:

- VPS package/tooling audit;
- exact update plan and Critical confirmation;
- package application;
- reboot preparation and post-boot acceptance when required;
- Hermes release/delta review;
- Hermes backup, patch port/staging, activation and runtime validation when the selected stable or main code target is pending;
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

Never compare the legacy checkout with upstream and call that the active Hermes delta. Resolve from `/root/.local/bin/hermes` and inventory first. Keep Phase 1 genuinely read-only: do not create a full profile archive during precheck. Large live profile trees can turn a non-mutating audit into a multi-gigabyte timeout and invalid partial archive; create the validated control-plane/profile rollback only after confirmation, immediately before the mutating Hermes stage.

## Phase 2 — Standard plan shown to Rodolfo

The plan always states:

- exact VPS packages/tool versions current→candidate;
- whether package service restarts or host reboot are expected;
- exact current→expected kernel;
- Hermes scope and state: `selected target already reached`, `stable-only requested: release pending`, or `main requested: code target pending`; name the frozen target SHA and report post-release main separately when stable-only was explicitly requested;
- backup/rollback paths to be created or retained;
- activation order and expected interruption;
- cleanup policy: only artifacts created by this update;
- validation and REPORT-INFRA closure.

If the selected scope is latest-stable and Hermes is already on that release, do not stage or cut over moving `main`; mark the Hermes update phase `not_needed_validated` and still run integrity/config/auth/smoke checks. If Rodolfo requested `atualizar tudo` or zero pending commits, latest-stable does not close the phase while `origin/main` is ahead: target the frozen moving-main SHA through the controlled large-port workflow.

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
3. Validate exact versions, zero executable APT/full-upgrade transactions pending inside the confirmed scope, clean dpkg, services and journals. Classify phased updates using fresh simulations plus policy evidence, and inventory each hold with its owner authorization and reason. Preserve authorized holds; investigate undocumented holds rather than removing them to manufacture a zero. New executable packages outside the frozen transaction remain a separate confirmation gate and must not be hidden as completed work.
4. Treat Snap, npm/Corepack and vendor packages as separate gates.
5. Interpret `needrestart` by named fields; do not rely only on `/var/run/reboot-required`.
6. If reboot is required, prepare a pure foreground verifier and a separate reboot-capable detached finalizer.
7. Post-boot require new boot ID, expected kernel, no reboot marker, clean APT/dpkg/needrestart, zero failed units, fresh Discord readiness for all gateways, security/QEMU/cron/auto-commit active, and unchanged Hermes when its phase is deferred.

## Phase 5 — Hermes maintenance

### Selected target already reached

- Apply this branch only when the active upstream base reaches the selected target. Being on the latest stable is sufficient only for an explicitly stable-only request; it never closes a main/zero-pending request while public main is ahead.
- keep launcher/runtime unchanged;
- run config checks for root + Zeus/Atena/Ares;
- validate operational Codex auth for Zeus/Atena/Ares without printing tokens;
- run patch guard, post-upstream regression and real 3/3 one-shot smokes;
- for stable-only, report moving-main commits as out-of-scope post-release development; for main, prove target equality with the final public ref or the explicitly authorized cutoff policy.

### Stable-only requested — release pending

Use this branch only when Rodolfo explicitly chose stable-only. Validate the latest official non-draft, non-prerelease GitHub release and freeze its tag/SHA; the nearest Git tag alone is not release proof. Post-release main does not block this branch and is not activated implicitly.

Follow the shared pending-target sequence below with that stable SHA.

### Main requested — code target pending

Use this branch for `atualizar tudo`, zero pending commits, or the standing combined plan without an explicit stable-only limit, including when no newer release tag exists. Verify the public upstream remote, freeze the active upstream base and latest public main SHA, and port in an inactive candidate. Use bounded repeated fetches before exact-SHA confirmation; if main cannot stabilize, stop for Rodolfo's explicit quiet-window or frozen-cutoff decision instead of repeatedly requesting approvals. A frozen-cutoff result must disclose later commits rather than claim public main has zero pending commits.

Follow the same shared sequence; version-label equality does not eliminate the code-update phase or benefits report.

### Shared pending-target sequence

1. Freeze the verified active upstream base and the selected stable/main target. Inventory manifest-backed patches, committed `base..HEAD` customizations, staged/unstaged changes and untracked local files; a clean working tree is not proof of stock code. Use `references/git-update-delta-and-patch-portability.md` for full-surface checks.
2. Crie snapshots nativos rápidos e validados por profile como rollback primário e preserve um runtime conhecido; não use archive recursivo da árvore viva de profiles como default. Full archive só entra com requisito explícito, headroom/timeout modelados e validação integral conforme `hermes-agent-operations/references/hermes-update-core.md`.
3. Review/port the complete local MGS patch surface in an inactive candidate.
4. Require clean Git, `fsck`, reverse patch checks, compile, patch guard, regression and profile/config/auth checks.
5. Activate through the safe detached flow in explicit order, with Zeus last.
6. Post-activation require launcher/head/version exact, new gateway PIDs, fresh Discord markers, mirrors, operational auth, guard/regression and real smokes.
7. If any gate fails, rollback to the frozen runtime and report the actual state.

### Protected workload collateral proof

When the Hermes/VPS cutover must prove that a separate protected production workload was untouched, capture a deterministic read-only fingerprint immediately before launcher/service mutation and again immediately after gateway readiness; an older backup-time fingerprint is historical evidence, not the cutover baseline.

For the MGS finance system, reach the RunCloud host only through `apps/finance-system/deploy/runcloud_ops.py` after `scripts/mgs_google_workspace_auth.py::load_env()`. Do not borrow the off-site-backup SSH wrapper or infer its vault/item because backup transport and finance operations have different credential routes. Run bounded PostgreSQL reads with the packaged client under `sudo -n -u mgs_pg`, the explicit `LD_LIBRARY_PATH`, socket `/run/mgs-postgresql18` and role `mgs_pg`. Hash each row first with `md5(row_to_json(t)::text)`, then aggregate only short hashes in deterministic key order; never aggregate full JSON documents or guess stale column names.

A pre-cutover mismatch is not automatically collateral damage: reconcile approved concurrent writers before mutation. In finance, scheduled `AUTO_QUOTES_UPDATED` activity legitimately changes `scenarios` and appends `audit_events`; inspect only action, actor and timestamp, attribute the writer, then refresh the just-in-time baseline. Keep the post-cutover comparison fail-closed unless the same approved writer is explicitly reconciled. If a chained validation command exits nonzero, rerun each gate separately before naming the failed component—the aggregate shell status does not identify which command failed.

### Evidence-seal closure

1. Write every cutover receipt, protected-workload pre/post fingerprint, deletion readback and final service/inventory result **before** declaring the retained backup finally sealed. A pre-cutover seal proves only the components present at that boundary.
2. After the last evidence write, regenerate the component checksum manifest from the complete retained set, excluding the checksum manifest and its top-level seal to avoid self-reference. Record the exact entry count in the backup manifest, then hash the backup manifest plus component manifest into the top-level seal.
3. Verify both layers by readback. If any evidence file or manifest field changes afterward—even a final finance readback or retention status—regenerate both manifests and revalidate the count; never report an older green seal against a newer directory state.
4. Keep historical failed-attempt logs as audit evidence when they are safe, but distinguish them from the final successful artifacts in the manifest.

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

If neither the Hermes release nor the active upstream code target changed, write `Benefícios da atualização: não aplicável — o runtime já estava no alvo selecionado`; do not repeat old release highlights as though they were newly installed. If a moving-`main` promotion changes the active upstream SHA while the semantic release label stays the same, benefits are still mandatory: summarize only the exact `old-upstream-base..new-main` commits, distinguish MGS-runtime effects from Desktop/other-surface changes, and say explicitly that the release version number did not change.

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
- active Hermes runtime plus one rollback runtime, **unless Rodolfo explicitly set latest-only retention for this maintenance class**;
- latest validated profile/update archive and latest safety backup, **or exactly one latest validated backup when latest-only retention was requested**;
- previous kernel immediately after a kernel update;
- Git packs with no proven garbage;
- logs/journals governed by system retention.

Under latest-only retention, the active runtime is not counted as a backup. Make any candidate created with shared Git objects independent before targeting the former source runtime; otherwise deleting the source can corrupt the active repository.

General cache cleanup is exceptional: disk around/above the MGS warning threshold (~75%), confirmed corruption, retired tool/version, or explicit owner request with a stable hardlink-aware manifest. If no material update-created residue exists, close as `no deletion needed`.

### Final auto-commit activation

When auto-commit was deliberately contained during the update and Rodolfo asked to restore it at the end:

1. Recompute the exact watcher candidate set with the watcher's real pathspecs, `git status --porcelain=v1 -z --untracked-files=all`, sensitive-name policy and per-file size ceiling. Scan eligible files against protected secret values and key formats without printing values; large protected finance evidence stays local and untracked.
2. Enable/start the real unit only after cutover, retained-backup validation and cleanup are closed. Read back `enabled`, `active/running`, a nonzero PID and the expected watcher command.
3. Do not assume an inotify watcher scans an already dirty tree on startup. For a bounded activation canary, use a temporary `/run/systemd/system/<unit>.d/` override with batch target `1`, quiet period `0` and a short max wait; daemon-reload/restart, then make one legitimate byte-changing write to an already authorized receipt or inventory file. `touch` is insufficient when the event mask omits `attrib`.
4. Require an auto-generated commit—never a manual substitute—inspect exact committed paths and blob sizes, fetch the remote and prove `HEAD == origin/main`. Oversized skipped files must remain local and no unexpected eligible path may remain.
5. Restore production batching, daemon-reload/restart and read back the effective environment. Inspect the watcher tail for restart loops or repeated no-op flushes, refresh the infrastructure inventory from the final service state and let that inventory traverse the same verified auto-commit path when needed.

## Phase 7 — Definition of fully updated

Say **“VPS atualizada”** only when:

- fresh APT upgrade and full-upgrade simulations show zero executable transactions pending in the approved scope, with no undisclosed executable update outside it; phased deferrals and authorized holds are listed with evidence and reported as residuals, not forced away; undocumented holds or newly actionable transactions leave the relevant decision gate open;
- standard security/ESM classification is explicit;
- Snap/npm/tooling gates are closed;
- running and expected kernel agree;
- reboot marker and `needrestart` agree;
- failed units are zero;
- all named operational services are active.

Say **“Hermes atualizado”** only when:

- active upstream base equals the selected target: latest official stable when stable-only was requested, or the final frozen `origin/main` SHA when Rodolfo required zero pending commits;
- for main/zero-pending scope, the just-in-time pre-activation public fetch equals the frozen target, unless Rodolfo explicitly approved a fixed cutoff; disclose any later commits under that exception and never call them zero pending. For stable-only, revalidate the official stable target; post-release main remains explicitly outside scope;
- launcher/runtime/version/head are exact and clean;
- MGS patch guard and regression pass;
- configs/mirrors and operational auth pass;
- 3/3 agent smokes pass.

If stable-only was explicitly requested and the runtime was already on that release, say **“Hermes já estava na última estável; integridade validada”**, not that a version update occurred. For main scope, say the selected code target was already reached only after upstream-base/target equality and integrity checks; latest-stable status alone is insufficient.

Say **“limpeza concluída”** only when either:

- exact confirmed targets were removed and absence/disk/runtime readback passed; or
- the audit proved `no deletion needed` and no deletion phase remains pending.

## Fixed executive response shape

Every plan/status/final answer uses these labels in this order:

- **Resultado:** success, partial, blocked, or already current.
- **VPS:** packages/tooling/kernel/reboot state.
- **Hermes:** installed release, selected target, tests and post-release main distinction.
- **Benefícios da atualização:** mandatory whenever the active release or upstream code target changed; show the exact previous→new release/SHA range, practical MGS impact, active-vs-out-of-scope features, and required action. Use `não aplicável` only when both version and active code target were already unchanged.
- **Backups:** created, retained, validated and deleted — explicitly say `none` where applicable.
- **Limpeza:** removed bytes/targets or `no deletion needed`; never omit whether deletion happened.
- **Serviços:** Zeus/Atena/Ares and supporting services.
- **Pendência:** exactly one next gate, or `nenhuma`.
- **Evidência:** compact paths/commit/report IDs without raw logs or credentials.

Binary answer comes first. Never let a green Hermes phase imply VPS/cleanup success or vice versa.

## Standard recommendation

When disk is healthy and only recurring caches remain, recommend stopping. The goal is a recoverable, current, low-drift system—not the smallest possible filesystem after every update.
