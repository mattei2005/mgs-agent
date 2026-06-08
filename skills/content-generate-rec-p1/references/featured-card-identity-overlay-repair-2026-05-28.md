# Featured card identity overlay repair — 2026-05-28

## Trigger

Use this reference when REC/P1 featured-image generation fails semantic audit because the generated image changes the card identity, adds a second/different card, produces CGI/prohibited render artifacts, or alters visible card text/branding.

This came from the Eggbev `gb-cc-en` RBS Reward Black REC+P1 run. The orchestrator correctly blocked publication after generated featured attempts showed issues such as a second card, wrong branding/text (`Block Credit` instead of `Black Credit`), and CGI-style composition.

## Durable lesson

For credit-card featured images, preserving the exact card identity matters more than aesthetic generation. If the image generator cannot preserve the card reliably, do not keep retrying full-card generation. Generate only the realistic lifestyle/finance background with no cards/logos, then overlay the validated real card asset yourself.

## Repair pattern

1. Validate or fetch the card art first.
   - Prefer official/source-safe card art.
   - Confirm identity visually and via URL/source context.
   - Use this same validated card asset for LazyBlock and for featured overlays when possible.

2. Generate or select a background that contains no cards, logos, text, bank names, or card-like objects.
   - Background should be realistic/contextual enough to pass featured audit.
   - Examples: desk, phone, wallet, travel/planning scene, finance workspace.
   - Avoid abstract/generic gradients if the auditor expects realistic context.

3. Compose the featured image locally.
   - Canvas: 1280x720.
   - Place the real validated card at readable size with shadow and safe padding.
   - Do not rotate/crop so aggressively that the physical cut-out, corners, or branding change.
   - Produce distinct REC and P1 concepts/URLs/media IDs.

4. Audit the composed image against the card source.
   - `scripts/audit-featured-image.py --image <featured> --card-image <card> --card-name "<card>"`
   - Required: identity preserved, no second/different card, theme relevant, not generic stock, no bad artifacts.

5. Publish only after audit passes and public pages verify the expected featured media.

## Reporting

In the final REC+P1 report, disclose the blocked generated-featured attempt as evidence that gates worked, not as a failure hidden from the user. Include:

- final featured media IDs/URLs;
- audit OK for REC/P1;
- confirmation that bad/temporary media from failed attempts was removed or returns 404;
- note if the workflow switched from full generative card image to background + real-card overlay.

## Do not persist

Do not preserve API keys, one-off generation endpoints, temporary credential commands, or provider-specific transient setup errors in this reference. Capture only the durable repair pattern.