# REC/P1 card image, competitor table and card descriptor hard gates — 2026-05-26

## Trigger

Use this for REC and P1 creation, repair, audit, or runner/template changes when the article includes a LazyBlock credit-card component and/or a REC Comparative Table.

## Durable rules from Rodolfo

### 1. LazyBlock card image

The card component image must contain exclusively the credit card itself.

Allowed:
- isolated horizontal card artwork only;
- issuer-published portrait/vertical card artwork only after rotating it 90° to horizontal without stretching or changing proportions;
- transparent/no external background;
- no visible canvas outside the card;
- no props, hands, people, graphic backgrounds, frames, shadows, external borders or decorative moulding.

Blocked:
- a vertical card left vertical in the LazyBlock card slot;
- a distorted card resized/stretched to fake horizontal orientation;
- a card placed over a coloured/artistic background;
- a card inside a banner, frame, phone, mockup, lifestyle scene, or promotional image;
- visible padding/canvas, abstract shapes, shadows or external border/moldura around the card.

If an automatic image search returns a visually attractive card-on-background image, it is still invalid for the LazyBlock slot until it is cropped/masked to card-only or replaced. If the only valid issuer asset is vertical, rotate the clean card-only image horizontally; do not leave it vertical.

### 2. REC comparative table

The Comparative Table must not use generic placeholders such as:
- `another card in the same segment`;
- `a second comparable card`;
- `Varies` as a substitute for researched annual fee when facts are available;
- generic notes like `Compare eligibility, APR and fees before applying` as the main table value.

The table must use real market cards from the same country and coherent segment. For each competitor, use real card names and real comparable facts/benefits. If two real competitors are not available from cache, explicit inputs, official-source research, or a bounded vetted same-segment scan, stop or request inputs instead of publishing a fake comparison.

### 3. LazyBlock card descriptor (`texto`)

The card descriptor must be short, commercial and benefit-led. It must not be generic.

Blocked examples:
- `A UK credit card with issuer terms and online account features.`
- `A UK credit card with ... and practical account features.`
- `Learn more about the card.`

Correct pattern:
- highlight one strong real benefit;
- create quick visual interest;
- stay objective and attractive;
- end with clean punctuation;
- ideal length <=70 characters, hard cap 100 characters.

Examples:
- `Earn cashback on everyday spending.`
- `Exclusive travel rewards and premium benefits.`
- `Build credit with flexible approval options.`
- `0% interest on purchases for up to 12 months.`
- `Earn Marriott Bonvoy points, elite nights and travel rewards.`

### 4. Opening copy and section uniqueness

REC subtitles, P1 subtitles and repeated P1 sections must be product-specific, not card-name substitutions inside a generic sentence.

Blocked examples:
- `{Card Name} offers key credit card benefits and features.`
- `{Card Name} earns rewards and explains key costs before you apply.`
- generic P1 sections about travel, balance transfers or rewards when those are not the product's real positioning.

Correct pattern:
- use a real primary benefit or product hook in the first sentence;
- adapt section examples and triggers to the card's confirmed features;
- for Amazon-style cards, mention Amazon rewards, gift-card welcome offers, Prime event boosts, app-first setup or 0% purchases when confirmed;
- for travel cards, mention the actual travel currency/perk;
- for cashback/build-credit cards, mention the real cashback, eligibility or credit-building angle;
- for low-APR/no-fee cards, do not force `rewards` language; focus on rate control, annual fee, overseas fees, balance-transfer rules and repayment fit.

### 5. REC/P1 semantic duplication gate

Before publishing or repairing scaled REC/P1 pages, scan the opening, `How Does It Work`, `Benefits`, `Requirements`, `How to Apply`, `How to Maximise` and final-fit sections for template reuse. The structure may remain consistent, but the reasoning, examples and benefit framing must change with the card's actual proposition.

Blocked patterns:
- introductions that only swap the card name;
- P1 subtitles using a repeated sentence frame;
- reward/travel/balance-transfer paragraphs on products whose main hook is low APR, no annual fee or overseas purchase fees;
- REC comparative tables with `Check issuer terms` or `Real same-segment comparison option` in any visible cell.

## Validation checklist

Before reporting a REC/P1 as corrected or validated:
1. Verify the raw WP content uses the approved card-only media ID/URL in every LazyBlock card component.
2. Verify public/cache-busted page HTML no longer contains the rejected card image URL.
3. Verify REC table contains only real competitor card names and real benefits/fees.
4. Verify competitor annual-fee and positioning cells are fully researched; never publish `Check issuer terms` or `Real same-segment comparison option`.
5. Verify no LazyBlock `texto` contains generic issuer/account wording.
6. Verify REC and P1 openings are benefit-led and not reused with only the card name changed.
7. Verify P1 body sections are adapted to the product's real proposition, not generic rewards/travel copy.
8. Verify P1 subtitle/excerpt is <=100 characters exactly, counting spaces and punctuation; if it exceeds 100, rewrite it before publication.
9. Verify REC copy is recommendation-led and commercially attractive without unsupported claims.
10. Verify P1 copy is deeper and more explanatory than REC, with richer product-specific context and a natural/human tone.
11. Re-run Yoast scoring after content repair and do not report clean success if scores are below green unless Rodolfo explicitly accepts the exception.
