# P1 Lloyds source + card-image hard gates (2026-05-24)

## Context

A P1 for Lloyds World Elite Mastercard was first published from an existing REC while:

- the originally used Lloyds official URL opened as an issuer error/Page not found page rather than product content;
- the REC LazyBlock card image was empty;
- a correct external card image was inserted, but the image was not normalized/cropped to remove its surrounding border/background before being used.

Rodolfo corrected the workflow: the issue with the card image was not that the selected card artwork was wrong; it was that Atena failed to remove borders/background and normalize it before use.

## Durable rules

1. **Official-source content gate for P1**
   - Do not publish a P1 when the official/source URL has no usable product content.
   - HTTP 200 is not enough. Reject branded 404 pages, issuer error shells, geo-block pages, empty bodies, search pages, or pages that lack product facts.
   - Stop before publication and ask Raquel/Rodolfo for the correct official link.
   - Explicit facts, cache data, REC copy, or secondary sources must not override a dead official URL for a publish run.

2. **Reader fallback boundary**
   - A reader/render fallback may be used only for the same official issuer URL.
   - The canonical source remains the issuer URL.
   - Do not substitute comparator/blog content as the official source.

3. **REC card image gate for P1**
   - When creating a P1 from an existing REC, the card image should come from the REC LazyBlock after it has passed the card-image quality gate.
   - If the REC LazyBlock image is empty, stop or repair the REC image first; do not silently inject a cache/manual/external image directly into the P1.
   - If a replacement image is used, it must be normalized before upload.

4. **Card image normalization is mandatory**
   - A visually correct card image still fails if it keeps a banner background, large borders, canvas padding, decorative background, or uncropped source frame.
   - Required output for the card slot: horizontal card-only image, tightly cropped/transparent or clean background, issuer/card identity preserved, no large empty canvas.

## Implementation pattern

For Lloyds World Elite in this incident:

- Correct official URL supplied by Rodolfo: `https://www.lloydsbank.com/credit-cards/mastercard-world-elite.html`.
- Direct fetch may still return a Lloyds error shell from non-UK automation.
- A reader rendering of the same official URL can expose product content, and is acceptable as a rendering aid when the canonical source remains the Lloyds URL.
- The card artwork from Head for Points was acceptable, but had to be cropped/normalized before use.

## Reporting lesson

Never report “official source validated” unless the source content itself was validated as product content. If a post was accidentally published through a failed gate, take it out of public circulation first, then repair and republish only after the source/image gates pass.
