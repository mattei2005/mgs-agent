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
- Before patching another profile's SOUL, run a read-only inference/auth preflight for that exact profile. Inspect access expiry and refresh presence without printing values, and compare refresh-token equality internally across active profiles. A cloned refresh chain can pass an earlier smoke and later fail when single-use rotation collides.
- Token presence, refresh-chain independence, and a running gateway are necessary evidence but **not proof that OAuth is usable**: a profile can satisfy all three while its next real inference fails during refresh. Require a fresh minimal inference before creating the SOUL patch/backup set; classify the real inference result as the authentication gate.
- If the target profile cannot complete inference or shares a refresh chain, keep the continuity rollout unvalidated and stop at a separate credential Critical Subset gate. Do not patch SOUL merely because static auth checks passed. Back up `auth.json` only outside Git, prefer independent device-code reauthentication, and never borrow another profile's OAuth block as the durable fix.
- Post-change proof requires both a successful fresh-session answer and read-only `state.db` evidence that the distinctive continuity marker appears exactly once in the new session's `system_prompt`. An OAuth failure before session creation is not partial behavior validation merely because live/versioned SOUL hashes match.

### Phase 4 — Disaster recovery

- Add encrypted off-host backup for the approved repo/profile/session/database surface.
- Define RPO/RTO.
- Run an isolated restore drill.
- A local tar validation proves archive readability, not off-host durability or operational restoration.
- Do not use `hermes backup --quick --output <zip>` as an archive primitive: current Hermes `--quick` ignores the output path, creates a live `state-snapshots/` directory, and may prune older snapshots. For deterministic off-site packaging, enumerate the approved critical state surface and copy SQLite databases with the WAL-safe `sqlite3.backup()` API.
- Hermes cron script-only jobs accept a script filename relative to the active profile's `scripts/` directory, not an absolute `/root/mgs-agent/...` path. Keep the canonical implementation in MGS and use a small profile-local wrapper when scheduling it.
- During an isolated restore, `PRAGMA quick_check` can expose a malformed derived FTS5 index even when the source database is otherwise readable. Rebuild only the affected FTS virtual indexes in the isolated restored copy, rerun `quick_check`, and record that repair. Never mutate the live database or call the source healthy merely because the restored derived index was rebuilt.

#### Phase 4 preflight and authorization gate

Before creating backup artifacts, establish the recovery chain in this order:

1. Re-read the initiative checkpoint and inspect the live backup, profile, disk-usage, and external-destination state.
2. Validate that the destination is genuinely off-host and writable. For Google Drive automation, require Shared Drive metadata (`driveId`) plus the intended technical identity's write capability; folder visibility alone is not upload proof.
3. Use Hermes' native `hermes -p <profile> backup` for Hermes state when available. It snapshots SQLite through `sqlite3.backup()` and excludes live WAL/SHM sidecars; do not replace that consistency guarantee with a raw copy of a running `state.db`.
4. Inventory the encryption-recovery path before uploading anything: dedicated key existence, private-key custody in 1Password, and how a replacement VPS obtains the decryption material. Do not reuse an unrelated application secret as a backup password.
5. If a dedicated backup key must be created or changed, stop at the MGS Critical Subset gate. The confirmation must name key creation/custody, any automatic cleanup of temporary plaintext, and any retention deletion of expired backup snapshots. A general “continue the backup plan” authorization is not the additional critical confirmation.
6. Prefer a design in which the scheduled backup host needs only encryption capability while decryption custody remains external to the VPS. Never upload plaintext archives or leave recoverable plaintext staging behind.
7. Run the proof end to end: create consistent backup → encrypt → upload → read back remote metadata/hash → download → decrypt in an isolated location → validate archive and expected canonical files/databases. Import into a live profile is not a restore test and risks overwriting production; use an isolated restore target.
8. Only after the first restore drill passes should scheduling, retention, age monitoring, and last-approved-restore monitoring be called active.

Keep scope proportional. Exclude reproducible caches, package trees, browser caches, generated media, prior local backups, and large temporary/update proof directories unless a canonical source explicitly requires them. Include the state that cannot be reconstructed from Git or 1Password: institutional data, checkpoints, sessions, memories, profile configuration, and consistent database snapshots.

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

## Executive communication and pilot ownership

- When Rodolfo asks a binary activation question such as “precisa reiniciar?”, answer **yes or no in the first sentence**. Do not lead with routing internals, cached-prompt nuances, or adjacent work. Add one short qualification only if it changes the decision.
- A SOUL-only change does not require a gateway restart. Existing routed sessions retain their stored system prompt; restarting the gateway generally resumes that session rather than rebuilding it. New sessions load the updated SOUL. Therefore, do not recommend restart as a cutover mechanism unless a live runtime/config component actually requires it.
- Never assign Rodolfo the job of “observing the pilot” after validation. Zeus owns monitoring, regressions, checkpoints, and exception detection; Rodolfo receives only material failures, authority gates, or decisions.
- “Observe the pilot” in a plan or checkpoint means an internal Zeus duty. Write checkpoints explicitly as “Zeus monitors...” so they cannot be misread as user work.
- If Rodolfo says a parallel subject is being handled with another agent, acknowledge ownership and exclude it from Zeus execution. Reconcile concurrent writes internally for attribution, but do not turn that parallel subject into the answer to an unrelated question.
- Do not imply uncertainty merely because rollout is conservative. State whether the artifact is validated, identify the remaining risk separately, and recommend the next gate without asking Rodolfo to supervise normal operation.

## Common pitfalls

1. **Memory-size solution** — increasing USER/MEMORY indefinitely creates prompt bloat and still lacks provenance/supersession.
2. **Canonical-source fallacy** — a fact in a routed reference is not always-active; classify residency before compacting memory.
3. **Foundation called active ingestion** — files and tests can be complete while agent behavior remains unchanged.
4. **Local backup called disaster recovery** — exclusions of sessions, memories, or databases and absence of restore drill leave a real gap.
5. **Stale plan becomes agent truth** — reconcile current agent-map/runtime before updating old restructuring plans.
6. **Dead-letter cleanup by deletion** — semantic recovery does not authorize deleting the pending file; preserve it or obtain the Critical Subset confirmation.
7. **Technical report to a nontechnical owner** — lead with the practical outcome, then state what is active, what is not active, and the one next gate.
8. **Making the owner supervise a validated pilot** — internal monitoring is Zeus work; only exceptions and authority gates go to Rodolfo.
9. **Over-answering a binary activation question** — first answer the exact yes/no question; diagnostics belong after the decision and only when relevant.
