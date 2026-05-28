# REC Readability Repair — Vitality Amex case (2026-05-26)

Use this reference when a REC article is published or drafted with Yoast Readability in yellow/red, especially after local deterministic generation.

## Trigger
- REC post exists in WordPress and Yoast readability is `<71`.
- SEO may already be green; do not assume SEO fixes will improve readability.
- User asks why readability is low or asks to improve it.

## Durable lesson
A short REC can still score yellow when it has:
- Low transition-word density.
- Avoidable passive voice (`it should be checked`, `it is presented`, `it is assessed`).
- Comparison/table text that Yoast reads as long sentence-like runs.

In the Vitality American Express REC, the initial state was:

```text
Readability: 60
Sentences: 35
Long sentences: 4 / 11%     # not the main problem
Transitions: 6 / 35 = 17%   # main issue
Passive candidates: 4       # secondary issue
```

After a light rewrite preserving LazyBlocks, CTA, image, official facts and URL:

```text
Readability: 90
SEO: unchanged at 86
Word count: 468
Subtitle: 75 chars
Transitions: 11 / 34 = 32%
Passive candidates: 1
```

## Repair pattern
1. Fetch raw post content via authenticated WP REST `context=edit`.
2. Preserve every `<!-- wp:lazyblock/... /-->` block exactly.
3. Rewrite only visible paragraphs/table copy.
4. Keep REC validation constraints:
   - 450–500 visible words.
   - Subtitle/excerpt ≤100 chars.
   - Max paragraph ≤30 words.
   - No long sentence ratio >20%.
5. Target Yoast readability, not just internal validation:
   - Transition words at ~25–33% of sentences.
   - Passive voice candidates below 10%.
   - Avoid table cells that concatenate into long pseudo-sentences.
6. Run `validate-article.sh` on the exact final HTML before update.
7. Update the post, run `yoast-score-post.sh`, and do not report final success until readability is green (`>=71`).

## Copy edits that worked
- Replace passive/abstract phrasing:
  - Before: `It should be checked against budget, eligibility and repayment habits.`
  - After: `Readers should compare budget, eligibility and repayment habits before applying.`
- Add natural transitions without stuffing:
  - `However`, `In addition`, `Therefore`, `As a result`, `In contrast`, `Meanwhile`, `After that`.
- Compact comparison/table copy:
  - Use short cells such as `Compare APR, fees and eligibility` instead of sentence chains.
- Keep financial meaning intact:
  - Do not invent benefits.
  - Keep issuer facts and rates exactly aligned with source/post data.

## Reporting pattern
When reporting the fix to Rodolfo, use a concise before/after table with:
- Readability before/after.
- SEO before/after.
- Word count.
- Subtitle length.
- Status and URL.
