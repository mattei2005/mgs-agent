# Tesco Balance Transfer REC+P1 runner fixes — 2026-06-08

## Context

REC+P1 publish for `Tesco Bank Balance Transfer Credit Card` on eggbev / gb-cc-en using official URL:

`https://www.tescobank.com/credit-cards/balance-transfer-credit-card/`

The session exposed several durable pipeline lessons for UK issuer balance-transfer cards and deterministic REC+P1 runners.

## Durable lessons

### 1. Official URL/title preflight must consider issuer hostname

The official page title was generic: `0% interest balance transfer credit card`. The path also did not include `tesco` or `bank`, but the hostname `tescobank.com` did.

Old behavior blocked with:

```text
official_url_title_mismatch ... missing_terms=['tesco', 'bank']
```

Durable fix pattern: when checking requested card terms against an official page, include the hostname/domain together with title + path before deciding issuer terms are missing. Generic product titles are common on issuer pages.

### 2. Tesco official page may expose a generic official card image

The page included this official usable image:

```text
https://forrit-one-tb-prod-cdn-p1-prod.azureedge.net/media-76a057a8-43e8-4899-a94d-aaa40249b955/3746884f-d21d-4e16-af52-395543379f1e/clubcard-plus-credit-card.png
```

It does not say “Balance Transfer” on the card face, but it is a clear official Tesco Bank generic credit-card visual and is acceptable when the surrounding LazyBlock/product text identifies the Balance Transfer Credit Card. Reject AI/generated competitor images with fake card text even if they look Tesco-themed.

### 3. Deterministic request facts need four specific facts

When extraction returns `annual_fee=N/A`, REC v2 blocks. Supplying only annual fee is not enough; the deterministic runner switches to request-facts mode only when both `--annual-fee` and at least one `--benefit` are present, and the REC contract requires at least four specific benefits/facts.

Verified facts from the official Tesco page used successfully:

```text
--annual-fee "No annual fee"
--apr "Representative 24.9% APR variable"
--benefit "0% interest on balance transfers for 36 months with a 3.45% fee"
--benefit "0% interest on money transfers for the first 9 months with a 3.99% fee"
--benefit "Collect Clubcard points almost every time you spend in and out of Tesco"
--benefit "Available to UK residents aged 18 and over, subject to status"
```

### 4. Balance-transfer REC top section must include enough intent keywords early

Semantic QA for balance-transfer REC expects the first visible sentences to include at least four of the balance-transfer top keywords and both offer + pain intent.

Useful early terms:

```text
balance transfer
interest free
months
existing card debt
repayments
interest pressure
```

Avoid opening copy that only repeats `balance transfer` + `existing card debt`; include duration, interest-free language and repayment/interest-pressure language before the card/ad area.

### 5. Avoid rewards/travel fallback from generic `points`

Tesco Clubcard points are rewards-related, but not automatically travel rewards. LazyBlock/tag derivation should not treat the word `points` alone as a travel signal. Only use travel-specific tags/descriptor when the official facts contain explicit travel terms such as `travel`, `Avios`, `lounge`, `hotel`, etc.

### 6. Featured image generation should preserve exact card identity deterministically

Gemini frequently altered small card text/dates when asked to include the card itself. A robust pattern is:

1. Generate only a realistic lifestyle/finance background.
2. Explicitly forbid generated cards/card-like rectangles in the prompt.
3. Composite the exact normalized card artwork over the generated background with ImageMagick.
4. Then run the semantic audit.

This improved card identity preservation and avoided fake card text.

### 7. P1 repeated-sentence QA can trigger on generic fee/APR benefit tails

For products with multiple fee/APR facts, avoid appending the same sentence tail to every `fee`/`APR` fact. Vary the second sentence by fact type, e.g. use a distinct money-transfer cost explanation instead of repeating:

```text
Read this as part of the total cost, because interest or fees can quickly reduce any benefit.
```

### 8. REC meta description repair must hard-cap after punctuation cleanup

Truncation + `clean_sentence_punctuation()` can push meta description length back over the 140-char contract limit. After cleanup, re-check length and hard-cap again before final validation.

## Successful artifacts from the session

- REC post: `62425`
- P1 post: `62429`
- REC Yoast after repair: SEO `88`, Readability `90`
- P1 Yoast: SEO `90`, Readability `90`
