# REC Readability Repair Gate — Vitality Amex lesson

## Trigger

Use this when a REC Yoast Readability score is yellow/red (`<71`), especially after a deterministic/local-generator draft or after manually changing a REC from draft to publish.

## Why this exists

The Vitality American Express REC initially reached SEO green but Readability stayed at `60` because the article had too few transition words, avoidable passive voice, and comparative-table copy that Yoast read as long pseudo-sentences. A light rewrite raised Readability from `60` to `90` while preserving SEO, facts, LazyBlocks, URL and word count.

## Hard gate

Do not report a REC as final/ready when Yoast Readability is `<71` unless Rodolfo or Raquel explicitly approves the exception in that same thread.

This applies to:
- newly created REC posts;
- edited/repaired REC posts;
- draft-to-publish status changes for REC or REC+P1 flows;
- manual REST status flips that bypass the normal runner summary.

## Repair recipe

1. Fetch the raw post content with authenticated WordPress REST.
2. Preserve all LazyBlocks exactly.
3. Rewrite only visible paragraphs and table cell copy.
4. Keep word count within `450–500` and subtitle/excerpt within `100` characters.
5. Target transition words at roughly `25–33%` of analysed sentences.
6. Convert avoidable passive voice into active phrasing.
7. Keep paragraphs at `≤30` visible words when possible.
8. Compact comparison/table cells so Yoast does not read them as long pseudo-sentences.
9. Re-run `validate-article.sh` on the exact final body.
10. Update WordPress and re-run `yoast-score-post.sh` until Readability is green.

## Vitality example

Before repair:
- Readability: `60`
- Transition ratio: `17%`
- Passive candidates: `4`
- Table copy produced long pseudo-sentences

After repair:
- Readability: `90`
- SEO stayed `86`
- Word count: `468`
- Subtitle: `75` characters
- Transition ratio: `32%`
- Passive candidates: `1`

## Preferred rewrite patterns

- Use transitions naturally: `However`, `In addition`, `Therefore`, `Also`, `As a result`, `In contrast`, `Meanwhile`.
- Prefer active copy: `Readers should compare...` instead of `It should be checked...`.
- Split benefit/rate details into two short sentences.
- Keep comparative-table cells short and noun-like, not full sentence chains.
