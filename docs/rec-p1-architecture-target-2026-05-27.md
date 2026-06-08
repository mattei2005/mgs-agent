# REC/P1 Architecture Target — GB-CC-EN

Date: 2026-05-27
Owner: Zeus
Status: target architecture proposal, not yet implemented
Scope: REC, P1, REC+P1 for GB credit-card content

## 1. Problem

The current REC/P1 production flow has accumulated too many active-looking instruction layers:

- Atena SOUL.md
- MGS AGENT.md
- Discord channel prompt
- content-generate-rec/SKILL.md
- REC template
- P1 template
- 50+ reference markdown files
- REC runner
- P1 runner
- helper scripts
- card-cache.db
- wp-term-cache.json
- rec-fingerprints.db
- current thread context

The operational issue is not only volume. The main issue is ambiguous authority: Atena may update or read a markdown reference, while production output is actually controlled by Python runners and cached data. This creates recurring failures where the current article is repaired, but the next card can repeat old mistakes.

## 2. Architecture decisions

1. Do not rebuild everything from zero.
2. Do not create a mega REC+P1 prompt.
3. REC and P1 remain separate editorial products.
4. REC+P1 is orchestration, not a third article type.
5. GB-CC-EN gets one active editorial contract.
6. Reference markdown files become historical archive, not active production rules.
7. Editorial card cache is removed from production content generation.
8. Technical caches may remain when they do not influence article content.
9. Hard gates, semantic validators, warnings, and manual QA must be explicitly separated.
10. Atena implements and operates; Zeus audits architecture and production safety.

## 3. Authority model

| Layer | New role | Production authority |
|---|---|---|
| Atena SOUL.md | Agent behavior/persona | No editorial rule authority |
| MGS AGENT.md | Governance, authorization, safety | Global authority only |
| Discord channel prompt | Thread behavior and operating shortcuts | Operational authority only |
| content-generate-rec/SKILL.md | Short routing/how-to guide | Operational routing only |
| contracts/gb-cc-en.md | Active editorial source of truth | Yes |
| templates/rec-gb-cc-en.md | Optional derived REC structure | Secondary to contract |
| templates/p1-gb-cc-en.md | Optional derived P1 structure | Secondary to contract |
| references/archive/ | Historical lessons and incidents | No active authority |
| mgs-rec-runner.py | Runtime REC execution and gates | Yes |
| mgs-p1-runner.py | Runtime P1 execution and gates | Yes |
| qa-content-validator.py | Editorial/semantic QA before publish/report | Yes |
| card-cache.db | Historical/debug only | No content authority |
| wp-term-cache.json | WordPress taxonomy cache | Technical only |
| rec-fingerprints.db | QA history/similarity evidence | QA only, not content source |
| current thread | Request-specific instruction | Applies only to current task |

## 4. Target file structure

```text
/root/mgs-agent/
├── AGENT.md
├── docs/
│   └── rec-p1-architecture-target-2026-05-27.md
├── data/
│   ├── sites.json
│   ├── wp-term-cache.json
│   ├── rec-fingerprints.db
│   └── card-cache.db                    # not used for editorial production
├── skills/
│   └── content-generate-rec/
│       ├── SKILL.md                     # short routing guide
│       ├── contracts/
│       │   └── gb-cc-en.md              # active editorial contract
│       ├── templates/
│       │   ├── rec-gb-cc-en.md          # optional derived/legacy support
│       │   └── p1-gb-cc-en.md           # optional derived/legacy support
│       ├── references/
│       │   └── archive/                 # historical only
│       └── scripts/
│           ├── generate-featured-image.sh
│           ├── search-card-image.sh
│           ├── validate-article.sh
│           └── yoast-score-post.sh
└── scripts/
    ├── mgs-rec-runner.py
    ├── mgs-p1-runner.py
    ├── mgs-rec-p1-orchestrator.py       # proposed
    ├── qa-content-validator.py          # proposed
    └── rec-fingerprint.py               # redesign target
```

## 5. No editorial cache policy

Editorial cache must not be used to generate production content.

### Remove from content flow

| Item | Decision | Reason |
|---|---|---|
| card-cache.db text/facts | Remove from REC/P1 generation | Can reuse stale or wrong facts |
| cached benefits/rewards | Remove | Must come from current official source |
| cached APR/annual fee | Remove as content source | Financial terms change |
| cached descriptor/tag/headline | Remove | Causes repeated positioning mistakes |
| cached card image | Not automatic | Must be validated per run or explicitly approved |
| card-cache-lookup.sh | Remove from main flow | Encourages stale data reuse |
| card-cache-save.sh | Stop saving editorial facts | Perpetuates mistakes |
| card-cache-stats.sh | Historical/debug only | Not needed for production content |

### Keep only technical/non-editorial data

| Item | Decision | Reason |
|---|---|---|
| sites.json | Keep | Site config |
| wp-term-cache.json | Keep | Category/tag IDs only |
| rec-fingerprints.db | Keep/redesign | QA history, not content source |
| logs | Keep | Auditability |
| credentials/config resolution | Keep | Technical execution only |

For multi-site scale, each site article should generate fresh editorial copy from the official source, not from previously cached article decisions.

## 6. GB-CC-EN contract outline

Target path:

```text
/root/mgs-agent/skills/content-generate-rec-p1/contracts/gb-cc-en.md
```

### 6.1 Common rules

- Vertical: UK credit cards.
- Use current official issuer page as the source of truth.
- Do not invent benefits, fees, APR, eligibility, bonuses, or application terms.
- Do not use editorial card cache.
- Do not use placeholders such as `Check issuer terms`.
- Do not use generic copy that can apply to any card.
- Card image must be card-only and horizontal unless explicitly approved.
- Tables must use approved columns only.
- Output must preserve REC and P1 as distinct editorial products.

