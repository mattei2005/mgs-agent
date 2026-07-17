# Memory, Skill, and Automatic-Write Governance

## Trigger

Load this reference when changing or auditing:

- `memory.write_approval` or `skills.write_approval`;
- background/self-improvement writes;
- `curator.enabled`;
- MEMORY/USER capacity or compaction;
- staged-write queues and their monitor;
- a claim that a fact can leave memory because it exists in a skill/reference.

## Four independent controls

Do not collapse these into one policy decision:

1. **Write gate** — `write_approval: true` stages; `false` permits direct writes.
2. **Curator** — archive/prune/consolidation behavior. It can remain disabled while direct learning writes stay enabled.
3. **Transparency** — whether an automatic write is reported to the user. This is required independently of the gate.
4. **Context residency** — whether knowledge is always present or only loaded when a route triggers.

A reporting failure does not prove automatic learning should be disabled. Fix transparency separately unless Rodolfo explicitly changes the write policy.

## Always-active versus on-demand classification

Before removing any fact from MEMORY or USER, split it into atomic claims and classify each one.

### Always-active

The rule must influence every relevant turn without waiting for a skill route.

Use:

- **SOUL/AGENT** for identity, authority, security, validation, reporting, restart safety, and global behavioral invariants;
- **USER** for stable Rodolfo preferences that should shape ordinary interaction;
- **MEMORY** for durable contextual facts that must remain present but do not belong in identity/policy.

A fact is not safely removable merely because similar wording exists in a skill. A routed reference is not always-on context.

### On-demand

The fact is only needed when a task activates its domain: host inventories, application codes, site/plugin mappings, campaign procedures, API-specific constraints, and similar operational detail.

Use a skill/reference/data source only after proving:

1. the exact semantic fact exists there;
2. the active router will load it for the relevant task;
3. the destination is canonical and current;
4. readback preserves the full meaning, not just a related paraphrase.

If any condition fails, keep the fact until the destination is created and validated.

## SOUL loading semantics

Hermes loads `HERMES_HOME/SOUL.md` into the stable identity slot during prompt construction. It is then present in every model turn for that session. Because prompt caching is intentional, the file is not reread from disk on every message of an already-open session.

Consequences:

- SOUL is always-active context, not a routed reference.
- A SOUL edit applies to newly built sessions; the explicit user instruction in the current conversation governs the current session immediately.
- Do not claim an exact memory fact is covered by SOUL unless the full invariant is actually present. A narrower reconciliation rule does not necessarily encode the separate fact that sessions are isolated.
- A write gate can change immediately while the reporting policy remains stale: `write_approval_enabled()` reads `config.yaml` on each gate evaluation, whereas the session keeps its cached SOUL. Treat this as a cutover risk, not as evidence that both settings hot-reload together.

Authoritative implementation checkpoints:

- `agent/system_prompt.py`: SOUL content is appended to `stable_parts`.
- `agent/prompt_builder.py::load_soul_md`: reads `HERMES_HOME/SOUL.md` as identity.
- `build_context_files_prompt`: documents that SOUL is always included when present and skipped only when already loaded into the identity slot.
- `tools/write_approval.py::write_approval_enabled`: reloads config when the gate is evaluated.

### Verify active-session cutover

Do not infer policy activation from the live SOUL file or gateway process alone. For each affected profile:

1. Read `state.db` in SQLite read-only mode.
2. Inspect `sessions.system_prompt` for an exact distinctive sentence from the new policy; a file mtime or related paraphrase is insufficient.
3. Inspect `gateway_routing` to identify thread/session mappings that may resume an older cached prompt even when `sessions.ended_at` is populated.
4. Report open/routed thread IDs whose prompt lacks the policy.
5. Use a new thread or explicit session reset to build a fresh prompt. A gateway restart is not required merely to load SOUL into a new session.

Until cutover is complete, avoid continuing an old session when direct writes are already enabled but its cached prompt does not require transparency.

## Safe write-policy change

1. Back up profile configs and affected live/mirror artifacts.
2. Apply approved pending writes before changing the gate when order matters.
3. For scalar values, use the canonical writer:
   - `hermes config set memory.write_approval false`
   - `hermes config set skills.write_approval false`
   - `hermes config set curator.enabled false`
   - `hermes config set skills.creation_nudge_interval 15`
