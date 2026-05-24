# P1 runner from existing REC — stale official URL and word-count expansion repair (2026-05-20)

## Context

While creating a published GB-CC-EN P1 for Barclaycard Platinum from an existing REC URL, `mgs-p1-runner.py` correctly inferred the P1 slug from the REC button:

- REC: `https://eggbev.com/rec-gb-cc-barclaycard-platinum/`
- P1 slug: `apply-now-gb-cc-barclaycard-platinum`

The first run failed before publication because the REC/reference contained an old product-level Barclaycard URL that now returns 404:

- stale URL: `https://www.barclaycard.co.uk/personal/credit-cards/platinum`
- current official source used: `https://www.barclaycard.co.uk/personal/credit-cards/balance-transfer-credit-cards`

A second run with `--official-url` plus explicit official facts passed source extraction but failed validation because the P1 body stayed below the hard 900-word limit after the built-in filler expansion:

`P1 body word count below hard limit after expansion: 841`

## Durable workflow lesson

When generating a P1 from an existing REC:

1. Trust the REC button/apply URL as the source of truth for the P1 slug.
2. Do not assume the official URL stored in the REC remains live.
3. If the runner fails with `reference_url fetch failed ... 404`, find the current official issuer page using a bounded official-source check, then rerun with:
   - `--official-url "<current official URL>"`
   - `--annual-fee "..."`
   - `--apr "..."`
   - repeated `--benefit "..."`
4. If the current official page is a category/listing page rather than a product detail URL, it is acceptable only when the page clearly names the target product and shows the official terms used in the P1.
5. **Updated hard gate 2026-05-24:** explicit facts/cache/REC copy cannot override an official URL that has no usable product content. If the issuer URL returns a branded 404/error/search shell or lacks product facts, stop before publish and ask Raquel/Rodolfo for the correct official link.
6. If the REC LazyBlock card image is empty, do not silently inject a cache/manual/external image into the P1. Stop and ask Raquel for the correct card image or repair the REC image first; any replacement must pass horizontal card-only crop/normalization before upload.
7. If the runner fails before publication on word-count validation, patch the deterministic expansion logic rather than manually publishing an under-limit P1.

## Runner repair applied

`/root/mgs-agent/scripts/mgs-p1-runner.py` had only seven expansion paragraphs in `fit_word_count()`, which was insufficient for this balance-transfer P1. Three additional balance-transfer-specific filler paragraphs were added:

- confirm transfer window, transfer fee and post-promotional interest rate;
- set a repayment plan before the promotional period ends;
- avoid transferring more than can realistically be repaid and note missed-payment risk.

This raised the generated body to 904 visible words and allowed the runner to publish normally.

## Reporting detail

If a failed first attempt uploaded an unused featured image, use the safe media cleanup path before the final summary. In this case:

- first attempt uploaded an extra P1 featured image;
- successful attempt uploaded the used featured image;
- unused media was deleted with `delete-media-safe.sh` after verifying it was not the final post featured media or referenced in content.

Final user summary should report the media audit as created/used/extra/deleted, not only the successful image.
