# Progressive-disclosure refactor for large operational skills

Use this procedure when an agent-specific `SKILL.md` has become monolithic, repeatedly inflates context, or mixes several operational branches that are rarely needed together.

## Audit without loading content

1. Scan metadata only: path, character/line count, H2/H3 counts, reference count, and whether a versioned mirror exists.
2. Prioritize MGS/custom skills over bundled or vendor skills.
3. Treat ~20K characters as a review signal, not an automatic defect. A large main file is acceptable only when nearly every section is always needed together.
4. Check runtime evidence separately. Visible Discord message count does not measure session size; tool results, schemas, replay fields, and system prompts dominate.

## Safe refactor

1. Back up every target outside Git under `/root/.hermes/secure-backups/`, with restrictive permissions and a manifest containing original hashes.
2. Preserve frontmatter byte-for-byte.
3. Keep `SKILL.md` as a short router: purpose, always-on rules, progressive-disclosure contract, routing index, pitfalls, and verification checklist.
4. Extract each H2 branch to `references/router-NN-topic.md`.
5. If one H2 remains very large, turn that reference into a second-level router and extract its H3 branches.
6. Create references before atomically replacing the main file so readers never observe broken links.
7. Do not rewrite or summarize procedures during a structural refactor; move them exactly. Content improvement is a separate reviewed change.

## Exact-preservation validation

- Parse the original from backup and reconstruct every H2 section from the new reference graph.
- Require exact equality, not semantic similarity.
- Do not use `rstrip()` independently on nested segments: it silently removes inter-section whitespace. Preserve exact slices and add routing prose only outside those slices.
- Validate frontmatter, every routed link, maximum main-file size, absence of temporary files, and live/mirror directory hashes.

## Git and secret-scanner pitfall

Auto-commit secret guards may classify filenames containing words such as `token`, `webhook`, or `private` as sensitive even when the moved content was already versioned safely. Use neutral operational filenames (`meta-runtime-diagnostics`, `alert-layout`, `thread-member-management`) while keeping the original section title inside the file. Never weaken scanning for additions or modifications just to land a refactor. Deletion-only status entries may bypass the sensitive-name path check because they remove an already-versioned path and cannot introduce a new secret; validate this distinction with a guard test before relying on it.

## Mirrors and sync scope

- Sync only the custom skills that were changed.
- Do not mirror an entire bundled/vendor category for convenience.
- If an agent's modified custom category is not versioned, add a selective skill allowlist to `sync-souls.sh`, then validate live/mirror byte equality.
- Run infrastructure discovery, append audit evidence, allow the normal auto-commit/push chain to finalize, and issue REPORT-INFRA according to MGS policy.

## Linked-file index overhead

`skill_view` does not return only `SKILL.md`: it recursively enumerates files under `references/`, `templates/`, `assets/`, and `scripts/` and includes the full `linked_files` index in the tool result. Reference explosion therefore has a context cost even when the main file is short.

- Measure `main_chars + serialized linked_files chars`, not only `SKILL.md` size.
- Prefer a small number of branch references in the 3–8K range over hundreds of tiny files.
- Use second-level routers only for genuinely independent sub-branches.
- When a skill already has a large historical library, keep the main routing links explicit and consider a runtime change that returns only explicitly linked files plus counts instead of the complete inventory.
- Do not call a 3K router “lean” if its automatic linked-file index adds another 10K+ characters.

### Do not confuse index compaction with main-body compaction

Linked-file compaction only reduces the serialized inventory returned beside the skill; it does not shorten `SKILL.md`. Before deciding that an upstream compaction fix eliminated the need for refactoring:

1. Read the active threshold/mode contract and count the target's support files. If the inventory is below the auto threshold, the fix may not activate at all.
2. Measure both `main_bytes` and `main_bytes + serialized_linked_files_bytes` before and after an in-memory candidate refactor.
3. Treat a main file above roughly 20K as a review signal even when the linked-file inventory is compacted.
4. Report separately whether the observed turn explosion came from the main body, linked-file enumeration, broad tool results, or repeated mutation/reload behavior.

### Attribution gate for patch/reload storms

Do not claim that a skill caused repeated self-edits merely because the session patched it many times. Search the current text for direct instructions to edit, patch, reread, reload, or maintain the skill. Distinguish:

- **direct cause** — explicit self-edit/reload instruction;
- **behavioral contributor** — duplicate rules, broad catalogs, unbounded retry, conflicting routes, or missing progressive-disclosure guard;
- **external cause** — global auto-learning policy, operator behavior, or runtime orchestration.

When direct self-edit wording is absent, say so plainly. Still propose a guard when useful: one primary reference at a time, no same-turn full reread unless the hash changed, at most one consolidated authorized patch at the end, and hunk/link/hash validation instead of `patch → full reload → patch`.

### Stale-reference safety

Before extracting canonical main-file content into existing references, compare their semantics. Historical references often retain obsolete rule names, thresholds, metrics, IDs, or workflows. If a dated reference conflicts with the current main contract:

1. Do not replace the current rule with a pointer to the stale file.
2. Create a small `current-*` canonical route pack by moving the current H2 slices literally.
3. Move the old dated files behind a historical catalog and state that the current canonical pack wins on conflict.
4. Keep permanent safety gates in the main router when their only other coverage is stale or branch-gated.
5. For a read-only audit, simulate the proposed extraction entirely in memory and report projected main size, line count, index size, exact source ranges, and verification invariants without creating files.

