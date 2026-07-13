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

Authoritative implementation checkpoints:

- `agent/system_prompt.py`: SOUL content is appended to `stable_parts`.
- `agent/prompt_builder.py::load_soul_md`: reads `HERMES_HOME/SOUL.md` as identity.
- `build_context_files_prompt`: documents that SOUL is always included when present and skipped only when already loaded into the identity slot.

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

## Mandatory transparency for automatic writes

Whenever background/self-improvement writes memory or a skill directly, report in the originating conversation:

- subsystem (`memory` or `skills`);
- target/path;
- concise description of what was saved;
- validation/readback;
- any background fork that may still write after the foreground response.

Never say “nothing changed” when an automatic fork wrote. A conversation-level report satisfies automatic-learning transparency by itself; structural script/config/data/AGENT/SOUL changes still follow formal REPORT-INFRA policy.

## Compaction workflow

1. Read the live MEMORY, USER, SOUL, AGENT, routed skills, and canonical data sources.
2. Record exact current character counts.
3. Decompose mixed entries into atomic claims.
4. Classify every claim as always-active or on-demand.
5. Identify the exact destination and prove route/load semantics.
6. Preserve facts with no sufficient destination.
7. Produce the complete before/after diff and destination matrix.
8. Obtain the required human review before deleting approved or always-active facts.
9. Back up, apply, validate character counts, and read back every retained invariant.
10. Verify capacity-monitor recovery and report the write.

## Pitfalls

- **Canonical-source fallacy** — “it exists in a reference” is not equivalent to “the agent knows it by default.”
- **Paraphrase loss** — a related SOUL rule may not preserve the exact approved fact.
- **Hot-reload assumption** — SOUL is stable per built session, not reread from disk each turn.
- **Policy coupling** — direct writes, curator pruning, user reporting, and context residency are separate controls.
- **Premature limit increase** — raising char limits before classification can hide misplaced procedure and stale state.
- **Silent foreground claim** — background writes remain the agent’s responsibility even when performed by a fork.

## Verification checklist

- [ ] Every removed claim classified individually
- [ ] Always-active claims remain in SOUL/AGENT/USER/MEMORY
- [ ] On-demand claims have exact content plus a working route
- [ ] SOUL coverage checked semantically, not by keyword only
- [ ] Config values validated through the runtime resolver
- [ ] Curator state validated separately from write gates
- [ ] Existing staged queue preserved and monitored
- [ ] Full diff reviewed before compaction
- [ ] Automatic writes reported with target and readback
