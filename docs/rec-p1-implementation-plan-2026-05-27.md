# REC/P1 Implementation Plan — GB-CC-EN Refactor

Date: 2026-05-27
Owner: Zeus
Status: implementation plan only, not executed
Depends on: docs/rec-p1-architecture-target-2026-05-27.md
Scope: REC, P1, REC+P1 production architecture for GB credit-card content

## 1. Objective

Implement the approved target architecture without rebuilding the entire system from zero:

- Keep the business operation simple: one REC+P1 request produces both articles.
- Separate REC and P1 technically during generation/validation.
- Remove editorial cache from content production.
- Consolidate active editorial rules into one GB-CC-EN contract.
- Reduce Atena's active instruction surface.
- Keep references as historical material only.
- Add explicit QA and validation boundaries.

## 2. Non-goals

- Do not implement SEO article generation in this phase.
- Do not delete historical references permanently.
- Do not remove technical WordPress cache.
- Do not change credential handling.
- Do not change Discord authorization model.
- Do not rewrite all runners from scratch.
- Do not create a single mega prompt that generates REC and P1 together.

## 3. Files to create

| File | Purpose | Priority |
|---|---|---:|
| `skills/content-generate-rec-p1/contracts/gb-cc-en.md` | Active editorial contract for GB credit-card REC/P1 | P0 |
| `scripts/mgs-rec-p1-orchestrator.py` | Coordinates REC runner + P1 runner as one operation | P1 |
| `scripts/qa-content-validator.py` | Semantic/editorial QA checks beyond current hard gates | P1 |
| `docs/rec-p1-refactor-test-report-YYYY-MM-DD.md` | Benchmark results after implementation | P2 |

## 4. Files to edit

| File | Change | Priority |
|---|---|---:|
| `skills/content-generate-rec-p1/SKILL.md` | Reduce to routing/how-to; remove active editorial sprawl and cache instructions | P0 |
| `scripts/mgs-rec-runner.py` | Remove editorial card-cache lookup/save from production path; load/apply contract; preserve technical gates | P0 |
| `scripts/mgs-p1-runner.py` | Remove editorial card-cache lookup; avoid REC prose as editorial input; load/apply contract | P0 |
| `scripts/rec-fingerprint.py` | Redesign scope or add modes for cross-card REC and P1 checks | P1 |
| `skills/content-generate-rec-p1/templates/rec-gb-cc-en.md` | Mark as derived/legacy or align with contract | P1 |
| `skills/content-generate-rec-p1/templates/p1-gb-cc-en.md` | Mark as derived/legacy or align with contract | P1 |

## 5. Files/directories to archive or demote

Do not delete permanently in the first pass. Move or mark as historical after implementation plan approval.

| Path | Action | Reason |
|---|---|---|
| `skills/content-generate-rec-p1/references/*.md` | Move to `references/archive/` or add clear historical header | Prevent active-rule confusion |
| `skills/content-generate-rec-p1/scripts/card-cache-lookup.sh` | Keep for audit/debug only or move to archive | Must not influence production content |
| `skills/content-generate-rec-p1/scripts/card-cache-save.sh` | Keep for audit/debug only or move to archive | Stop saving editorial facts |
| `skills/content-generate-rec-p1/scripts/card-cache-stats.sh` | Keep for audit/debug only or move to archive | No longer production-relevant |
| `data/card-cache.db` | Keep as historical/debug initially; do not query in production | Avoid destructive deletion; remove runtime authority |

## 6. Editorial cache removal plan

### 6.1 REC runner

Current active cache paths:

- `CACHE_DB = ROOT / "data/card-cache.db"`
- `cache_lookup(card_slug)`
- lookup around current `card_cache_lookup_sec`
- `cache_hit` step
- `cache_saved` step
- `card-cache-save.sh` invocation

Target:

