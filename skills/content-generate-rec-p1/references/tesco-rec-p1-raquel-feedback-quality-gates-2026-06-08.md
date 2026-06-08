# Tesco REC+P1 Raquel feedback — quality gates

Session: 2026-06-08
Scope: post-publication editorial/structural review of Tesco Bank Balance Transfer Credit Card REC+P1, comparing Atena output and Raquel `-2` revisions.

## Core lesson

Runners can still convert real facts into wrong commercial framing when broad fallbacks are used. The clearest example was `Clubcard points` being treated as generic `points`, which allowed `Travel rewards` copy/tagging even though the product is a balance-transfer card, not a travel-rewards card.

Future REC+P1 work must validate not only that facts came from the official source, but also that the **category interpretation** of those facts is correct.

## Confirmed official facts for Tesco Balance Transfer

Use as pattern for balance-transfer products, not as universal facts:

- 0% interest on balance transfers guaranteed for 36 months.
- Balance transfer fee: 3.45%.
- 0% interest on money transfers for first 9 months.
- Money transfer fee: 3.99%.
- Collect Clubcard points almost every time you spend in and out of Tesco.
- Representative 24.9% APR variable.
- UK residents aged 18+; subject to status.

Do not add `No Annual Fee` unless confirmed by current official source/facts.

## Editorial gates to promote to runners/validators

### Benefits

- REC H3 benefits must be named real product features, not internal labels.
- Block generic benefit labels such as:
  - `Main benefit`
  - `Financial value`
  - `Usage convenience`
  - `Complementary benefit`
- For balance-transfer cards, expected benefit headings should look like:
  - `0% Balance Transfers for 36 Months`
  - `0% Money Transfers for 9 Months`
  - `Tesco Clubcard Points on Eligible Spending`
  - fee/repayment planning benefit where relevant.

### Voice

- Avoid addressing the audience as `reader`, `readers`, or `users` in editorial body copy.
- Prefer direct second person: `you`, `your balance`, `your repayment plan`, `your existing card debt`.
- Institutional phrasing is allowed only where legally/technically necessary; main copy should feel consultative.

### Category interpretation

- `points` alone is not enough to infer `travel rewards`.
- Only use `Travel rewards`, `Avios`, `lounge`, `hotel`, etc. when the official facts explicitly support travel value.
- `Clubcard points` should be treated as retailer/loyalty value, not travel value.

### Language consistency

- P1 contract/runners must not hardcode Portuguese section labels when `lang=en`.
- Block mixed-language output such as English article body with headings/details named `Benefícios` or `Quem deveria usar`.
- Details titles must be localized by article language.

### LazyBlocks and CTA

- REC and P1 must each contain exactly one `lazyblock/credit-card` unless a repair task explicitly asks otherwise.
- P1 card must appear once immediately after the introduction.
- REC final CTA must be a valid LazyBlock/button linking to the internal P1.
- P1 final CTA must be a valid LazyBlock/button linking to the official issuer URL.
- Do not accept a plain hyperlink or visible CSS/HTML artifact as a successful CTA render.

### Details blocks

- Details summaries should be visually scannable; prefer strong/bold summary text or equivalent CSS.
- Block empty H2/H3 headings and empty Details summaries.

### Featured image card visibility

- Featured images may be lifestyle/contextual, but the card must remain fully visible.
- No person/object/layer may cover card borders, corners, logo, or critical identity elements.
- Treat card occlusion as a visual failure even if the image file itself is not cropped.

## Balance-transfer P1 depth pattern

A P1 for a balance-transfer card should go beyond listing facts. It should explain:

- how moving an existing balance works;
- why the promotional 0% window matters;
- how to compare the transfer fee against interest avoided;
- what happens after the promotional period ends;
- why repayment discipline matters;
- who benefits most: people with existing card debt, people consolidating balances, people with a realistic repayment plan, and relevant Tesco customers when Clubcard points are confirmed.

Reduce repetitive regulatory warnings. Keep warnings, but tie them to concrete decisions and practical consequences.
