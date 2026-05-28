# REC/P1 perceived-benefit tone and comparison-table scope — 2026-05-28

## Trigger

Use this reference when REC/P1 output is technically correct but still reads cold, generic, rigid, or like a product inventory.

## User correction

Rodolfo corrected the NatWest Travel Reward REC/P1 after publication:

- Technical benefits must become perceived benefits. The reader should imagine the card in practical use, not only receive extracted facts.
- Tone should be professional, accessible, persuasive without exaggeration, informative with a light human touch, conversational where useful, confident and clear.
- Text should increase attention, time on page, Google ranking potential, trust, clicks and conversion.
- Language must adapt to the vertical, audience and product identity: technical, premium, relaxed, sales-oriented, institutional, young or sophisticated as appropriate.
- REC comparison table guidance applies only to the `gb-cc-en` vertical/contract. Where `gb-cc-en` includes a comparison table, it should stand on its own: do not add generic post-table paragraphs such as `Compared with...`, `The table is a quick orientation tool`, or `Rates and terms can change`. Use that space for a useful next section. Do not require or report article tables for other verticals unless their own contract explicitly requires them.
- P1 intro paragraphs should stay around 30–35 words each for mobile readability.

## Durable pattern

### Convert fact → perceived benefit

Bad:

```text
No foreign transaction fees on purchases abroad.
```

Better:

```text
Purchases abroad can feel easier to control because eligible card spending avoids the usual foreign transaction fee.
```

Bad:

```text
Up to 15% back in Rewards with chosen partner retailers.
```

Better:

```text
Up to 15% back with chosen partner retailers can make planned travel feel more worthwhile.
```

### Remove table aftertext (`gb-cc-en` only)

This section is scoped to `gb-cc-en`. Do not promote the comparison-table requirement to other verticals unless their own active contract explicitly says so.

After the REC comparison table, go directly to a useful next subtitle, for example:

- `How to Use It in Practice`
- `What to Check Before Applying`
- `Who Is This Card Best For`

Avoid explaining the table after the table. The table already carries the comparison.

### P1 intro shape

Use multiple compact paragraphs rather than one dense paragraph:

```text
The [Card] is most relevant when [real use case] already sits inside the reader's normal spending plans.

The value is not about chasing perks. It is about making [planned behaviour] return something useful without weakening repayment control.

Start with [fee/APR/core numbers], then judge whether [benefit rules] fit real usage.
```

## QA gates added in session

The validator was updated to block:

- weak generic perceived-benefit copy;
- REC post-table explanation filler;
- P1 intro paragraphs over 35 words.

## Operational lesson

Machine QA can pass while the article still feels weak. For benchmark/publish runs, inspect the visible REC/P1 text for emotional/commercial fit, not just factual correctness and Yoast scores.
