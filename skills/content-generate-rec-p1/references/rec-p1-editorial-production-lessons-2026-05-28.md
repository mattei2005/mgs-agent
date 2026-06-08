# REC+P1 editorial production lessons — 2026-05-28

Use this reference when producing or debugging GB credit-card REC+P1 articles.

## REC is the ad/click bridge, not just a summary

Mobile order observed on Eggbev:

```text
Title
Summary / first paragraph
Ad block
Card LazyBlock
P1 button
```

Operational implication: the REC top-of-page must carry high-value commercial/search terms before the ad and before the card. Weak inventory wording such as “confirmed costs and benefits” or “highlights real benefits, costs and application steps” should be treated as a blocker.

For balance-transfer cards, the first 2 paragraphs should include terms like:

```text
balance transfer, 0% interest, interest-free, months, existing card debt,
repayments, interest pressure, transfer fee, savings, breathing room
```

For travel/reward cards, the first 2 paragraphs should include terms like:

```text
travel rewards, overseas purchases, foreign transaction fees, rewards,
partner retailers, travel spending, flights/hotels/trains/car rental,
annual fee, APR, eligible spending
```

## REC editorial pattern that beat the old Zeus version

Raquel’s REC beat the earlier Zeus REC because it opened with the user-facing promise, not the existence of facts.

Bad pattern:

```text
{Card} highlights its confirmed costs and benefits.
```

Better pattern:

```text
{Card} offers up to {specific headline benefit}.
```

Then immediately connect the benefit to user intent:

```text
- debt / interest pressure / repayment control for balance transfer
- travel value / foreign-fee savings / eligible travel spend for travel rewards
- everyday shopping / cashback return / no annual fee for cashback cards
```

## REC benefits structure

When there are 4+ concrete benefits, prefer a short scannable list under `Key Benefits` rather than only dry paragraphs.

Explain fees as a trade-off, not as a bare fact:

```text
The transfer fee matters, but the trade-off can make sense when the
interest-free window creates real savings and breathing room.
```

## P1 must not default to generic technical context

P1 should start with the real user problem/outcome, then move to APR, fees and application mechanics.

Balance transfer P1 context:

```text
existing card debt, interest charges, multiple repayments, repayment path,
control, promotional window, fee vs avoided interest
```

Travel rewards P1 context:

```text
planned trips, hotels, transport, overseas purchases, partner retailers,
foreign purchase fees, reward value, repayment discipline
```

If a travel rewards card includes “foreign transaction fees”, do not let the P1 route fall into a generic `low-rate`/`low cost` framing. Travel/rewards intent takes priority over low-rate framing when the card name or benefits contain travel/rewards signals.

## LazyBlock tags

Block/avoid:

```text
2, 24, 2.99, Over 1, Transfer fee, Official terms,
Credit card, Card benefits, Balance transfer when already in card name
```

Prefer commercial, user-visible hooks:

```text
30 mo 0%, No FX fees, Travel rewards, No annual fee, Cashback
```

## Image sourcing rule

If Rodolfo does not supply a card image URL, search for the correct card image independently before blocking. Use the official issuer page first. Block only when identity/semantics cannot be validated.

A small but semantically correct official/manual card image may proceed as a warning after normalization/upscale. Continue blocking wrong product, mockups/cellphone/hand scenes for the card LazyBlock, or identity mismatch.

## Featured image audit nuance

For REC featured images, require realistic contextual/lifestyle hero artwork and preserved card identity, but do not require a person/hand in every REC image. For P1 featured images, person/hand requirement remains useful because the P1 hero needs layered application/context emphasis.

## Validation expectations before reporting success

Before saying REC+P1 is done:

```text
- public HTTP 200 for REC and P1
- card image visible on both
- featured image visible on both
- P1 contains official URL
- Yoast SEO/readability pass
- semantic QA OK
- REC/P1 similarity below threshold
- no editorial cache use
- check P1 title/heading matches actual card intent, not just QA pass
```

QA can pass while framing is still wrong, e.g. Travel Reward accidentally titled as Low Rate Costs. Always review the first visible paragraphs and major headings for intent alignment.