4. Run `hermes config check` for every profile.
5. Validate raw YAML types and the deployed writer resolver, such as `write_approval_enabled(subsystem)`.
6. Confirm live and versioned profile mirrors are byte-identical.
7. Do not restart when the user explicitly requests no restart; record that no restart occurred.
8. Keep the staged-queue monitor: pre-existing or exceptional staged items can remain after direct writing is enabled.

## Drain a legacy staged queue after disabling the gate

Turning `write_approval` off does not resolve records created under the old policy. Do not leave them to age indefinitely and do not bulk-apply them merely because direct writes are now allowed.

For every profile and subsystem:

1. Inventory every pending ID, action, target, origin, summary, and dependency pair.
2. For patches, compare `old_string` and `new_string` against the current live target:
   - one `old_string` match and zero `new_string` matches → technically applicable;
   - zero old/new matches → stale; never force it;
   - `new_string` already present → likely already applied or superseded; reconcile before removal.
3. For `write_file`, verify whether the destination now exists and whether a newer reference already covers the same class.
4. Group reference+router pairs and overlapping patches before recommending a batch decision.
5. Classify each item:
   - **apply** — current, non-duplicative, evidence-backed;
   - **reject** — substantively wrong or unsupported, with rejection evidence;
   - **discard** — obsolete, stale, or superseded; remove only through the audited/canonical queue path available in the deployment.
6. Present one line per item plus a batch recommendation. Wait for the human decision; do not mutate the queue during inventory.

### Canonical discard after explicit approval

Discarding a recovered, stale, or superseded pending record is a deletion and therefore requires the exact Critical Subset confirmation. Keep queue deletion separate from USER/MEMORY compaction: approval to discard records does not authorize rewriting the durable stores.

After approval:

1. Freeze the exact profile/subsystem/pending-ID list. Refuse any extra ID discovered later until separately authorized.
2. Before deletion, create a protected backup outside Git under `/root/.hermes/secure-backups/` with directory mode `0700` and files `0600`. Copy each pending JSON, record its SHA-256 in a manifest, and record pre-action hashes/sizes for the affected `USER.md` and `MEMORY.md` stores.
3. Read each record through `tools.write_approval.get_pending()` under the correct profile scope. Use `hermes_constants.set_hermes_home_override()` / `reset_hermes_home_override()` for in-process multi-profile work; never rely on the default profile fallback.
4. Verify the readback ID, subsystem, failure type, action, and classification match the approved batch. A changed or missing record stops that item; do not substitute another pending ID.
5. Delete only through `tools.write_approval.discard_pending(subsystem, pending_id)`, not raw `rm`/`unlink`. Require `True`, then verify `get_pending(...) is None` and the exact source path is absent.
6. Re-hash every affected USER/MEMORY store and require byte identity with the pre-action manifest. Queue cleanup must not mutate durable memory.
7. Run `monitor_hermes_pending_writes.py --summary-json` and validate exact remaining IDs/counts. For an approved full drain, require `total=0`, `dead_letter_count=0`, and `aged=0`; capacity warnings are a separate follow-up, not proof the discard failed.
8. Append audit with authorized IDs, recovered/superseded classification, backup path, canonical discard method, store-hash proof, and remaining capacity risk. Regenerate inventory and emit/read back the canonical REPORT-INFRA when MGS policy requires it.

Pitfall: a backup proving recoverability does not authorize replaying its payload. Restoring, applying, compacting, and deleting are distinct state changes with distinct scopes.

### Reconcile evidence before rejecting a proposal

Do not reject a staged proposal merely because its evidence is absent from the current session. Reconcile the exact claim in this order: `logs/events-audit.jsonl` → `data/infra-inventory.json` → REPORT-INFRA → Git → `session_search`. Then:

- distinguish live observed usage from measured per-run call counts, projections, and conservative upper bounds;
- preserve the staged wording only when it matches the evidence class exactly;
- correct a stale predecessor when later authorized validation superseded it;
- reject only after the source chain is exhausted or reveals a real contradiction.

