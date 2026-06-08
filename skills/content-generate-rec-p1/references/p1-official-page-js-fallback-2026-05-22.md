# P1 runner fallback for JS-heavy official pages

## When this applies

Use this note when creating or updating a P1 from an existing REC and the official issuer page is visible in a browser but the deterministic fetch used by the runner returns too little text, commonly with JavaScript-heavy issuer pages.

Observed with the British Airways American Express Premium Plus Card official page. Browser-rendered text contained the fee, APR, Avios earning and Companion Voucher details, while the non-rendered fetch only exposed the page title, causing `reference_url returned too little fetchable text for deterministic extraction`.

## Durable workflow lesson

Do not abandon the P1 when the official page is browser-readable but fetch extraction is short. Provide explicit, source-confirmed facts to the P1 runner using its supported flags:

- `--official-url <official issuer URL>`
- `--card <short SEO-safe card name>`
- `--annual-fee <exact source-backed fee phrase>`
- `--apr <exact source-backed APR/purchase-rate phrase>`
- one or more `--benefit <source-backed benefit>` flags

This keeps the runner deterministic and avoids manual WordPress assembly.

## SEO/title guardrail

If the official product name makes the P1 title exceed the title character limit, prefer a shorter recognized card name via `--card`, while keeping the official issuer URL and source-backed facts intact.

Example: use `British Airways Amex Premium Plus` instead of the full formal Amex product name when needed for title length.

## Cleanup guardrail

If a first P1 creation succeeds but needs an immediate update for title/focus-keyphrase length, update the existing post with `--update-post-id` rather than creating a duplicate. If the update creates a replacement featured image, delete the earlier unused featured media safely so the media library does not keep orphaned P1 assets.

## Verification expectations

Before reporting completion, verify the public P1 URL returns 200 and contains:

- the official issuer URL,
- the current featured image,
- the card image,
- CTA/apply copy,
- expected Yoast schema word count or equivalent public word-count signal.
