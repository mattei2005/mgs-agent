# REC/P1 Active Content Map — Before Refactor

Date: 2026-05-27
Owner: Zeus
Status: read-only audit artifact
Scope: active/near-active content sources that can influence Atena REC, P1 and REC+P1 production

## 1. Purpose

This document maps the current REC/P1 instruction surface before implementation.

Goal:

- Identify what Atena may read.
- Identify what the runners actually read/execute.
- Separate active authority from historical/reference material.
- Identify cache paths that currently influence content.
- Prevent premature edits to `SKILL.md`, templates, runners or cache before the authority model is clear.

## 2. Executive finding

The current flow has too many active-looking sources. The largest ambiguity is that many markdown files look like production rules, while the real runtime behavior is controlled by Python runners and helper scripts.

The biggest production risk is `card-cache.db`: both REC and P1 runners currently consult it, and REC saves editorial data back into it after publication. This means stale/wrong card facts can become part of future content generation unless explicitly removed from the flow.

## 3. Current active/near-active file inventory

| Component | Path | Size / count | Current role | Runtime authority |
|---|---|---:|---|---|
| Atena SOUL | `/root/.hermes/profiles/atena/SOUL.md` | 38 KB | Agent behavior/persona/rules | Partial behavioral authority |
| Atena config/channel prompt | `/root/.hermes/profiles/atena/config.yaml` | 19 KB | Discord behavior, shortcuts, skill dirs, model | Operational authority |
| MGS AGENT | `/root/mgs-agent/AGENT.md` | 18 KB | Global governance and safety | Global authority |
| REC skill | `skills/content-generate-rec/SKILL.md` | 1,366 lines / 88 KB | Mixed routing, references, old workflows, cache rules, reporting | High Atena-context authority, not directly runner runtime |
| REC template | `skills/content-generate-rec/templates/rec-gb-cc-en.md` | 293 lines / 11 KB | REC editorial/SEO template | Read by REC runner |
| P1 template | `skills/content-generate-rec/templates/p1-gb-cc-en.md` | 369 lines / 15 KB | P1 editorial/SEO template | Not clearly read by P1 runner in current audited lines |
| References | `skills/content-generate-rec/references/*.md` | 54 files | Incident lessons / corrections / historical rules | Not read by runners by filename |
| REC runner | `scripts/mgs-rec-runner.py` | 1,749 lines / 85 KB | REC runtime and publication | Direct runtime authority |
| P1 runner | `scripts/mgs-p1-runner.py` | 943 lines / 53 KB | P1 runtime and publication | Direct runtime authority |
| Card cache scripts | `skills/content-generate-rec/scripts/card-cache-*.sh` | 3 scripts | Lookup/save/stats for card cache | Runtime helper authority when called |
| Other helper scripts | `skills/content-generate-rec/scripts/*` | 12 scripts total | Images, validation, Yoast, search | Runtime helper authority |
| Sites config | `data/sites.json` | small | Site config/template key/domain | Runtime authority |
| Card cache DB | `data/card-cache.db` | database | Cached card facts/editorial metadata | Runtime authority today, should be removed |
| WP term cache | `data/wp-term-cache.json` | data | Category/tag ID cache | Technical runtime authority only |
| REC fingerprints | `data/rec-fingerprints.db` | database | Similarity history | QA authority only |

## 4. Authority map

| Source | Atena may treat as active? | Runner reads/executes? | Target authority after refactor |
|---|---:|---:|---|
| SOUL.md | Yes | No | Behavior only |
| AGENT.md | Yes | No | Governance only |
| Discord channel prompt | Yes | No | Thread/runner shortcut only |
| `SKILL.md` | Yes | No | Short operational routing only |
| `templates/rec-gb-cc-en.md` | Yes | Yes, REC runner reads it | Derived from contract or secondary |
| `templates/p1-gb-cc-en.md` | Yes | Not clearly in current P1 runtime | Derived from contract or secondary |
| `references/*.md` | Yes, if loaded | No by filename | Historical/archive only |
| `mgs-rec-runner.py` | Optional to inspect | Yes | Runtime authority |
| `mgs-p1-runner.py` | Optional to inspect | Yes | Runtime authority |
| `card-cache.db` | No | Yes today | No production editorial authority |
| `wp-term-cache.json` | No | Yes | Technical only |
| current Discord thread | Yes | No | Current task only |

## 5. Current reading/execution order — REC