For credential-related memory cleanup, separate **bad residency** from **secret exposure**. A credential variable name, provider reference, or `.env` path is unnecessary in MEMORY/USER and can be removed for hygiene, but it is not proof that a credential value leaked. Verify literal exposure without printing the value: compare the active secret internally against MEMORY/USER, logs, reports, the tracked tree, and reachable Git blobs; report only match counts and paths. Generic token/JWT pattern matches are triage evidence, not proof that the active secret leaked. Likewise, the presence of a protected, ignored local credential backup prevents a broad “no sensitive material exists in reports” claim even when the active token has zero matches.

A newly generated class-level reference can legitimately supersede several narrow staged proposals. Prefer the current umbrella and discard duplicate one-session variants rather than applying all of them.

## Capacity failure without silent loss

The built-in memory store rejects an add/replace that would exceed its character limit and returns the current entries. That protects existing memory but does not preserve the unsaved proposal if a background reviewer fails to surface the tool error.

### Interpret the percentage and create headroom safely

A `98%` USER or MEMORY reading is the usage of that one bounded character store, not the model context window, VPS disk, process memory, or overall agent capacity. The store evaluates the projected result before writing, so a proposal can be rejected before the displayed usage reaches exactly `100%`. Existing bytes remain unchanged; the new proposal is the item at risk and must be surfaced or preserved through the deployed dead-letter path.

Hermes has no practical unlimited sentinel for these limits. The configured value is an integer: zero/non-positive values are invalid for the MGS monitor and make ordinary non-empty writes overflow in the built-in comparison. A very large integer merely moves the ceiling; it does not create infinite context. USER/MEMORY is injected into the stable prompt of newly initialized agents, so actual growth consumes context and attention on every session even when prefix caching reduces repeated billing.

Use layered capacity instead of an unbounded always-active prompt:

1. Keep USER/MEMORY for facts that must shape ordinary turns.
2. Put procedures and domain detail in routed class-level skills/references or canonical MGS data.
3. Put institutional decisions/ownership in registry, checkpoints, and MGS OS sources.
4. Use session history/search for long-tail conversation recall.
5. Keep the failure-only dead-letter and capacity monitor as the no-silent-loss safety net.

When Rodolfo authorizes a headroom increase, a safe sequence is:

1. freeze scope to the named active profiles and back up live configs, mirrors, and the capacity monitor;
2. change numeric limits with `hermes config set`, synchronize mirrors, and validate integer type plus semantic diff;
3. adjust the monitor threshold independently and add a boundary test proving the new default;
4. initialize a fresh configured `MemoryStore` per profile and verify the resolved limits, current usage, zero queue drift, and live/mirror equality;
5. run memory/dead-letter tests, business regressions, inventory, audit, Git sync, and REPORT-INFRA;
6. restart only when explicitly requested, through the detached safe finalizer with non-Zeus order preserved and Zeus last.

A headroom increase and a compaction are separate mutations. If the promised workflow says Rodolfo will review a full before/after diff, approval to increase limits or restart does not waive that compaction gate. Increase the approved buffer first, then prepare the semantic compaction diff read-only, and apply it only after the separate review. Likewise, dead-letter deletion does not authorize rewriting USER/MEMORY.

### Deployment gate: approved design is not protection

Never say a dead-letter mechanism protects writes merely because its design was approved or documented. Before relying on it, verify all three layers:

1. an executable overflow branch exists outside documentation and emits a failure-only record such as `capacity_overflow`;
2. a behavior test proves the rejected payload survives with a pending/recovery handle while the memory file remains unchanged;
3. the originating-conversation report and pending/capacity monitor both surface the same exception.

If `capacity_overflow` exists only in a skill/reference, the runtime is still unprotected. Treat the current behavior as fail-closed rejection with possible loss of the unsaved proposal.

Preferred deployed design:

