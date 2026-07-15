# MGS Institutional Knowledge and Continuity

## Trigger

Use when Rodolfo wants agents to preserve important context across sessions, restarts, handoffs, or future growth without forcing him to repeat decisions, strategies, ownership, and agent functions.

## Executive framing

Do not present this primarily as a memory-engineering problem. Rodolfo's required outcome is simple: **an important fact already decided should be found and reused without him repeating it**.

Separate four properties:

1. **Availability** — agent processes stay online.
2. **Durability** — important knowledge survives process/session loss.
3. **Retrieval** — the correct agent can locate the current source.
4. **Governance** — stale or unauthorized information does not become active truth.

Agent MEMORY/USER is a small always-active cache, not the company database. MGS OS and canonical runtime/data sources are the institutional memory.

## Knowledge classification

Route every durable item before writing:

```text
Stable user preference             USER/MEMORY
Identity/global behavior           SOUL/AGENT under its authorization gate
Reusable procedure                 skill/reference
Company structure/owner/route      context/*.md
Current operational state          data/database/external dashboard
Approved strategic decision        knowledge registry + canonical source
Unapproved candidate               knowledge inbox only
Long-running initiative state      checkpoint
Executed event                     events-audit.jsonl
Credentials                        1Password only
```

Capture is not promotion. Never turn conversation text into policy merely because it was captured.

## MGS implementation surface

Current foundation:

```text
context/knowledge-governance.md
scripts/mgs-knowledge-control.py
data/knowledge-registry.json
data/knowledge-inbox.jsonl
data/agent-checkpoints.json
tests/test_mgs_knowledge_control.py
docs/mgs-knowledge-continuity-plan.md
```

`data/knowledge-registry.json` stores metadata and canonical pointers, not duplicate copies of every fact. Only one active record may exist per `canonical_key`; replacements use explicit `superseded_by` links.

`data/knowledge-inbox.jsonl` is candidate-only and is never a source of truth.

A checkpoint answers: objective, current state, next step, responsible agent, thread/source, and update time. It does not replace audit or the pendência system.

## Safe rollout sequence

### Phase 0 — Stabilize

- Measure USER/MEMORY usage with exact character counts.
- Inspect capacity dead-letters without exposing payloads publicly.
- For every rejected proposal, classify it as already recovered, needs restoration, or still unresolved.
- Consolidate only when full meaning is preserved.
- Never delete a pending/dead-letter file automatically; canonical discard deletes a file and therefore follows the Critical Subset confirmation.

### Phase 1 — Add the institutional foundation

- Add governance, registry, inbox, checkpoint store, deterministic CLI, and tests.
- Keep the first block additive: no restart, permission change, credential change, or agent behavior cutover.
- Register Rodolfo's approved decision directly; do not leave an already-approved decision as an inbox candidate.
- Update `mgs-os-map.md`, `sources-of-truth.md`, and relevant Company OS pointers.

### Phase 2 — Pilot one agent

- Start with Zeus only.
- Add automatic candidate capture and checkpoint behavior only after a separate behavior-change gate.
- Prove retrieval through representative business questions.
- A deployed script or governance document is not proof that automatic ingestion is active.

### Phase 3 — Roll out one agent at a time

- Atena and Ares receive only domain-relevant routes.
- Validate live behavior and rollback independently.
- Historical agents such as Hera remain history/rollback; do not recreate them from stale plans.

### Phase 4 — Disaster recovery

- Add encrypted off-host backup for the approved repo/profile/session/database surface.
- Define RPO/RTO.
- Run an isolated restore drill.
- A local tar validation proves archive readability, not off-host durability or operational restoration.

## Transactional control requirements

For JSON registers and checkpoints:

- every mutator uses the same exclusive lock;
- reload state after acquiring the lock;
- validate IDs and active canonical-key uniqueness;
- write same-filesystem temp + flush + fsync + atomic replace + directory fsync;
- perform semantic readback while still locked;
- candidate IDs are idempotent from normalized content;
- test concurrent capture, duplicate active keys, supersession, missing sources, checkpoint upsert, and replace failure.

Use the class-level `software-development-methods` reference `transactional-json-registers.md` for the full concurrency pattern.

## Validation and closure

Minimum proof:

- focused tests pass, including OS/process or thread concurrency where applicable;
- production registry validator returns no errors;
- source paths exist;
- registry/inbox/checkpoint counts match expectations;
- no secret-pattern findings in changed files;
- `git diff --check` passes;
- infra inventory is regenerated and confirms executable/non-empty data artifacts;
- Git auto-commit/push reaches `HEAD == origin/main` without manual push;
- REPORT-INFRA helper succeeds and the exact message ID is read back with empty content, one expected embed, semantic fields, and no mentions;
- audit records implementation and REPORT readback separately.

Generated inventory may omit an intentionally empty JSONL inbox while Git still tracks it. Do not misclassify that as missing infrastructure: verify the executable and non-empty stores in inventory, and verify the empty inbox through Git/readback.

## Phase 2 Zeus pilot implementation pattern

1. Back up live and versioned Zeus SOUL, prove their pre-change hashes match, then patch both with one compact always-active continuity section. Detailed mechanics remain in this reference and `context/knowledge-governance.md`.
2. Do not restart merely to load SOUL. Prove cutover with a fresh local `hermes -p zeus chat -Q --source tool -q ...` session that asks for an existing section rule without supplying its answer.
3. Verify the fresh session in `state.db` read-only. The current schema keys `sessions` by `id`, not `session_id`; require the exact distinctive policy sentence once in `sessions.system_prompt`. A successful model answer alone is not sufficient proof.
4. Keep current-session semantics separate: Rodolfo's explicit current instruction governs immediately, while the new SOUL is guaranteed only for newly constructed sessions.
5. Add source-backed business regression cases with `required_all` and `forbidden_any`. Tests must fail before implementation, cover PASS and missing-term failure, and run against real canonical files in production.
6. When a regression fails, distinguish source drift from an over-literal fixture. Read the canonical wording; correct the case only when the same intended invariant is present. Never weaken a gate merely to turn it green.
7. Register the approved pilot decision and regression capability, update the initiative checkpoint, and keep Atena/Ares outside scope until their own gates.
8. Reconcile automatic skill writes and unrelated concurrent agent writes before closure. Verify live/mirror equality and exact REPORT-INFRA readback. If auto-commit bundles an attributed concurrent write with the pilot, disclose that path and its separate report instead of claiming the whole commit as Zeus-only.
9. Final proof should include: full suite PASS, business regressions PASS, registry/checkpoint/inbox counts, SOUL live=mirror, fresh-session prompt marker, inventory hits, secret scan, services active, Git synchronized, audit, and exact REPORT readback.

## Common pitfalls

1. **Memory-size solution** — increasing USER/MEMORY indefinitely creates prompt bloat and still lacks provenance/supersession.
2. **Canonical-source fallacy** — a fact in a routed reference is not always-active; classify residency before compacting memory.
3. **Foundation called active ingestion** — files and tests can be complete while agent behavior remains unchanged.
4. **Local backup called disaster recovery** — exclusions of sessions, memories, or databases and absence of restore drill leave a real gap.
5. **Stale plan becomes agent truth** — reconcile current agent-map/runtime before updating old restructuring plans.
6. **Dead-letter cleanup by deletion** — semantic recovery does not authorize deleting the pending file; preserve it or obtain the Critical Subset confirmation.
7. **Technical report to a nontechnical owner** — lead with the practical outcome, then state what is active, what is not active, and the one next gate.