Observed runtime behavior from `scripts/mgs-rec-runner.py`:

1. Loads `data/sites.json`.
2. Resolves `template_key` and reads `skills/content-generate-rec/templates/rec-{template_key}.md`.
3. Defines/uses `CACHE_DB = data/card-cache.db`.
4. Calls `cache_lookup(card_slug)` early in execution.
5. Merges cached fields such as `card_official_url` when available.
6. Validates official source content.
7. Generates article locally through `generate_article_local(...)` using current `card_data`.
8. Validates HTML through `validate-article.sh`.
9. Handles card image search/normalization/upload.
10. Generates featured image.
11. Runs duplicate fingerprint check through `scripts/rec-fingerprint.py`.
12. Resolves taxonomy, using `wp-term-cache.json` for technical category/tag caching.
13. Creates/updates WordPress post and Yoast.
14. Saves a payload back into card cache through `card-cache-save.sh`.
15. Stores fingerprint.
16. Emits JSON summary.

Important cache evidence:

- `mgs-rec-runner.py` line 32: `CACHE_DB = ROOT / "data/card-cache.db"`
- line 111: `def cache_lookup(card_slug: str)`
- line 1213: `cache = cache_lookup(card_slug)`
- line 1214: timing `card_cache_lookup_sec`
- line 1218: `card_official_url` can come from cache
- line 1654: invokes `card-cache-save.sh`
- line 1656: step `cache_saved`

Target: remove card-cache lookup/save from production content generation.

## 6. Current reading/execution order — P1

Observed runtime behavior from `scripts/mgs-p1-runner.py`:

1. Loads `data/sites.json`.
2. Defines/uses `CACHE_DB = data/card-cache.db`.
3. Loads REC content via post ID or public URL.
4. Reads REC `content.raw` and `content.rendered`.
5. Parses LazyBlock and extracts card metadata.
6. Calls `cache_lookup(card_slug)`.
7. Uses `args.official_url or cache.get("card_official_url")`.
8. Fetches official source and extracts official data.
9. Preserves LazyBlock labels from REC (`tag10`, `tag2`, `descriptor`) when official extraction is generic.
10. Generates P1 body through deterministic Python composition.
11. Resolves taxonomy and publishes/updates WordPress.
12. Updates Yoast, verifies public URL, emits JSON.

Important coupling/cache evidence:

- `mgs-p1-runner.py` line 31: `CACHE_DB = ROOT / "data/card-cache.db"`
- line 140: `def cache_lookup(card_slug: str)`
- line 801: builds `public_html` from REC content raw/rendered
- lines 807-810: reads `rec_raw`, `rec_rendered`, then `parse_card_from_rec(...)`
- line 813: `cache = cache_lookup(card_slug)`
- line 814: official URL can come from cache
- lines 839-841: preserves `tag10`, `tag2`, `descriptor` from parsed REC

Target: P1 may use only minimal REC metadata and validated image/link data. It should not inherit REC prose, descriptor/tag by default, or card-cache editorial data.

## 7. `SKILL.md` findings

Current `content-generate-rec/SKILL.md` is too broad. It contains:

- a long session-learned references list;
- fast-runner default instructions;
- REC+P1 orchestration instructions;
- cache behavior and cache-miss discussions;
- image rules;
- WordPress/Yoast instructions;
- reporting format requirements;
- many historical incident references;
- old manual workflow sections.

Examples of conflicting or obsolete-for-target authority:

- It states that normal REC should not read long references first, but the file itself lists many references as session-learned context.
- It still references shared official facts/cache for multi-site same-card flow.
- It explains runner consolidation including cache lookup and cache save.
- It includes cache-miss operational paths that should not remain active if editorial cache is removed.

Target role: reduce `SKILL.md` to a short routing guide:

- identify REC / P1 / REC+P1 request;
- call the right runner/orchestrator;
- point to `contracts/gb-cc-en.md` as the active editorial contract;
- state references are historical;
- state no editorial card-cache for production content;
- define final reporting requirements.

## 8. Template findings

### REC template

Path: `skills/content-generate-rec/templates/rec-gb-cc-en.md`

Current role:

- read by REC runner through `load_template(template_key)`;
- contains REC editorial and SEO expectations;
- should remain active until contract migration is implemented.

Target:

- either keep as a derived REC-specific template subordinate to `contracts/gb-cc-en.md`, or absorb into the contract and make the runner use contract sections directly.