1. Keep normal memory/skill writes direct when the gate is off.
2. Make the store return a machine-readable `error_code: capacity_overflow` for add, replace, and atomic-batch budget failures; never infer overflow by parsing English error text.
3. At the `memory_tool` dispatcher, intercept only that error after a direct write fails and preserve the exact rejected operation in a failure-only pending/dead-letter record. Validation errors, missing targets, drift, and user denials must not create dead letters.
4. Record `failure_type`, target, exact replay payload, current/limit usage, write origin, session/thread identity, and timestamp. Use an idempotency key derived from profile + normalized payload + relevant state so retries do not create duplicate records.
5. Require proof that staging really persisted. The pending writer must return a persisted/readback result rather than a plausible ID after disk failure. Use atomic rename, directory mode `0700`, and file mode `0600`.
6. Return the failure honestly: the durable memory file remains unchanged, `success` stays false, and the response includes `staged`, `pending_id`, usage, and a user-report requirement. Do not describe the memory write itself as saved.
7. Report the failed target, current/limit usage, concise unsaved-content summary, and pending ID in the originating conversation.
8. Let the existing pending/capacity monitor alert immediately on `capacity_overflow`, with anti-spam keyed by pending ID, no sensitive payload in the alert, and a recovery event only after resolution.
9. Never compact, delete, or replace durable facts automatically to make room.

Minimum behavior tests: add/replace/batch overflow preservation; remove and non-capacity errors do not stage; gate-on paths do not double-stage; duplicate retries coalesce; persistence failure is surfaced; `0700/0600` permissions hold; monitor alert/recovery/anti-spam works; and the original MEMORY/USER bytes remain unchanged after rejection.

### MGS implementation surface (2026-07-13)

The deployed-on-disk implementation is carried by `/root/mgs-agent/patches/hermes/memory-dead-letter-structural-trace-2026-07-13.patch` and guarded by `scripts/ensure-hermes-mgs-patches.sh`:

- `tools/memory_tool.py` emits machine-readable `capacity_overflow` and stages only failed add/replace/batch operations;
- `tools/write_approval.py::stage_failure_write` persists and reads back an idempotent failure record atomically with `0700/0600` permissions; its key includes the canonical state fingerprint, and pending-ID lookups reject traversal/path separators;
- `agent/background_review.py::summarize_background_review_actions` surfaces staged or unpersisted `capacity_overflow` failures even when normal write notifications are off, without echoing rejected content;
- `tools/write_trace.py` emits metadata-only structural receipts for successful background skill writes;
- `tools/skill_manager_tool.py` attaches those receipts only to `background_review` writes;
- `scripts/monitor_hermes_pending_writes.py` alerts on a new capacity dead-letter on the next one-minute monitor tick, keyed only by pending ID and without payload content;
- `scripts/finalize-hermes-structural-write.py` closes MGS-synced receipts idempotently through mirror sync, inventory, correlated REPORT-INFRA readback, audit, and receipt readback;
- root cron runs the monitor and structural finalizer every minute under separate `flock` locks.

Do not call the Hermes runtime branch active in already-running gateway processes until the gateways have been safely restarted after the tests pass. A source-file readback proves deployment to disk, not module activation inside a pre-existing Python process. After restart, run a temporary-profile overflow smoke and verify a newly initialized live agent imports the markers before declaring the protection active.

### Close activation without rewriting history

Treat feature readiness, restart-orchestration success, and prompt-policy cutover as separate gates:

1. A failed restart finalizer remains failed. If the services recover later, never append `gateway_restart_finalizer_finished` to that failed run or describe recovery as retroactive success. Run a separately correlated, read-only revalidation and record a distinct revalidation result.
2. Diagnose readiness from the real startup path: capture the agent log offset before restart, restart one profile, then poll until systemd is `active/running` **and** a new Discord connection marker appears after that offset. Use observed profile startup distributions plus safety margin rather than one global sleep; stop before restarting the next agent on any failure.
3. A second restart is justified only when it resolves an unproven runtime property or is explicitly required to test the corrected restart orchestrator. Do not restart merely to create prompt sessions: gateway restart does not construct a new `sessions.system_prompt`.
4. For `policy_in_prompt`, inspect post-change sessions in `state.db` for the exact policy sentence. No post-change session means **not proven**, even if SOUL is correct on disk and the gateway is connected. Require a fresh validation-only turn/thread or explicit session reset; do not label the policy active in Atena/Ares from file readback alone.
5. A one-shot validation/governance job that exited blocked is finished; it will not wake up when the dependency recovers. Schedule a new closure explicitly after the missing evidence exists.
6. Preserve the evidence classes in reporting: code/tests may be PASS while activation remains BLOCKED. State both instead of collapsing the whole proposal into “approved” or “failed.”