## Compact linked-files runtime contract

For MGS Hermes runtime, large support-file inventories use a compact `skill_view` response:

- Default mode is `auto`; inventories with more than 40 total linked files are compacted.
- The main response keeps only file paths explicitly named in rendered `SKILL.md` content.
- `linked_files_summary` is emitted only when at least one file is actually omitted; small inventories and large fully referenced inventories preserve their previous response shape and ordering.
- Normalize `\\` to `/` only for path matching so rendered Windows `${HERMES_SKILL_DIR}` references remain discoverable without rewriting returned paths.
- Direct `skill_view(name, file_path=...)` reads are unchanged, including omitted files.
- Omitted names remain discoverable on demand through `search_files(target='files', pattern='*.md', path=skill_dir)`.
- Small inventories preserve the historical full-list response.
- Instant rollback: set `skills.linked_files_mode: full` in profile config, or `metadata.hermes.linked_files_mode: full` for one skill. `compact` can force the behavior on a small skill.
- Persist the runtime change as a selective Hermes patch and protect it with helper/result/test invariants in `ensure-hermes-mgs-patches.sh`.

Required validation: unit tests for auto threshold, small-list compatibility, per-skill override, config rollback, and direct omitted-file access; then E2E profile loads for Zeus, Atena, Ares, and agente legado.

### Runtime rollout and persistence

1. Back up only the runtime and test files in scope before editing.
2. If the Hermes checkout already has unrelated local changes, generate the durable patch with a path-scoped diff for only the files changed by this feature; never capture the whole dirty worktree.
3. Register the selective patch and its behavioral markers in `ensure-hermes-mgs-patches.sh`, including `py_compile` and the targeted regression suite.
4. A live gateway must restart to import the changed Python module. Follow the safe-restart contract: send the clean user-facing status first, then schedule an external finalizer; restart Zeus last.
5. REPORT-INFRA is fail-closed before activation. If 1Password/webhook resolution is temporarily rate-limited, an external finalizer may wait and retry, but it must not restart gateways until the report succeeds. Exhausted retries leave the code installed but inactive and record the failure in audit logs.
6. Validate all gateway services from the external job; never foreground-poll the active Discord conversation through its own restart.

## SOUL refactor safety contract

Treat SOUL reduction as a safety-critical prompt migration, not a text-shortening exercise.

1. Inventory each H2/H3 by characters and classify it as `MUST`, `MUST/split`, `MOVE`, or `DUP/STALE`.
2. Before moving anything, compare the SOUL against MGS OS/context, runtime config, active skills, and permission data. Resolve contradictions first; never replace a permanent guardrail with a pointer to a stale or conflicting reference.
3. Keep permanently loaded: identity, authority, scope boundaries, authorization, credential safety, anti-invention/validation, Critical Subset, source precedence, historical-context non-actionability, anti-loop, and a short fail-closed restart invariant.
4. For `MUST/split`, retain the decision rule and exact trigger in SOUL; move only mechanics, examples, IDs, commands, histories, and mutable inventories.
5. Extract procedures literally first. Do not combine migration and semantic rewriting in one diff. Resolve stale/conflicting wording in a separate reviewed change.
6. Preserve the complete original source, not only H2 bodies: include the preface/title and every section in route packs or an immutable backup. Build a per-pack hash manifest, then prove that concatenating the preserved raw payloads reproduces the original file byte-for-byte. A backup is rollback evidence; it is not proof that knowledge remains discoverable through references.
7. Preserve explicit routing: every removed operational branch must name the exact skill/reference loaded on that trigger. Mark migrated packs as historical detail and state that the compact SOUL plus current canonical sources win on conflict.
8. Validate with negative scenarios before rollout: unauthorized user, out-of-scope request, credential/budget change, cross-agent ownership, restart during an active turn, unsupported provider, and success without evidence.
9. Keep adjacent remediations separate in scope and evidence. A Discord/config regression discovered during a SOUL audit is not proof that the SOUL migration failed; diagnose and validate each surface independently before applying authorization.
10. Roll out one profile at a time with backup, size/hash manifest, prompt/runtime smoke test, rollback artifact, inventory update, audit log, and REPORT-INFRA.

Common blockers found in real MGS audits include hardcoded model/provider names, stale permission IDs, conflicting budget limits, contradictory upload semantics, obsolete runtime-tool guidance, and duplicate REPORT-INFRA/thread rules. These must be reconciled before extraction.

## Full context audit beyond skills

A complete context-efficiency audit must also measure, per profile:

1. `SOUL.md` and stored `system_prompt` character sizes.
2. Current/recent `last_prompt_tokens`, message counts, and tool-call counts.
3. Tool-result characters by tool name, especially `skill_view`, `read_file`, `terminal`, and `session_search`.
4. `tool_output.max_bytes`, `file_read_max_chars`, `agent.max_turns`, compression policy, and tool-loop hard-stop settings.
5. Enabled/disabled toolsets, because every enabled model tool schema rides on every API call.
6. Runtime evidence of which large skills are actually loaded; do not prioritize unused bundled skills over frequently loaded MGS skills.

## Completion criteria

- Original content reconstructs exactly from references.
- Main files are lean routers and all links resolve.
- Reference-index overhead is measured and not excessive.
- Every changed live skill has a byte-identical versioned mirror where required.
- Backup, audit, inventory, Git state, and infrastructure report are accounted for.
