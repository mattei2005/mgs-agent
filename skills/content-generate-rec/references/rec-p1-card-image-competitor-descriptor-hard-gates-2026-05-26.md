# REC/P1 card image, competitor table and card descriptor hard gates — 2026-05-26

## Trigger

Use this for REC and P1 creation, repair, audit, or runner/template changes when the article includes a LazyBlock credit-card component and/or a REC Comparative Table.

## Durable rules from Rodolfo

### 1. LazyBlock card image

The card component image must contain exclusively the credit card itself.

Allowed:
- isolated horizontal card artwork;
- transparent/no external background;
- no visible canvas outside the card;
- no props, hands, people, graphic backgrounds, frames, shadows, external borders or decorative moulding.

Blocked:
- a card placed over a coloured/artistic background;
- a card inside a banner, frame, phone, mockup, lifestyle scene, or promotional image;
- visible padding/canvas, abstract shapes, shadows or external border/moldura around the card.

If an automatic image search returns a visually attractive card-on-background image, it is still invalid for the LazyBlock slot until it is cropped/masked to card-only or replaced.

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
- for cashback/build-credit cards, mention the real cashback, eligibility or credit-building angle.

## Validation checklist

Before reporting a REC/P1 as corrected or validated:
1. Verify the raw WP content uses the approved card-only media ID/URL in every LazyBlock card component.
2. Verify public/cache-busted page HTML no longer contains the rejected card image URL.
3. Verify REC table contains only real competitor card names and real benefits/fees.
4. Verify competitor annual-fee cells are fully researched; never publish `Check issuer terms` when a public fee exists.
5. Verify no LazyBlock `texto` contains generic issuer/account wording.
6. Verify REC and P1 openings are benefit-led and not reused with only the card name changed.
7. Re-run Yoast scoring after content repair and do not report clean success if scores are below green unless Rodolfo explicitly accepts the exception.