### 6.2 REC contract

REC is the short recommender.

Purpose:

- Spark interest.
- Highlight strongest benefits.
- Use light commercial/recommendation tone.
- Route reader to P1.

REC must not:

- Become a long explainer.
- Use generic finance filler.
- Use placeholders.
- Copy from another card article.
- Depend on card-cache editorial data.

### 6.3 P1 contract

P1 is the longer complementary page.

Purpose:

- Explain the card in more detail.
- Help the reader decide whether to continue to the official bank page.
- Expand on facts from the official source, not on REC prose.
- Route reader to official issuer/bank page.

P1 must not:

- Be a stretched REC.
- Copy REC paragraphs.
- Reuse REC opening/benefit prose.
- Depend on REC text as editorial input.
- Depend on card-cache editorial data.

### 6.4 REC+P1 orchestration contract

REC+P1 is not a new article template.

It is:

```text
REC runner → validated REC → metadata handoff → P1 runner → validated P1 → combined report
```

Allowed metadata from REC to P1:

| Field | Allowed? | Notes |
|---|---:|---|
| card_name | Yes | Technical identity |
| card_slug | Yes | Technical identity |
| rec_post_id | Yes | Linking |
| rec_url | Yes | Linking |
| official_url | Yes | Source reference |
| card_image_id/url | Yes, if validated | Technical reuse only |
| REC paragraphs | No | Prevent editorial contamination |
| REC opening | No | Prevent repetition |
| REC benefit prose | No | Prevent P1 becoming expanded REC |
| REC descriptor/tag | No by default | Generate independently or validate explicitly |
| card-cache facts | No | Cache is not source of truth |

## 7. Target REC flow

```text
Request REC
→ load gb-cc-en contract REC section
→ fetch official source
→ extract current official facts
→ generate REC
→ run hard gates
→ run semantic QA
→ publish/update WordPress
→ validate public URL
→ store fingerprint/QA evidence
→ final report
```

No editorial card-cache lookup.

## 8. Target P1 flow

```text
Request P1
→ load gb-cc-en contract P1 section
→ fetch official source
→ extract current official facts
→ use only allowed metadata if linked to REC
→ generate P1 independently
→ run hard gates
→ run semantic QA
→ publish/update WordPress
→ validate public URL
→ final report
```

P1 must be editorially independent even when linked to REC.

## 9. Target REC+P1 flow

```text
Request REC+P1
→ orchestrator parses card/site/source
→ run REC flow
→ collect allowed metadata only
→ run P1 flow in separate execution context
→ validate REC → P1 link
→ validate P1 → official bank link
→ run combined QA summary
→ final report with both URLs and validation evidence
```

The orchestrator must not generate article prose. It coordinates runners and validation only.

## 10. Validation taxonomy

| Type | Examples | Outcome |
|---|---|---|
| Hard gate | Placeholder, invalid card image, wrong table columns, missing official URL, missing card image, bad public verify | Abort or block publish |
| Semantic validator | Generic intro, repeated opening, near-duplicate body, REC/P1 tone bleed, missing card-specific benefits | Regenerate or block pending review |
| Warning | Minor Yoast/readability margin, non-critical metadata gap, slow external source | Report clearly |
| Manual QA | Final editorial judgment from Raquel/Rodolfo | Human decision |

## 11. Fingerprint redesign target

Current `rec-fingerprint.py` is useful but insufficient for the observed issue.

Target behavior:

- Compare REC against recent RECs from the same vertical, not only same card across sites.
- Add P1 fingerprinting.
- Compare openings separately.
- Compare recurring phrases/templates.
- Track same-card multi-site similarity separately from cross-card generic similarity.
- Make high-risk similarity a blocker or regeneration trigger, not only a warning.

## 12. Migration plan

### Phase 1 — Plan and approve

- Approve this target architecture.
- Identify exact files to create, edit, archive, or leave untouched.
- Confirm that card-cache is removed from editorial production.

### Phase 2 — Create source of truth

- Create `contracts/gb-cc-en.md`.
- Reduce `SKILL.md` to routing/operation only.
- Mark references as historical.

### Phase 3 — Remove editorial cache from runners

- Remove `card-cache.db` lookup from REC content generation.
- Remove `card-cache.db` lookup from P1 content generation.
- Stop saving editorial facts to card-cache after publish.
- Keep wp-term-cache and QA fingerprints.

### Phase 4 — Build orchestrator

- Add `mgs-rec-p1-orchestrator.py`.
- Ensure REC+P1 is coordinated execution, not a new prompt mode.
- Pass only allowed metadata to P1.

### Phase 5 — QA layer

- Add or redesign semantic QA validator.
- Add P1 fingerprinting.
- Add cross-card generic-copy detection.

### Phase 6 — Benchmark

Run three benchmark REC+P1 jobs before normal production:

1. Amazon Barclaycard
2. Royal Bank Credit Card
3. Santander World Elite Mastercard

Evaluate:

- REC identity preserved.
- P1 identity preserved.
- No cache editorial use.
- No repeated openings.
- No generic benefit prose.
- Card image valid.
- Table valid.
- Links valid.
- Final report includes evidence.

## 13. Non-goals

- SEO articles are out of scope for this refactor.
- This document does not authorize production code changes by itself.
- This document does not delete historical references.
- This document does not remove databases yet.

## 14. Approval checkpoint

Before implementation, Rodolfo must approve:

1. Contract file creation.
2. SKILL.md reduction scope.
3. Reference archive policy.
4. Editorial cache removal from REC/P1 runners.
5. REC+P1 orchestrator design.
6. QA validator scope.
