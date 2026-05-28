# Manual banner card extraction and rotation — HSBC Rewards correction (2026-05-28)

## Trigger

Use this when Rodolfo/Raquel supplies a `--card-image-url` that is not a clean card asset, but a full article/banner/social image containing:

- wide white or colored canvas;
- headline/promotional text outside the card;
- decorative background waves/shapes;
- the actual card shown in portrait/vertical orientation inside the banner.

The LazyBlock card image must be the card artwork only, not the whole banner.

## Durable rule

If the supplied manual card image contains a card inside a larger banner/canvas, the pipeline must:

1. Detect and crop the internal card object.
2. Remove the surrounding canvas/headline/decorative background.
3. If the internal card is vertical/portrait, rotate it to horizontal before upload.
4. Apply a conservative rounded-card alpha mask when needed.
5. Use the extracted horizontal card as the LazyBlock image and as the source for REC/P1 featured images.
6. Regenerate featured images after replacing the card asset, because featured scenes may preserve the wrong vertical/banner card.
7. Re-run semantic image audit, public verification and Yoast/readability checks before reporting success.

Do not treat a landscape source image as valid merely because the overall banner is horizontal. Inspect the actual card inside the image.

## HSBC Rewards incident pattern

The supplied image was a 450×250 banner with text on the left and a vertical HSBC card on the right. The first run uploaded the full banner normalized/upscaled. Rodolfo corrected that the expected behavior was to extract the card, rotate it and use only the card.

Correct repair sequence:

- Extract right-side card object from the banner.
- Rotate portrait card 90° to horizontal.
- Upload new card media.
- Update REC and P1 LazyBlocks to the new card media ID/URL.
- Regenerate REC and P1 featured images using the corrected card.
- Update featured_media and any inline featured image references.
- Delete old wrong media safely if not referenced.
- Verify public pages no longer reference the old card media.

## Verification checklist

Before final report, verify:

```text
new card URL appears in REC public HTML      | required
new card URL appears in P1 public HTML       | required
old card URL absent from REC/P1 HTML         | required
REC featured_media points to regenerated art | required
P1 featured_media points to regenerated art  | required
image audit with corrected card              | pass
Yoast/readability after update               | pass
```

Visual QA question to ask the vision model or reviewer:

> Does this image show only the extracted card in horizontal orientation, without the original banner/headline/canvas?

## LazyBlock containment rule

A technically correct extraction can still render badly inside the LazyBlock if the card asset is edge-to-edge or uses fragile transparency. After extraction/rotation, create a presentation-safe asset for the LazyBlock:

- center the corrected card on a 16:9-ish containment canvas (for current MGS LazyBlock, `900×528` worked well);
- keep visible padding/respiro around the card so the CSS/container does not clip the right/left edge;
- preview on the same kind of background the LazyBlock will show, not only on transparent/black viewers;
- if transparency exposes edge artifacts, flatten onto a neutral light-gray background similar to the card container rather than shipping a transparent PNG with jagged/notched edges;
- inspect the actual public page screenshot after update, because standalone image QA can pass while the LazyBlock crop/object-fit exposes a defect.

Visual QA question for this second pass:

> In the LazyBlock/page context, is the card fully contained with padding, without clipped edges, notches, banner text or decorative canvas?

## Pitfalls

A card-normalizer that only rotates when `image.height > image.width` misses this class of failure, because the full banner can be landscape while the card inside it is portrait. The detector must look for the internal card object, not only the outer image aspect ratio.

Do not stop after “better than before.” Rodolfo may still reject the asset if the LazyBlock exposes a visible notch/cutout, clipped side, or edge artifact. Iterate until the page-context view is acceptable, then update both REC and P1 to the final asset and verify that all intermediate URLs disappeared from public HTML.

Quality can still fail after a technically correct crop if the supplied banner is small. In the HSBC Rewards repair, the first extracted card came from a 450×250 third-party banner and looked pixelated in the LazyBlock. The correct second-pass repair was to search the issuer page/static assets, retrieve the original HSBC DAM image instead of the low-res rendition, crop the card from that official source, rotate it horizontal, then add containment padding/final background treatment before updating REC/P1 again. If a URL contains an AEM rendition segment like `/_jcr_content/renditions/cq5dam.web.1280.1280.jpeg`, inspect available `srcset`/DAM alternatives before accepting the first rendition as the best source.