- Do not call `cache_lookup()` for content data.
- Do not read benefits, APR, annual fee, descriptor, tag, URL, or image from `card-cache.db`.
- Do not call `card-cache-save.sh` after publish.
- If cache code remains temporarily, mark it unused/deprecated and unreachable from production flow.
- Keep WordPress term cache untouched.

### 6.2 P1 runner

Current active cache paths:

- `CACHE_DB = ROOT / "data/card-cache.db"`
- `cache_lookup(card_slug)`
- lookup around current cache merge stage

Target:

- Do not call `cache_lookup()` for P1 content data.
- P1 must fetch current official facts or receive explicit request parameters.
- P1 may receive allowed REC metadata only: `card_name`, `card_slug`, `rec_post_id`, `rec_url`, `official_url`, validated card image id/url.
- P1 must not inherit REC descriptor/tag/prose by default.

## 7. Contract implementation

Create:

```text
skills/content-generate-rec-p1/contracts/gb-cc-en.md
```

Minimum sections:

1. Common rules
2. REC rules
3. P1 rules
4. REC+P1 orchestration
5. Hard gates
6. Semantic validators
7. Warnings
8. Manual QA boundaries
9. No editorial cache policy
10. Reporting requirements

Runtime expectation:

- Runners should load this contract or embed a generated prompt derived from it.
- Atena should treat this contract as the only active editorial source of truth for GB credit-card REC/P1.
- References are historical unless explicitly promoted into the contract.

## 8. SKILL.md reduction plan

Current issue:

- `content-generate-rec/SKILL.md` is too large and contains operational instructions, historical lessons, cache rules, references, and report details.

Target `SKILL.md` responsibilities:

- Identify request type: REC, P1, REC+P1.
- Tell Atena which runner/orchestrator to call.
- State that editorial rules live in `contracts/gb-cc-en.md`.
- State that references are historical only.
- State that card-cache is not allowed for content production.
- State reporting format.

Remove/demote from active body:

- detailed old incident lessons;
- card-cache lookup/save instructions;
- long reference list as mandatory reading;
- stale runner workarounds;
- duplicate editorial rules now covered by contract.

## 9. REC+P1 orchestrator design

Create:

```text
scripts/mgs-rec-p1-orchestrator.py
```

Responsibilities:

1. Parse request parameters: site, card, official URL, language/vertical, dry-run/update flags.
2. Run `mgs-rec-runner.py`.
3. Parse REC runner JSON output.
4. Extract only allowed metadata.
5. Run `mgs-p1-runner.py` with independent generation context.
6. Validate links: REC → P1 and P1 → official bank.
7. Run combined QA report.
8. Emit a single summary JSON for Atena to report.

Non-responsibilities:

- Do not generate article prose.
- Do not build a combined REC+P1 prompt.
- Do not pass REC paragraphs to P1.
- Do not query editorial card-cache.

Allowed REC → P1 handoff:

| Field | Allowed |
|---|---:|
| card_name | Yes |
| card_slug | Yes |
| rec_post_id | Yes |
| rec_url | Yes |
| official_url | Yes |
| card_image_id/url | Yes, if validated |
| REC paragraphs/opening/body | No |
| REC descriptor/tag/benefit prose | No by default |
| card-cache data | No |

## 10. QA validator design

Create:

```text
scripts/qa-content-validator.py
```

Initial checks:

| Check | REC | P1 | Outcome |
|---|---:|---:|---|
| Placeholder phrases | Yes | Yes | hard gate |
| Invalid table columns | Yes | optional | hard gate |
| Card image aspect/card-only evidence | Yes | Yes | hard gate |
| Missing official URL | Yes | Yes | hard gate |
| Subtitle/title length | Yes | Yes | hard gate |
| Generic opening phrases | Yes | Yes | semantic block/regenerate |
| Repeated opening vs recent posts | Yes | Yes | semantic block/regenerate |
| Near-duplicate body vs recent posts | Yes | Yes | semantic block/regenerate |
| REC tone too informational | Yes | No | semantic warning/block |
| P1 tone too REC-like | No | Yes | semantic warning/block |
| Missing card-specific benefits | Yes | Yes | semantic block |

