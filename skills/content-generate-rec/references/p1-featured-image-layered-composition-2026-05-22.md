# P1 featured image layered composition — 2026-05-22

## Trigger

Use this when creating, repairing, auditing, or updating a P1/application-page featured image, especially when the user complains that the image looks like only a card on a background or the card is cropped/misaligned.

## Durable rule

For P1, the WordPress featured image and the contextual image inserted near the top of the article must be the same image. It must look like a professional advertising scene built in literal layers, not a simple card-only mockup.

Mandatory layer order:

1. **Background/base:** a realistic contextual scene filling the full composition, with depth and a real environment. Acceptable contexts include office, airport, café, travel, corporate/lifestyle, shopping, or other card-relevant scenes. It must not look like a blurred backdrop pasted behind the product.
2. **Main element:** the exact card artwork, centred, slightly enlarged, visually valued, naturally integrated, and completely inside the safe area. No cropped corners and no overflow at the bottom/top/sides.
3. **Front layer:** a realistic human character/person in the foreground, with soft natural overlap over the card. The person humanises the image but must not hide important card information.

## Card integrity gates

- Never add borders, frames, moulding, glow outlines, badges, stickers, or graphic elements around the card.
- Keep the card clean and in its original shape.
- Improve only quality, sharpness, resolution, alignment, orientation, and proportion.
- If the source card is vertical, rotate/adapt to horizontal when required by the established card standard.
- Never invent, reconstruct, redraw, recolour, or recreate card details. The card identity must remain exactly the same as the article's original card image.

## Runner/prompt implementation lesson

The old P1 repair path generated a contextual scene, blurred it, darkened it, and overlaid the exact card manually. That was reliable for preserving the card but produced a card-only/overlay look and could place the card too low or outside the safe area. The better default is to make the P1 image prompt itself request the layered advertising scene and then only normalize/crop/compress the final image, not paste a giant standalone card over the scene.

When the exact card must be preserved after generation, avoid making the repair look like an obvious paste-up. If manual overlay is unavoidable, keep the card fully safe, proportional to the hands/person, use only natural contact shadows, and visually validate before upload.

## Verification checklist before reporting success

1. Public post uses the new media ID as `featured_media`.
2. The same featured image appears inside the article near the top.
3. Image is 16:9 and fully fills the frame.
4. Scenario has depth and does not look like a plain/blurred background.
5. Card is central/valued, completely inside safe area, and not cropped.
6. A realistic person is present in the foreground or immediate scene layer.
7. Card has no added frame/border/glow/badge and no redesigned details.
8. Use `vision_analyze` on the final local or uploaded image and explicitly check for artificiality, card overflow, card identity changes, and missing human layer.

## Reporting note

When repairing an already published P1, keep the user-facing summary short and operational: confirm the image was replaced, show public link and featured image link, include word-count differences if relevant, Yoast scores, tags, duration/cost, and mention Raquel when the article is published.