### Implementation-review chokepoints

When reviewing a proposed overflow dead-letter against deployed Hermes, verify these less-obvious sibling paths:

- A retry-budget or graceful-degradation wrapper must preserve `error_code: capacity_overflow` and numeric usage fields. A wrapper that replaces the whole error dict after repeated failures can silently bypass dispatcher interception on later retries.
- Intercept overflow only after the approval gate allowed a direct store attempt. Do not intercept approved-pending replay: the original pending record already survives when replay fails, so a second dead letter is duplication.
- Derive the idempotency key from profile scope + canonical replay payload + a target-state fingerprint computed under the store lock. Exclude timestamps, session/thread IDs, and origin from the key; include them only as record context.
- Existing pending writers may be best-effort and return plausible IDs after disk failure. A recovery writer must atomically persist, fsync, read back, verify the record, and fail truthfully when persistence is unconfirmed.
- Create or repair pending directories to `0700` and records to `0600`. Use a unique same-directory temp file and replace the queue entry itself; do not use a symlink-preserving atomic helper for deterministic queue filenames.
- Validate pending IDs as single safe path components before `get` or `discard`; slash-command IDs are user-controlled.
- Background-review summaries often ignore every `success: false` result. Special-case staged and unpersisted `capacity_overflow` before that filter, report target/usage/pending ID, and never expose rejected payload content in alerts. Safety disclosure must survive a normal notification mode of `off`.
- Before a scheduled restart or activation, reconcile every still-running read-only review dispatched for the same change. If a late review produces a valid safety finding, pause activation before its execution time, prove by scheduler/audit readback that no restart started, fix by RED→GREEN, then reschedule only after tests, Git sync, and REPORT-INFRA. A review arriving before activation is part of the gate, not optional post-deploy feedback.
- The model tool schema usually describes inputs only. Keep the capacity contract in result dictionaries rather than adding overflow as an input action or top-level schema combinator.

### Buffer ordering and activation semantics

A temporary limit increase is a bridge, not the durable fix. Raising the cap alone adds no prompt tokens until content actually grows; document the possible maximum growth, compact with a reviewed full diff, then reduce or reassess the cap.

When headroom is critically low and no deployed dead-letter exists, do not delay an explicitly approved temporary buffer behind dead-letter implementation. The design review may come first, but the unimplemented mechanism provides no interim safety. Apply the buffer through the native scalar config writer with backup, config check, live/mirror readback, and the required MGS infrastructure reporting.

Memory limits are captured when `MemoryStore` is instantiated from config; changing YAML does not mutate an already-active store instance. Do not call the change effective for an in-flight agent merely from file readback. Exercise a freshly initialized agent/turn and verify that the live store reports the new limits. A gateway restart is not inherently required, but a new agent initialization is.

The durable safety property is that a failed learning write remains recoverable and visible.

## Mandatory transparency for automatic writes

Whenever background/self-improvement writes memory or a skill directly, report in the originating conversation:

- subsystem (`memory` or `skills`);
- target/path;
- concise description of what was saved;
- validation/readback;
- any background fork that may still write after the foreground response.

A failed automatic write must also be surfaced when it would otherwise lose a learning: include the failure reason, target, current/limit usage, unsaved summary, and recovery/dead-letter handle when available. Do not phrase a capacity rejection as a successful save.

Never say “nothing changed” when an automatic fork wrote. A conversation-level report satisfies automatic-learning transparency by itself; structural script/config/data/AGENT/SOUL changes still follow formal REPORT-INFRA policy.

### Structural trace closure and Discord readback

For an automatic write in an MGS-synced skill/category, conversation transparency and structural closure are separate obligations. Close the structural trace with a correlated receipt containing profile, subsystem, origin session/thread, exact paths, before/after hashes, and readback result; then synchronize the mirror, regenerate inventory, append audit, and send one canonical REPORT-INFRA.

