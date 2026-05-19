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