# Manual card image validation and MBNA teardown lessons

Use this reference when a REC uses a user-provided/manual card image or when a test article must be deleted and recreated from scratch.

## Manual card image is an override, not a suggestion

When the user provides a manual card image URL, do not silently replace it with an automatic/fallback image. If the source is low quality, keep the user-selected source as the basis and use a controlled enhancement/card-only workflow. Report warnings clearly instead of switching to a different card image.

## Pre-publish visual gate for LazyBlock card images

Before publishing or updating the LazyBlock card image, visually/technically validate the final asset that will be uploaded, not just the source image.

Block or repair the image if any of these are present:

- visible checkerboard pattern or preview-transparency background;
- large 16:9 canvas with a small card floating inside;
- excessive margins around the card;
- leftover colored halo/border from the source background;
- holes/transparent artifacts inside the card design;
- card identity not matching the product requested;
- card is too small because a thumbnail crop was simply upscaled.

Acceptable LazyBlock card image shape:

- card-focused image, preferably tight crop;
- clean background, usually solid white for WordPress/LazyBlock reliability;
- card occupies most of the frame;
- no human/lifestyle scene in the LazyBlock card asset;
- no checkerboard, no fake transparency preview, no green/teal halo.

## Controlled enhancement workflow

If a manual source has useful crop width below the quality threshold, generate a card-only enhancement, then post-process it:

1. remove edge-connected checkerboard/light neutral background;
2. crop tightly around the non-background card area;
3. compose onto solid white RGB background;
4. re-check that the final file is card-focused and clean;
5. only then upload/use in LazyBlock.

Do not rely on Gemini output dimensions alone. A 1344x768 image can still be invalid if it contains a small card on a large checkerboard/canvas.

## Teardown for benchmark/test REC

When Rodolfo asks to delete a test REC and recreate it in a fresh thread, clean only that article/card scope:

1. delete the WordPress post with force=true;
2. delete attached/current media IDs and known generated media for that card;
3. clear the local runner cache rows for that card slug in `card_cache` and `cache_access_log`;
4. verify post and media return 404 via WordPress REST;
5. if server access is available, remove physical upload/cache files matching the specific card slug/post ID only;
6. verify origin 404 for the article and image URLs.

Cloudflare may continue serving old uploaded images with `CF-Cache-Status: HIT` after origin cleanup. Treat origin 404 as the important verification for the next runner test unless Cloudflare API credentials are available for a URL purge.