### P1 template

Path: `skills/content-generate-rec/templates/p1-gb-cc-en.md`

Current role:

- contains P1 structure, image rules and validation expectations;
- current audited P1 runner lines do not clearly show it being loaded like REC template is loaded;
- P1 runner appears to generate body mostly through deterministic Python composition in `generate_p1_body(...)`.

Target:

- align P1 template with `contracts/gb-cc-en.md`;
- make authority explicit: either runner reads it/contract, or it is historical/derived only.

## 9. References findings

Current count: 54 markdown files under `skills/content-generate-rec/references/`.

Recent references include multiple overlapping incident/rule files:

- `rec-p1-active-content-map-before-refactor.md`
- `rec-p1-architecture-cleanup-cache-policy.md`
- `rec-p1-structural-audit-playbook.md`
- `santander-rec-p1-specificity-and-operation-time-2026-05-27.md`
- `rec-p1-scale-quality-gates-2026-05-27.md`
- `rec-p1-card-image-competitor-descriptor-hard-gates-2026-05-26.md`
- `rec-p1-publish-sequential-orchestration-2026-05-26.md`
- `rec-p1-global-editorial-alignment-2026-05-26.md`
- `p1-official-source-and-card-image-hard-gates-2026-05-24.md`
- `p1-gb-cc-en-structure-and-test-2026-05-19.md`

Themes overlap heavily:

- cache;
- hard gates;
- REC+P1 orchestration;
- placeholder blocking;
- horizontal/vertical card image;
- fingerprint;
- subtitle length;
- generic text;
- final summary format.

Target:

- references become historical archive;
- extract durable rules into `contracts/gb-cc-en.md` or runtime validators;
- do not let Atena choose between many overlapping reference files during normal production.

## 10. Cache map

### Editorial cache — remove from production

| Item | Current status | Target |
|---|---|---|
| `data/card-cache.db` | Queried by REC and P1 runners | Historical/debug only |
| `card-cache-lookup.sh` | Queries `card_cache`, logs hits/misses | Not used in content flow |
| `card-cache-save.sh` | Upserts card facts into `card_cache` | Not used after publish |
| `card-cache-stats.sh` | Reports card cache stats | Debug only |
| cached official URL | Used as fallback | Prefer explicit/current official source |
| cached benefits/APR/fee | Possible content influence | Do not use |
| cached descriptor/tag | Possible content influence | Do not use |

### Technical cache — keep

| Item | Current status | Target |
|---|---|---|
| `wp-term-cache.json` | Caches WP taxonomy IDs | Keep |
| `rec-fingerprints.db` | Similarity history | Keep/redesign for QA |
| `sites.json` | Site config | Keep |

## 11. Conflicts / ambiguity to resolve before edits

| Issue | Current ambiguity | Target resolution |
|---|---|---|
| Source of truth | SKILL, templates, references and runners all look authoritative | `contracts/gb-cc-en.md` + runners/validators |
| REC+P1 type | Can be read as combined mental mode | Operation composed of separate REC + P1 execution |
| P1 dependency on REC | P1 reads REC raw/rendered and preserves labels | Pass only minimal metadata; no editorial inheritance |
| Cache | Treated as speed/reuse feature | Remove editorial cache from production |
| References | Many look like current rules | Archive/historical only |
| Fingerprint | Same-card/multi-site only | Add cross-card and P1 QA modes |
| Hard gates vs warnings | Mixed vocabulary in docs | Define runtime blocking vs warning vs manual QA |
| P1 template authority | Template exists but P1 runner generation is mostly code | Make explicit in contract/runner |

## 12. Recommended next sequence

No code changes should occur before this map is reviewed.

Correct sequence:

1. Review this active content map.
2. Approve authority model.
3. Extract active rules from SKILL/templates/recent references into draft `contracts/gb-cc-en.md`.
4. Review contract with Rodolfo/Raquel.
5. Only then reduce `SKILL.md`.
6. Only then remove editorial cache from runners.
7. Only then build orchestrator and QA validator.

## 13. Implementation guardrails

- Do not delete `card-cache.db` in first pass.
- Do not move references until contract is created and reviewed.
- Do not reduce `SKILL.md` until its useful rules are migrated.
- Do not modify runners until no-cache production behavior is approved.
- Keep git diffs small and checkpointed.
- Validate with dry-runs before any publish/update benchmark.
