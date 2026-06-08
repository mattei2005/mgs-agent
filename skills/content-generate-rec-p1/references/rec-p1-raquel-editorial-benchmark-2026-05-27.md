# REC/P1 editorial benchmark — Raquel vs Zeus (2026-05-27)

## Context

Rodolfo compared Zeus-generated REC/P1 content for `Nationwide Balance Transfer Credit Card` with Raquel's manually improved versions on Eggbev.

Finding: the Zeus output passed technical gates but was still too generic/mechanical. Raquel's versions were stronger because they framed the product as a user solution, not as a product inventory.

## Durable lesson

For credit-card REC/P1 generation, passing format, Yoast, image and link gates is not enough. The first blocks must sell the user outcome.

### P1 pattern that won

Raquel's P1 was better because it opened with:

- real user pain: existing debt, interest pressure, multiple payments;
- desired outcome: reduce interest, simplify repayments, regain control;
- commercial/emotional context before APR/fee/application mechanics;
- benefits as explanatory blocks, not a dry extracted-fact list.

For balance-transfer P1s, lead with debt relief and repayment simplification before mechanics.

### REC pattern that won

Raquel's REC was better because it opened with the strongest benefit:

> Nationwide Balance Transfer Credit Card offers up to 30 months interest-free transfers.

Zeus's weaker opening was:

> Nationwide Balance Transfer Credit Card highlights its confirmed costs and benefits.

The winning REC pattern:

- open with the strongest commercial benefit, not article intent;
- connect balance transfer to debt, interest pressure, time to pay and financial control;
- use a short scannable benefits list when there are 4+ concrete benefits;
- explain transfer fee as a trade-off against time/interest savings;
- define the target user as someone carrying higher-interest balances who wants a clearer repayment plan.

## Runner/validator implications

- REC/P1 openings such as `confirmed costs and benefits`, `real benefits, costs and application steps`, and similar inventory framing should be blocked or rewritten.
- Balance-transfer LazyBlock tags should prefer commercial benefit labels such as `30 mo 0%`, `No FX fees`, `0% transfers`; avoid `Balance transfer`, `Transfer fee`, numeric fragments like `2`, and ambiguous `No fees` when material fees exist.
- P1 must not inherit REC LazyBlock tags by default; derive tags independently from current official/request facts.
- QA should include a semantic check for user-outcome context, especially in balance-transfer articles.

## Use in future benchmarks

Before declaring REC+P1 stable, validate at least 3 articles. For each article, compare against Raquel/editorial review on:

1. opening/golden hook;
2. commercial/emotional context;
3. LazyBlock tags;
4. benefit explanation;
5. target-user fit;
6. scanability and conversion intent.