Never identify a Discord embed from timestamp proximity, author, or blank `content`. Several automated reports can land in the same channel close together, and embeds appear as empty content in compact message listings. Read back the exact message ID through an authenticated Discord GET (without printing credentials) and verify `content` is empty plus the expected embed title and semantic fields. Derive field labels from the current canonical helper/readback contract or compare normalized labels case-insensitively; do not hard-code stale uppercase labels. If the helper already returned HTTP 200 but a local verifier fails, GET that exact message ID and diagnose the verifier before posting again—never create a duplicate REPORT merely because validation code expected an older field schema. If the candidate message is a different report, correct the attribution explicitly and keep the infrastructure trace open until the real REPORT-INFRA is posted and read back.

A durable finalizer should be idempotent on profile + paths + post-write hashes. It marks the receipt closed only after mirror, inventory, audit, REPORT-INFRA, and Discord readback all succeed; a conversation report alone must not masquerade as that structural completion.

### Audit historical capacity rejections before claiming “no loss”

Separate two questions:

1. **Was existing MEMORY/USER content deleted or changed?** Compare live files with backups, mtimes, approved write events, and semantic diffs.
2. **Was a new proposed learning rejected before persistence?** Query `state.db` read-only for `messages.tool_name='memory'` capacity failures, pair each result with its originating assistant `tool_call_id`, and inspect subsequent memory calls before the next user message.

For each rejection:

- a later successful add/replace/batch in the same turn is a recovered write, not loss;
- no immediate success is only an unresolved candidate—search current MEMORY, USER, SOUL, routed skills/references, audit, Git, and the originating session for a semantically equivalent recovery;
- count duplicate retries as one proposed learning;
- if the durable fact exists only in session history, restore it to the correct class-level skill or always-active memory and report the readback;
- never say “nothing was lost” merely because the durable memory file stayed byte-identical: fail-closed rejection protects old content while the new proposal can still be absent.

Report the evidence class precisely: **no existing-data deletion**, **rejected proposal recovered**, **rejected proposal restored during audit**, or **unresolved historical proposal**. The durable dead-letter prevents future silent rejection; it does not retroactively prove old failures were recovered.

### Prevent structural receipts from becoming permanent drift loops

The preferred writer records only files actually created, modified, or removed by one automatic write. The finalizer must also be defensive with legacy/full-directory receipts: derive the receipt delta as every path where `before[path] != after[path]`, and validate/synchronize only that set. A later authorized write to an unchanged sibling path must not turn the older receipt into `live_hash_drift`.

Keep fail-closed behavior for the receipt's own delta: if a path that the receipt actually created, modified, or removed no longer matches its expected post-write state, block and reconcile rather than rewriting expected hashes.

When an existing receipt is blocked by drift:

1. derive and display the actual changed-path set from `before` versus `after`;
2. identify whether the drift is on the receipt's own delta or only on an unchanged sibling captured by an older broad snapshot;
3. reconcile attribution through audit → inventory → REPORT-INFRA → Git → session history;
4. prove live and mirror equality for the current changed files;
5. classify a delta conflict as real conflict or unattributed drift; treat sibling-only drift as a later authorized supersession when the source chain proves it;
6. never rewrite expected hashes merely to make a receipt pass;
7. make closure idempotent and preserve original hashes, correlation/commit, reason, REPORT readback, and audit readback;
8. stop minute-by-minute retry noise after a bounded attempt threshold and raise one metadata-only alert rather than silently looping forever.

Regression coverage must include both directions: drift in the receipt's own changed path stays blocked before side effects, while drift in a sibling whose before/after hashes were identical does not block closure.

## Cross-agent USER/MEMORY standardization

Standardize the **governance and residency model**, not identical file contents.

- Every active agent should use the same safety architecture: bounded stores, capacity monitoring, dead-letter recovery, backup/readback, and reviewed compaction.
- `USER` contains stable Rodolfo preferences that should shape that agent's ordinary work. Truly global interaction preferences may appear across profiles; domain-only preferences stay with the relevant agent.
- `MEMORY` contains durable agent-specific context and lessons. Do not copy the same operational inventory into every profile merely for symmetry.
- Institutional ownership, company policy, and cross-agent decisions belong in MGS OS/registry/SOUL rather than duplicated MEMORY entries.
- Procedures and application-specific constraints belong in routed skills/references or canonical data.
- Runtime truth such as active model, curator state, service state, and credential topology must be verified from live config/runtime before rewriting a stale memory entry. MEMORY is not the source of truth for those values.

