# Vitality REC+P1 — card copy and meta punctuation corrections (2026-05-26)

## Trigger
Rodolfo reviewed the draft REC+P1 for Vitality American Express Credit Card and corrected recurring output-quality issues in the REC meta description, REC card LazyBlock, and P1 card LazyBlock.

## Canonical lessons

### 1. Meta description punctuation gate
Meta descriptions must end with clean sentence punctuation.

Allowed:
- Period (`.`) — preferred.
- Ellipsis (`...`) only when unavoidable due to strict character trimming.

Blocked:
- `.,...`
- `,...`
- `..`
- `... .`
- lowercase sentence starts after a period, such as `terms apply.` after `... months.`

Bad example:
`Vitality American Express Credit Card offers £100 statement credit after £2,000 spend in the first three months. terms apply.,...`

Good example:
`Vitality American Express Credit Card offers a £100 statement credit and cashback rewards for eligible Vitality members.`

### 2. REC/P1 card text (`texto`) gate
The LazyBlock card `texto` should be short, commercial, and visually clean.

Rules:
- Ideal limit: up to 70 characters.
- Hard cap: 100 characters only if the theme requires it.
- Must highlight one real differentiator or benefit.
- Must end with a period.
- Avoid long operational clauses and stacked fee explanations.

Bad example:
`A UK credit card with no annual card fee; £5.50 vitality programme fee and practical account feature`

Good example:
`Earn cashback with Vitality rewards.`

### 3. REC/P1 card tag gate
LazyBlock card tags (`tag10`, `tag2`) must be one benefit or feature each.

Rules:
- No semicolons.
- No commas joining multiple facts.
- No broad generic labels.
- Never use `Card features`, `Card benefits`, `Credit card`, or `Features` as a card tag.
- Prefer concrete product-specific value hooks.

Bad examples:
- `No annual card fee; £5.50`
- `Card features`

Good examples:
- `£100 statement credit`
- `Cashback rewards`
- `Airport lounge access`
- `Travel insurance`
- `No foreign fees`

## Runner enforcement added in-session
The REC and P1 runners gained deterministic helpers for:
- Cleaning broken meta punctuation.
- Producing single-benefit card tags.
- Producing concise card descriptors with final punctuation.
- Removing the generic `Card features` fallback from P1 LazyBlocks.

Future agents should preserve these gates when modifying REC/P1 generation. If a generated draft violates any item above, repair before reporting the package as ready for review.
