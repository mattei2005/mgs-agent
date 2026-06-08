# REC/P1 LazyBlock tags and opening gates — 2026-05-27

## Trigger

Rodolfo compared a Zeus-generated REC/P1 pair with Raquel's editorial version and found Zeus technically valid but editorially weaker. The visible issues were:

- REC/P1 opening sounded like an inventory: “highlights real benefits, costs and application steps”.
- LazyBlock `tag10` repeated the card category already present in the card name, e.g. `Balance transfer` for `Nationwide Balance Transfer Credit Card`.
- LazyBlock `tag2` became a broken numeric fragment (`2`) because a fee string like `2.99% balance transfer fee; minimum £5` was split on the decimal point.
- A visually strong label like `No fees` can be factually ambiguous when the card has a balance-transfer fee or other material fee.

## Durable rule

Do not solve this by post-editing one article. Fix the class of failure in three places:

1. Contract: make the editorial expectation explicit.
2. Runner generation: derive tags from current benefits/facts instead of raw fee strings or REC handoff labels.
3. QA validator: block bad labels and weak openings before publication.

## Required generation behavior

LazyBlock tags must be short, commercial and benefit-led:

```text
Good examples:
- 30 mo 0%
- No FX fees
- 0% transfers
- 0% purchases
- Cashback
- Travel rewards
- No annual fee

Bad examples:
- 2
- 2.99
- 24
- Over 1
- Balance transfer when already in the card name
- Credit card
- Card benefits
- Official terms
- Transfer fee
- No fees when any material fee exists
```

Never split a fee string on `.` because it can truncate decimals (`2.99%` → `2`). Prefer extracting semantic labels from benefits and explicit official facts.

For REC+P1, the P1 must not blindly preserve REC LazyBlock `tag10`, `tag2`, or `descriptor`. P1 should derive fresh labels from current official/request facts.

## Required opening behavior

The first sentence should translate the product into a user outcome or problem:

```text
Better:
Nationwide Balance Transfer Credit Card is aimed at readers who want to reduce interest pressure while organising existing card debt.

Better:
Nationwide Balance Transfer Credit Card helps organise card debt before interest returns.

Worse:
Nationwide Balance Transfer Credit Card highlights real benefits, costs and application steps.
```

For balance-transfer cards, lead with interest pressure, repayment window, existing card debt, or repayment timing. For reward/travel/cashback cards, lead with the concrete spending use case and reward value.

## Validation pattern

QA should hard-block:

- numeric or decimal-only LazyBlock labels;
- fee fragments used as labels;
- generic labels (`Credit card`, `Card benefits`, `Official terms`, `Transfer fee`);
- redundant category labels when already present in card name;
- ambiguous `No fees` where the page/facts mention any material fee;
- weak inventory openings such as “highlights real benefits, costs and application steps”.

A generated Nationwide balance-transfer smoke test should produce tags like:

```text
tag10 = 30 mo 0%
tag2  = No FX fees
```

and QA should return `OK` for the good sample and `BLOCK` for a bad sample containing `tag2="2"` or the inventory opening.