Identical USER/MEMORY files create prompt bloat and multi-copy drift. The desired invariant is: **same schema and governance, shared global preferences where justified, agent-specific content otherwise**.

### Compaction audits must inspect active automation

A stale memory fact can reveal an automation that would recreate the deprecated state. Before treating it as text-only cleanup:

1. Identify any named cron, systemd unit, sync script, finalizer, or background writer in the entry.
2. Inspect the live scheduler and executable behavior read-only.
3. Compare the automation direction with the current canonical architecture.
4. If it can undo a validated state, stop the compaction audit and open a separate system-change gate; do not hide the risk by merely rewriting memory.
5. After authorization, back up scheduler + affected stores, neutralize the narrow automation reversibly (prefer a commented cron line and preserved script when appropriate), validate readback, then correct the stale entries.
6. Resume the full no-write compaction matrix only after the runtime contradiction is closed.

For exclusive per-agent OAuth, a legacy global→profiles sync is incompatible even when its current dry-run makes zero writes because the global timestamp is older. A future global refresh can make it destructive. Validate safely by:

- comparing access/refresh fingerprints pairwise without printing token values;
- confirming the active scheduler line count before/after;
- running one real inference per active profile;
- checking a fresh session prompt contains corrected memory and excludes stale model/curator/sync claims;
- preserving the old script for rollback unless deletion receives its own critical authorization.

## Provider-architecture gate before building a custom compactor

When USER/MEMORY pressure is recurring rather than a one-time cleanup, evaluate Hermes' current native memory-provider architecture before designing a bespoke semantic autocompactor. Honcho can operate as a native `memory.provider`, with cross-session persistence, user modeling, session context, semantic conclusions/search, per-peer isolation, and a bounded injected-context budget. This can reduce dependence on ever-growing file-backed USER/MEMORY; it does not automatically compact or safely migrate the existing files.

Use this sequence:

1. Read the current official Hermes Memory Providers and Honcho documentation; provider behavior changes faster than MGS wrapper notes.
2. Inspect live profile state separately: `memory.provider`, profile-local `honcho.json`, provider status, and whether the deployment is only using the legacy/manual `mgs-memory-copilot` wrapper. A working manual wrapper is not proof that Honcho is the active Hermes provider.
3. Classify information before migration: always-active safety/authority remains in SOUL/AGENT or minimal USER/MEMORY; canonical MGS facts remain in JSON/DB/Git/audit; Honcho holds user modeling, session context, and derived conclusions subject to canonical validation.
4. Decide the data boundary before activation. Managed Honcho must not receive raw private MGS conversations under a sanitized-only policy; use sanitized/manual inputs or approve a separate self-hosted deployment for operational history.
5. Pilot one profile with backup, bounded `contextTokens`, explicit gateway peer mapping, real cross-session continuity tests, rollback, and readback before broader rollout.
6. Only after the provider pilot decide whether a residual 90% monitor or autocompactor is still needed. Keep the monitor as a fail-safe until the new provider and migration have passed end-to-end validation.

Pitfall: solving a provider-architecture problem with increasingly complex file rewriting. Before adding retries, validators, or model passes to a custom compactor, ask whether the durable information belongs in file-backed always-active context at all.

## Compaction workflow

1. Read the live MEMORY, USER, SOUL, AGENT, routed skills, canonical data sources, and any automation named by the entries.
2. Record exact current character counts.
3. Decompose mixed entries into atomic claims.
4. Classify every claim as always-active or on-demand.
5. Identify the exact destination and prove route/load semantics.
6. Preserve facts with no sufficient destination.
7. Produce the complete before/after diff and destination matrix.
8. Obtain the required human review before deleting approved or always-active facts.
9. Back up, apply, validate character counts, and read back every retained invariant.
10. Verify capacity-monitor recovery and report the write.

### Automatic compaction at the 90% threshold

