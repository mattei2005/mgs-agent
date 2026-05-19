# REC manual card image override

Use when Rodolfo/Raquel provides a direct card image URL in a REC request, e.g. `Imagem do cartão: https://...jpg`, `Imagem manual: ...`, or `card image: ...`.

## Durable rule

A user-supplied card image is an explicit override, not a hint. The REC runner must use it for:

- LazyBlock `credit-card` image
- featured image source/reference
- final audit/reporting

A manual-image run only passes when the runner output includes:

```text
images.card_selection.mode == manual_card_image_url
```

If output shows `auto_ranked_card_image`, the manual-image objective failed even if the draft/post was created successfully.

## Runner contract

Preferred CLI shape:

```bash
/root/mgs-agent/scripts/mgs-rec-runner.py \
  --site <site_key> \
  --card "<exact card name>" \
  --status <draft|publish> \
  --source-url "<official URL>" \
  --card-image-url "<direct image URL>"
```

Do not pass manual images only as loose environment/context text. The runner has defensive env fallbacks (`MGS_CARD_IMAGE_URL`, `MGS_MANUAL_CARD_IMAGE_URL`) for agent mistakes, but the CLI flag is the source-of-truth contract.

## Cache interaction pitfall

If a card has cached `card_image_uploaded_id` / `card_image_uploaded_url`, the manual override must still win. The runner should ignore cached image media whenever `--card-image-url` or its defensive env fallback is set.

Failure pattern from the MBNA benchmark: cache hit + manual URL in prompt + Atena did not pass `--card-image-url` caused the runner to reuse/search automatic media and report `auto_ranked_card_image`.

## Validation checklist

For a safe dry-run proof:

```bash
MGS_CARD_IMAGE_URL='<direct image URL>' \
python3 scripts/mgs-rec-runner.py \
  --site eggbev \
  --card "MBNA Credit Card" \
  --status draft \
  --source-url "https://www.mbna.co.uk/credit-cards.html" \
  --dry-run
```

Expected evidence:

```text
success: true
steps includes: manual_card_image_override_requested
steps includes: dry_run_manual_card_image_validated
images.card_selection.mode: manual_card_image_url
images.card_selection.width/height/aspect present
validation.status: PASS
```

## Image quality note

A direct image URL can be technically valid but editorially poor (e.g. YouTube thumbnail/banner). If Rodolfo provides it as a benchmark override, respect it and report quality caveats separately. Do not silently replace it with automatic search.

Manual images still go through card-art normalization before upload/featured generation. The runner should crop white/transparent padding and, for manual overrides, apply aggressive flat-background canvas crop so a user-supplied thumbnail such as a 1280x720 image with a small centered card becomes card-only artwork for the LazyBlock. Manual normalized card images should be saved/uploaded as PNG so rounded corners can keep transparency; saving the crop as JPEG bakes the flat thumbnail background into ugly corner/border artifacts.

Expected evidence for manual image normalization:

```text
images.card_normalize.manual_crop_applied: true/false
images.card_normalize.crop_method: background_canvas_crop | white_or_transparent_trim | null
images.card_normalize.before/after: dimensions before and after crop
```

If the user explicitly asked for a bordered/manual image to be cropped and `manual_crop_applied=false`, report the caveat; do not claim card-only normalization succeeded.

Manual image LazyBlock gate: after normalization, if the useful card crop is small/rough for an isolated LazyBlock asset, report `manual_card_image_low_quality_source` with the pre-upscale useful crop width. If aggressive background removal creates internal transparency/checkerboard or removes colours that are part of the card design, reject that normalization and preserve original RGB colours with a rectangular/card-edge crop instead. Do not silently replace a user-supplied benchmark image with automatic search, but also do not present a low-resolution or visually damaged crop as production-quality. Do **not** use AI/Gemini to recreate or enhance an isolated card-only LazyBlock asset unless the user explicitly approves a generated substitute; generated card-only assets can change text, edges, shadows, and brand design.card workflow for explicit manual benchmarks: it creates a high-resolution card-only product asset from the supplied reference and records `manual_card_image_url_enhanced`. Do not use colour-key transparency on the card interior; crop the flat canvas tightly and apply only a conservative rounded-corner alpha mask so teal/blue details inside the card are not punched out.

## Manual crop quality gate

Do not treat `manual_crop_applied=true` as a full visual PASS. It only proves the canvas/border was removed. After aggressive crop, validate source quality separately:

```text
Gate                                | Action
------------------------------------|------------------------------------------------------------
final card width < 600px             | report LOW_QUALITY_SOURCE; ask for better source or use auto fallback
text/logos visibly pixelated         | report LOW_QUALITY_SOURCE; do not call it production-ready
PNG alpha/borders clean but image soft| say border fixed, quality still failed
featured looks good but card poor    | do not infer card quality from featured; Gemini can mask/recreate defects
```

Lesson from MBNA 62092: YouTube `maxresdefault` was 1280x720, but the actual card occupied only ~442x288 after crop. The PNG transparency/border fix was technically correct, yet the LazyBlock card remained poor because the source was low-resolution/compressed. Recropping the same URL will not recover detail; replace the source with a higher-quality official/comparison-site card-only image.

## Auto-image fallback lessons

When no manual image is provided, automatic selection should prefer isolated product/card artwork. Penalize or skip contextual marketing assets for LazyBlock:

- person/people/woman/man
- hand/hands
- phone/mobile/app/screenshot/screen
- Apple Pay / Google Pay scenes
- virtual assistant/support/decline/call-us pages
- YouTube/ytimg/Google Play/social thumbnails
- cross-country issuer domains when the official URL is country-specific, e.g. MBNA UK should not pick MBNA Canada

If the fallback picks a clean but generic comparison-site image, report it as acceptable with caveat instead of claiming it is perfect card-only art.