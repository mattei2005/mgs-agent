# REC benchmark cleanup helper

Purpose: deterministic cleanup checklist/script pattern for a single REC benchmark article before recreating it in a fresh thread.

Inputs to adapt before use:

- `SITE_KEY` (example: `eggbev`)
- `POST_ID`
- `CARD_SLUG` (example: `mbna-credit-card`)
- optional known media IDs from the runner/audit output

High-level pattern:

```python
# Pseudocode, not a drop-in credential script.
# Use content-publish-wordpress credential resolver and keep credentials out of chat.

post = wp_get(f"/wp-json/wp/v2/posts/{POST_ID}?context=edit")
assert CARD_SLUG in post.slug or CARD_SLUG.replace('-', ' ') in post.title.lower()

media_ids = {post.featured_media} | extract_lazyblock_media_ids(post.content.raw)
media_ids |= known_media_ids_from_runner_output

wp_delete(f"/wp-json/wp/v2/posts/{POST_ID}?force=true")

for media_id in media_ids:
    media = wp_get(f"/wp-json/wp/v2/media/{media_id}?context=edit")
    if CARD_SLUG in (media.slug + media.title + media.source_url).lower():
        wp_delete(f"/wp-json/wp/v2/media/{media_id}?force=true")

sqlite_delete("card_cache", "card_slug = ?", [CARD_SLUG])
sqlite_delete("cache_access_log", "card_slug = ?", [CARD_SLUG])

verify post REST is 404
verify media REST is 404
```

If server/origin access is available, remove only physical files matching the scoped card slug or post ID:

```bash
WP=/home/runcloud/webapps/<webapp>
find "$WP/wp-content/uploads" -type f -iname "*${CARD_SLUG}*" -delete
find "$WP/wp-content/cache" -type f \( -iname "*${CARD_SLUG}*" -o -iname "*${POST_ID}*" \) -delete
```

Never delete broad cache directories or unrelated media for a one-article benchmark cleanup.