Rodolfo's confirmed policy is automatic compaction of USER/MEMORY when a store reaches 90%, followed by a metadata-only before/after report in `#limites-90`; do not request per-occurrence approval. Keep the configured 3600/6400 limits unless he separately changes them. After Rodolfo approved native Honcho integration for all current and future MGS agents, treat this compaction path as residual capacity protection—not the primary long-term memory architecture.

Treat desired policy and active protection separately. Hermes upstream does not auto-compact by itself, and an approved Honcho rollout is not evidence that any profile already uses it. Before changing the compactor, inspect `memory.provider`, profile-local Honcho configuration, provider status, peer mapping, and a real cross-session canary for each profile. Until Honcho is active and validated per agent, do not claim it has removed the 90% risk. Likewise, do not claim automatic compaction is active until the monitor is connected to a compactor and an end-to-end temporary-profile canary proves semantic preservation, atomic write, protected backup, readback, failure alerting and anti-loop behavior. A prototype or green unit suite alone is insufficient.

While activation is blocked, preserve the current fail-closed behavior and handle an actual threshold occurrence conservatively:

1. Verify the alert and current source hash; a zero-savings exact-duplicate proposal is a no-op snapshot, not a write.
2. Create a protected `0700/0600` backup.
3. Rewrite the smallest sufficient set of long entries, preserving every atomic fact and keeping unaffected entries byte-identical.
4. Apply replacements atomically, validate exact changed indexes, entry count, characters, percentage, file mode and post-write hash.
5. Run the monitor read-only and require zero warnings/errors; verify the scheduled recovery embed by exact message ID.
6. Report that the occurrence was compacted but automatic future activation remains blocked when that is the real state.
7. Leave stale proposal/backup deletion separate because file deletion has its own authorization gate.

A semantic compactor must fail closed on model timeout, malformed output, protected-literal drift, semantic-verifier rejection or concurrent source change. After repeated failures, stop rather than weakening validation or silently applying an unverifiable rewrite.

## Pitfalls

- **Canonical-source fallacy** — “it exists in a reference” is not equivalent to “the agent knows it by default.”
- **Paraphrase loss** — a related SOUL rule may not preserve the exact approved fact.
- **Hot-reload assumption** — SOUL is stable per built session, not reread from disk each turn.
- **Split cutover** — the write gate reloads config while an old session keeps cached SOUL, enabling direct writes before the session knows it must report. Verify `sessions.system_prompt` and move work to a fresh thread/reset.
- **Orphan queue rot** — disabling the gate does not decide old staged items. Inventory applicability, dependencies, overlap, and supersession; never bulk-apply or leave them indefinitely.
- **Silent capacity rejection** — fail-closed protects existing memory but can lose the proposed learning. Report the failure and preserve the rejected payload in a failure-only dead-letter path.
- **Policy coupling** — direct writes, curator pruning, user reporting, and context residency are separate controls.
- **Premature limit increase** — raising char limits before classification can hide misplaced procedure and stale state.
- **Silent foreground claim** — background writes remain the agent’s responsibility even when performed by a fork.

## Verification checklist

- [ ] Every removed claim classified individually
- [ ] Always-active claims remain in SOUL/AGENT/USER/MEMORY
- [ ] On-demand claims have exact content plus a working route
- [ ] SOUL coverage checked semantically, not by keyword only
- [ ] Config values validated through the runtime resolver
- [ ] Character-limit changes validated on a freshly constructed configured `MemoryStore` or newly initialized agent, not only YAML readback
- [ ] Active/routed sessions checked for the exact new policy in `sessions.system_prompt`
- [ ] Fresh thread/reset used where an old cached SOUL would permit unreported direct writes
- [ ] Curator state validated separately from write gates
- [ ] Existing staged queue inventoried for current, stale, overlapping, and superseded items
- [ ] Dependency pairs kept together and no stale patch forced
- [ ] Capacity failures are reported and preserve the unsaved proposal through a recovery/dead-letter handle
- [ ] Full diff reviewed before compaction
- [ ] Automatic writes reported with target and readback
- [ ] MGS-synced automatic writes have correlated mirror/inventory/audit/REPORT closure and the exact Discord embed was read back by message ID
