# REC existing draft manual image repair

Use this reference when Rodolfo/Raquel asks to fix an already-created REC draft because a user-supplied card image was ignored, especially when the post must stay as the same draft and no new post may be created.

## Trigger

- User says to correct an existing draft/post.
- They provide a `Post ID` and a direct image URL.
- They explicitly say: keep draft, do not create a new post, apply the image to the LazyBlock/card image, and regenerate the featured image from the same source.

## Key lesson from MBNA 62092

The normal `mgs-rec-runner.py` direct path creates a post. It supports manual image creation with:

```bash
--card-image-url "https://...jpg"
```

But it does **not** currently expose a `--post-id` / update-existing-post mode. If the task is to repair an existing draft, do not rerun the normal create-post runner unless the runner has gained a supported update flag. Creating another post violates the correction request.

## Repair pattern

1. Confirm the target post exists and is the expected status via WordPress REST `GET /wp-json/wp/v2/posts/<post_id>?context=edit`.
2. Download the manual image URL with a normal browser-like User-Agent.
3. Validate dimensions/aspect ratio locally. Normalize the manual image before upload:
   - Preferred helper: `/root/mgs-agent/scripts/normalize-card-artwork.py <input> <output.png> --aggressive`
   - Use PNG output so rounded card corners keep transparency; JPEG bakes the old thumbnail/background color into ugly corners.
   - For card/LazyBlock image, the final `card_selection` should record:
   - `mode: manual_card_image_url`
   - `source: <manual URL>`
   - width, height, aspect
   - `card_normalize.manual_crop_applied: true` when canvas/borders were removed
4. Upload the normalized manual card image with `content-publish-wordpress/scripts/upload-image.sh`.
5. Generate the featured image from that exact local manual card file with `content-generate-rec/scripts/generate-featured-image.sh`.
6. Upload the new featured image.
7. Fetch the current post content and replace only the `imagem` field inside the `<!-- wp:lazyblock/credit-card {...} /-->` attributes:
   - Decode/edit the block JSON safely with Python/JSON, not regex string surgery alone.
   - The `imagem` value is URL-encoded JSON containing the WP media object.
   - Preserve the article body, CTA, title, tags, and status unless the user asked for more changes.
8. `PUT /wp-json/wp/v2/posts/<post_id>` with:
   - `status: draft` when the user said to keep draft
   - updated `content`
   - `featured_media: <new_featured_id>`
9. Re-run Yoast update/scoring on the same post ID if content or featured changed.
10. Safe-delete only the old card/featured media after verifying they are no longer referenced:
    - use `delete-media-safe.sh <site> <media_id> <post_id>`
    - never delete if the media is still `featured_media`, referenced in HTML, or attached elsewhere.
11. Verify final post state:
    - same post ID
    - status unchanged as requested
    - `featured_media` equals the new featured ID
    - content contains the new card URL/ID
    - content no longer contains the old automatic card image URL/ID

## Final report requirements

For manual-image repair summaries, include:

```text
Post ID
Status
Edit link
No new post created: PASS
card_selection.mode = manual_card_image_url
manual image source URL
updated card/LazyBlock image ID + URL
updated featured ID + featured_url
artifact audit: created, used, old extras, deleted
Yoast scores if rescored
cost: runner/image known cost plus session operational cost when available
```

If the current session tool output cannot expose the Hermes operational session cost helper/state query, say the operational cost is not available from the current output rather than inventing a value.

## Pitfalls

- Do not pass manual images only via env vars for normal creation. The runner contract is `--card-image-url`.
- Do not create a replacement post when the task says to correct the existing draft.
- Do not report success for manual-image benchmarks unless the actual recorded mode is `manual_card_image_url`.
- Do not delete old media before the WordPress post update has been verified.
- Do not expose WordPress credentials or tokens in logs or chat.
