# REC/P1 scale quality gates — repeated-error prevention (2026-05-27)

## Why this exists

Rodolfo escalated that recurring REC/P1 errors cannot be fixed manually article by article. For scale across many sites, repeated corrections must become pipeline/skill hard gates, not Discord reminders.

This reference complements `references/rec-p1-card-image-competitor-descriptor-hard-gates-2026-05-26.md`.

## Root cause pattern from Amazon Barclaycard

The previous repair fixed only part of the rule:
- it correctly rejected phone/app/background promotional card compositions;
- but it incorrectly allowed issuer-published portrait/vertical card art to remain vertical in the LazyBlock card slot.

Correct interpretation:
- `card-only` is required;
- **horizontal card orientation is also required**;
- if the only clean official issuer asset is vertical, rotate it 90° without stretching/distortion;
- do not choose a phone/app/hero composition just because it is already horizontal.

## Non-negotiable gates before REC/P1 is reported ready

### Card image gate

For every LazyBlock card image in REC and P1:
1. Image must show only the card.
2. No phone, app screenshot, hand, scene, banner, background, frame, shadow, mockup or decorative canvas.
3. Card must be horizontal in the final LazyBlock image.
4. If official card art is vertical/portrait, rotate 90° with preserved proportions.
5. Never stretch or distort the card to fake horizontal orientation.
6. Verify the published page no longer references rejected media.
7. Delete the rejected media after replacement when safe.

### Subtitle/excerpt gate

For REC and P1 opening/subtitle/excerpt:
1. Hard cap: **100 characters exactly**, counting spaces and punctuation.
2. Count before publishing and after every rewrite.
3. If >100, rewrite; do not truncate into weak/generic copy.
4. The fallback must still be benefit-led, not a generic sentence.

Blocked fallback examples:
- `{Card Name} offers key credit card benefits and features.`
- `{Card Name} earns rewards and explains key costs before you apply.`
- `{Card Name} explains key costs and benefits before you apply.`

Better fallback pattern:
- `{Card Name} highlights real benefits, costs and application steps.`
- Prefer product-specific hooks when known, e.g. Amazon rewards, cashback, Avios, Nectar, low APR, no annual fee.

### Tone, card-tag and differentiation gate

REC and P1 must not sound like the same article with more words.

REC should read as:
- a light commercial recommendation;
- benefit-led and curiosity-building;
- concise, natural and persuasive without unsupported claims;
- a reason to continue to the P1/application page.

P1 should read as:
- deeper and more strategic;
- richer in product-specific details;
- practical about costs, eligibility and repayment;
- natural/human, not robotic or over-formal.

LazyBlock card tags must be commercially meaningful, not truncated fragments or generic labels. They must:
- highlight real product benefits;
- be clear and objective at a glance;
- transmit value quickly;
- reinforce the product's actual differentiators.

Blocked card-tag patterns:
- truncated strings such as `Over 1`;
- generic labels such as `Travel perks`, `Card benefits`, `Premium card` when a specific benefit is known;
- tags that look incomplete, ambiguous or detached from the product.

Preferred card-tag patterns:
- `Airport Lounge Access`;
- `No Foreign Transaction Fees`;
- `Premium Travel Benefits`;
- `Global Rewards`;
- product-specific reward/fee/insurance/lifestyle benefits confirmed by the official source.

Blocked narrative patterns:
- same structure + same paragraph logic + only card name and numbers changed;
- broad paragraphs that could apply to any premium/rewards card;
- neutral filler such as “frame around its real practical value” without naming the actual benefits.

Required narrative pattern:
- keep the architecture if needed, but vary reasoning, examples, hooks and benefit framing according to the actual product;
- name the specific benefits in explanatory paragraphs, not only in bullet lists;
- for premium travel cards, explicitly connect travel, lounge access, international use, exclusivity, lifestyle and real cost/fee trade-offs when those facts are confirmed.

### P1 featured image opacity gate

For P1 featured images, the card must look solid, crisp and realistic. A visually pleasant composition still needs repair if the card appears transparent, ghosted, washed out, or too low-contrast against the background.

Required checks:
- card body is opaque and visually solid;
- key identity marks remain legible;
- no translucent overlay effect;
- card sits naturally in the premium/lifestyle context without looking pasted or faded.

## Implementation notes from the session

Changes made in the pipeline after the correction:
- `scripts/mgs-rec-runner.py`: REC opening copy made more recommendation-led and product-specific.
- `scripts/mgs-p1-runner.py`: P1 Amazon subtitle shortened and Amazon sections made more natural/product-specific.
- `skills/content-generate-rec-p1/scripts/search-card-image.sh`: official portrait card art is accepted only as clean card-only input and normalized to horizontal output via 90° rotation.
- `references/rec-p1-card-image-competitor-descriptor-hard-gates-2026-05-26.md`: updated with horizontal-image, 100-character subtitle and REC/P1 tone gates.

## Verification recipe

Before final reply on REC/P1 repair or publication:
1. Check LazyBlock media URL(s) in raw/rendered content.
2. Confirm final card image dimensions are landscape (`width > height`).
3. Vision-check if there is any doubt about phone/app/background/mockup elements.
4. Count first REC/P1 subtitle characters exactly.
5. Search visible/rendered content for blocked generic phrases, truncated card tags, weak generic tags, and placeholders.
6. Vision-check P1 featured images for card opacity/solidity, not only 16:9/person/context.
7. Validate REC body with `validate-article.sh` when applicable.
8. Rerun Yoast scoring.
9. Report only verified status, not intended fixes.