Implementation options:

- Phase 1: deterministic regex/text heuristics.
- Phase 2: fingerprint/Jaccard by sections.
- Phase 3: embedding/LLM judge only if needed.

## 11. Fingerprint redesign plan

Current limitation:

- `rec-fingerprint.py` compares the same `card_slug` across different sites.
- It does not compare different cards on the same site.
- It does not cover P1.
- WARN does not necessarily block.

Target:

1. Add content type: REC/P1.
2. Store section-level fingerprints: intro, body, conclusion, metadata.
3. Compare same-card across sites separately from cross-card generic similarity.
4. Compare recent N posts in same vertical/site.
5. Support hard fail threshold and warning threshold.
6. Include comparisons in final report.

## 12. Test plan

Benchmark cards:

1. Amazon Barclaycard
2. Royal Bank Credit Card
3. Santander World Elite Mastercard

Test modes:

| Mode | Purpose |
|---|---|
| dry-run REC | validate REC contract/cache removal |
| dry-run P1 | validate P1 independence |
| dry-run REC+P1 | validate orchestrator handoff |
| publish/update controlled article | validate WordPress integration |

Acceptance criteria:

- No editorial card-cache lookup in logs/timings/steps.
- REC and P1 both use current official source.
- REC remains short recommender.
- P1 remains detailed complement, not stretched REC.
- P1 receives no REC paragraphs.
- Table columns valid.
- No placeholders.
- Card image valid/horizontal/card-only.
- Links valid: REC → P1 → official bank.
- Final report includes validation evidence and total elapsed time.

## 13. Rollback plan

Before code changes:

- Ensure git working tree is clean or commit this plan/docs first.
- Create a branch or checkpoint commit.

Rollback method:

```bash
git -C /root/mgs-agent status
git -C /root/mgs-agent diff
git -C /root/mgs-agent restore <file>
```

For production safety:

- Do not delete `card-cache.db` in first implementation.
- Only remove runner references to it.
- Keep archive copies of SKILL.md/references.
- Test in dry-run before publishing.

## 14. Execution order

Recommended safe order:

1. Commit architecture docs.
2. Create `contracts/gb-cc-en.md`.
3. Reduce `SKILL.md` to routing-only with explicit contract pointer.
4. Add no-cache policy to contract and skill.
5. Remove editorial cache lookup/save from REC runner.
6. Remove editorial cache lookup from P1 runner.
7. Verify existing REC and P1 dry-runs independently.
8. Create REC+P1 orchestrator.
9. Add QA validator v1.
10. Add P1/cross-card fingerprinting or extend existing script.
11. Run benchmark dry-runs.
12. Publish/update one controlled benchmark pair.
13. Review with Rodolfo/Raquel.
14. Enable normal REC+P1 operation.

## 15. Approval checkpoints

Rodolfo approval required before each group:

| Checkpoint | Scope |
|---|---|
| A | Create contract + reduce skill |
| B | Remove editorial cache from runners |
| C | Add orchestrator |
| D | Add QA validator/fingerprint changes |
| E | Run benchmark publishes |

## 16. Open decisions

1. Should templates remain as separate files or be fully absorbed into the contract?
2. Should old references be physically moved to `archive/` or only marked with headers?
3. Should initial semantic validator block publish or generate warnings only?
4. Should card images ever be reused automatically if already validated?
5. Should P1 always fetch official source independently, even if REC just fetched it seconds earlier?

Recommended defaults:

1. Keep templates initially, but mark contract as authority.
2. Move references into archive after contract is complete.
3. Start semantic validator as blocking for obvious generic/repeated openings.
4. Do not reuse card images automatically without validation evidence.
5. Yes, P1 should fetch official source independently to avoid REC contamination.
