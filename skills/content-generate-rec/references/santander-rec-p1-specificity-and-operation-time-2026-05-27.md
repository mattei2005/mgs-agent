# Santander REC+P1 specificity + operation-time correction (2026-05-27)

## Why this exists

Rodolfo reviewed the Santander World Elite Mastercard REC+P1 and corrected two recurring pipeline issues:

1. Final summary timing reported only successful runner duration, while the user experienced the full request-to-summary elapsed time.
2. REC/P1 copy and visuals passed basic gates but still felt too generic for a premium travel card.

This reference extends the class-level REC/P1 quality gates rather than creating a narrow one-off skill.

## Final summary timing rule

For REC, P1 and REC+P1 summaries, the primary duration must be **tempo total da operação**:

- starts when the user publishes the request in the thread;
- ends when Atena sends the final summary;
- includes failed attempts, retries, image repairs, Yoast/validation, cleanup and agent overhead;
- runner-only duration may be used for diagnostics, but must not replace the main duration.

If the summary says only “Tempo total dos runners”, it can mislead the user when retries or repairs happened before the successful runner call.

## REC card tag correction

Bad observed tag:

- `Over 1`

Why it failed:

- truncated fragment;
- no clear context;
- no commercial value;
- looked incomplete in the card UI.

Required pattern:

- use specific benefit tags such as `Airport Lounge Access`, `No Foreign Transaction Fees`, `Premium Travel Benefits`, `Global Rewards`;
- tags must be real benefits from official/source facts;
- tags must work as a quick visual hook, not as extracted raw text fragments.

## Generic copy correction

Bad observed sentence:

> Overall, the card should be framed around its real practical value rather than forced into a generic rewards or premium-card story.

Why it failed:

- too neutral;
- could apply to almost any card;
- did not name Santander World Elite’s real differentiators;
- reduced commercial impact.

Repair direction:

- explicitly name the product-specific value drivers;
- for Santander World Elite, emphasize travel, LoungeKey access, no foreign transaction fees, cashback, Flexiroam data, premium positioning, exclusivity and international use when supported by the official source;
- avoid abstract “generic rewards/premium-card story” wording.

## P1 specificity correction

Rodolfo noted that P1 structure was dominating the product narrative.

Required P1 behavior:

- keep the application-page architecture, but make the reasoning product-specific;
- premium travel cards need a more sophisticated/lifestyle narrative;
- mention how benefits interact with the monthly fee and real user behavior;
- avoid paragraphs that can be reused by changing only the card name.

For Santander World Elite-style cards, explore:

- travel and airport experience;
- lounge access / VIP positioning;
- international spending;
- exclusivity / eligible customer profile;
- premium lifestyle;
- cashback and fee trade-offs.

## P1 featured opacity correction

Observed issue:

- P1 featured image composition was attractive, but the card looked slightly transparent/ghosted.

Required gate:

- card must look solid, opaque, crisp and realistic;
- identity marks should be legible;
- no washed-out or semi-transparent overlay effect;
- a pleasant lifestyle scene still fails if the card does not look physically solid.

## Verification checklist after repair

1. Search rendered/public content for truncated tags such as `Over 1`.
2. Search visible copy for blocked generic phrases like `generic rewards or premium-card story`.
3. Confirm REC validates at 450–500 words and subtitle ≤100 chars.
4. Confirm P1 word count remains in the accepted range and subtitle ≤100 chars.
5. Re-score Yoast for both posts.
6. Vision-check corrected P1 featured image for card opacity/solidity.
7. Delete replaced media only when safe and unreferenced.

## Implementation notes from this session

- `render-article-summary.py` gained operation-time support (`--operation-seconds` / `--started-at`).
- `article-final-summary-format-rodolfo-2026-05-26.md` now says “Tempo total da operação”.
- `rec-p1-scale-quality-gates-2026-05-27.md` gained card-tag, product-specific narrative and P1 opacity gates.
- Santander posts were repaired and revalidated after publication.
