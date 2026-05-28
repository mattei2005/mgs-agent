# REC/P1 Architecture Cleanup and Editorial Cache Policy

Use this reference when Rodolfo asks to reform, simplify, or audit the Atena REC/P1/REC+P1 pipeline.

## Core lesson

REC+P1 is not a third article type. It is a composed operation:

1. Generate REC with the REC contract.
2. Generate P1 with the P1 contract.
3. Link REC -> P1 -> official bank page.
4. Validate each article separately.
5. Report the pair together.

Do not design a mega prompt that blends REC and P1. Consolidate the source of truth, not the articles.

## Recommended authority model

| Layer | Role |
|---|---|
| Atena SOUL.md | Behavior/persona only; not editorial source of truth |
| AGENT.md | MGS governance, safety, authorization |
| content-generate-rec/SKILL.md | Short operational routing and commands |
| contracts/gb-cc-en.md | Active editorial source of truth for GB credit-card REC/P1 |
| runners .py | Runtime execution and hard gates |
| references/archive/ | Historical lessons only; not active source |
| thread instructions | Current-case instruction; not permanent rule unless promoted |

## Contract shape

Prefer a single vertical contract with separated sections:

```text
contracts/gb-cc-en.md
├── COMMON rules
├── REC contract
├── P1 contract
└── REC+P1 orchestration rules
```

The REC+P1 section should state that REC+P1 only orchestrates two separate article contracts. P1 must not use REC paragraphs/opening/benefit prose as editorial input.

## Editorial cache policy

Rodolfo's operational preference after the REC/P1 audit: cache must not drive content production.

Remove or disable editorial cache from production content flows:

| Cache/input | Production content use |
|---|---|
| card-cache text/facts | No |
| benefits / rewards / fees / APR | No as source of truth; fetch current official source |
| descriptor / tag / headline | No |
| REC paragraphs/opening/benefit prose | No input to P1 |
| cached card image | Not automatic; only if explicitly approved and revalidated |
| wp-term-cache.json | Yes, technical taxonomy cache only |
| rec-fingerprints.db | Yes, QA history only, not content source |
| sites.json | Yes, technical site config |

Reason: when the same card is produced across 25-30 sites, editorial cache can propagate stale or bad decisions at scale. Each article should consult current official source data and generate fresh copy with QA.

## Multi-site rule

For the same card across many sites, facts may match because the issuer page is the same, but article copy must be fresh:

- Do not reuse opening, title, subtitle, narrative, table prose, conclusion, meta description, or editorial positioning.
- Do not use cached benefit prose or descriptors.
- Use fingerprint/semantic QA to detect cross-card and cross-site repetition.

## Refactor sequence

1. Map active runtime vs human references vs cache.
2. Approve authority model before code changes.
3. Create/approve the vertical contract.
4. Enshrine references as historical/archive, not active source.
5. Remove editorial cache reads/writes from REC/P1 runners.
6. Ensure P1 receives only metadata minimum from REC: card_name, card_slug, rec_post_id/URL, official_url, and validated card image reference if needed.
7. Add QA validators before scaling.
8. Benchmark with several REC+P1 cards before broad rollout.
