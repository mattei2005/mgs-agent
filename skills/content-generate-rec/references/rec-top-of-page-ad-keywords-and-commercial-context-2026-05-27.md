# REC top-of-page ad keywords and commercial context — 2026-05-27

## Trigger

Use this reference when improving, auditing or generating REC articles, especially REC+P1 credit-card flows where the REC routes users to P1 and triggers monetisation events.

## Lesson

Rodolfo clarified that REC is the commercial heart of REC+P1. On mobile the page order is effectively:

```text
Title
Summary / first paragraph
Ad block
LazyBlock card
P1 button / interstitial path
```

Because an ad appears before the card, the title/summary and first 1-2 visible paragraphs are not just editorial copy. They are a monetisation surface. They must carry the highest-value commercial intent keywords so Google can match better advertisers and so the user has a reason to continue to the P1.

## What failed

Weak REC opening pattern:

```text
<card> highlights its confirmed costs and benefits.
```

This is technically correct but commercially weak. It does not surface the strongest benefit, user pain, or ad-relevant keywords before the first ad block.

## Better pattern

For balance-transfer cards, the top of the REC should immediately include:

- `balance transfer`
- `0% interest` / `interest-free`
- promotional duration, e.g. `30 months`
- `existing card debt` / `card debt`
- `repayments`
- `interest pressure` / `interest savings`
- `transfer fee` when relevant
- `financial control`, `breathing room`, `simplify monthly payments` when supported by facts

Example top-of-page copy:

```text
Nationwide Balance Transfer Credit Card offers up to 30 months interest-free balance transfers.

Nationwide Balance Transfer Credit Card is built for users who want to cut interest pressure on existing card debt and organise repayments with more control.

Its strongest hook is 0% interest on balance transfers for the first 30 months, giving borrowers more time to simplify monthly payments before interest starts building again.

The transfer fee matters — 2.99% balance transfer fee; minimum £5 — but the trade-off can make sense when the interest-free window creates real savings and breathing room.
```

## REC vs P1 distinction

REC should sell the reason to click through. P1 can explain the full decision.

```text
REC = commercial hook + ad-relevant keywords + P1 click motivation.
P1  = deeper context, eligibility, application path, fee/APR explanation and official CTA.
```

## QA rule

Block REC output when:

- first sentence/summary says only `confirmed costs and benefits`, `highlights real benefits`, or similar inventory language;
- balance-transfer REC top section lacks commercial intent keywords;
- balance-transfer REC top section lacks user pain/outcome language around debt, repayments, interest pressure, savings or financial organisation;
- fee is only listed and not framed as a trade-off against interest saved/time gained.

## Runner implication

The runner should generate top-of-page copy first from the product type and strongest benefit, not from generic metadata. For balance-transfer products, derive a dedicated top section before assembling the LazyBlock/card.