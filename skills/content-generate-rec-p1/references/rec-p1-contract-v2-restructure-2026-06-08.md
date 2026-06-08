# REC/P1 contract v2 restructure — 2026-06-08

Use this reference when reviewing, rolling back, or extending the Atena REC+P1 credit-card restructure validated with Rodolfo/Raquel.

## What changed

- REC became a short consultative recommendation, not a generic long review.
- P1 became the deeper application/details article and must not repeat REC phrasing.
- REC meta description range changed to 130–140 chars.
- P1 keyword/card-name count changed to 5–8 visible uses.
- REC slug pattern: `rec-{country_code}-cc-{card_name}`.
- P1 slug pattern: `apply-now-{country_code}-cc-{card_name}`.
- Visual rules moved to `references/featured-image-visual-contract.md`.
- Runners/validators were aligned after contract changes; do not update contracts alone if runners/hard gates still enforce old rules.

## Card image vs featured image rule

Keep this distinction explicit in future reviews:

```text
Isolated card image      Separate asset used in LazyBlock REC/P1.
                         May be reused between REC and P1.
                         May serve as visual reference/base.

Featured image REC       Final contextual/lifestyle ad composition for REC.
Featured image P1        Final contextual/lifestyle ad composition for P1.
                         Must be different from REC featured image.
```

The isolated card image is **not** the featured image final. It only helps preserve card identity when generating the featured composition.

## Runner validation lessons

After applying editorial contract changes, validate at both levels:

1. Static/syntax:
   - `python3 -m py_compile` for REC/P1/orchestrator scripts.
   - `git diff --check` for changed contracts/scripts.
2. Safe generation:
   - REC dry-run with official/card data and realistic benefits.
   - P1 unit generation or dry-run.
   - Semantic QA on generated HTML/body.
3. Evidence expected:
   - REC word count within contract and semantic QA OK.
   - REC meta chars in 130–140.
   - P1 details blocks present.
   - P1 has two LazyBlocks.
   - P1 visible keyword total in 5–8.

## Common pitfalls fixed in this session

- Contract says new REC/P1 structure but runner still generates old sections.
- SEO validators still enforce old meta ranges.
- Keyword count accidentally includes LazyBlock JSON/figure alt instead of visible text.
- REC body uses words/phrases that trip hard gates (`Review`, repeated generic reader phrasing).
- Reporting featured-image rules without separating card reference asset from final featured composition.

## Operational next step after restructure

Do not jump straight to publish. First run one controlled real draft REC+P1:

```text
1. Choose one site.
2. Choose one real card.
3. Use official issuer URL/source.
4. Generate REC+P1 as draft.
5. Validate card image, REC featured image, P1 featured image different from REC, LazyBlocks, Yoast, slugs, semantic QA, and preview/draft evidence.
6. Only then release production use.
```

Atena gateway restart is not usually required for scripts/contracts read from disk, but for the first post-restructure live test, prefer a clean gateway restart if Rodolfo approves so no stale active-thread/session context influences the test.
