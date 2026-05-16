---
name: content-publish-wordpress
description: Utility skill to publish posts to WordPress (resolve credentials from 1Password, upload media, create/update posts, set Yoast SEO meta, resolve category/tag IDs). Called by other skills like content-generate-rec, content-generate-p1, content-generate-seo. Does NOT write article content — receives pre-assembled HTML.
---

# content-publish-wordpress

Shared utility skill that publishes content to WordPress sites configured in
`/root/mgs-agent/data/sites.json`. Handles every HTTP interaction with the WP
REST API so other skills can focus on generating content.

## When to use

Invoke this skill from another skill (never directly from the user) when you
need to:

1. Upload an image to the media library
2. Resolve a category or tag by name → ID (creating if missing)
3. Create a post with fully assembled HTML (including LazyBlock comments)
4. Apply Yoast SEO meta to an existing post (title / description / focus keyword)

## Required inputs

Every call must include a `site_key` matching a key in
`/root/mgs-agent/data/sites.json`. The skill reads that file to discover
`wp_url`, `publishing_user`, and `credentials_ref` (1Password pointer).

## Scripts

All scripts live in `./scripts/` and must be invoked via absolute path.

HTTP calls must use the centralized `wp_curl_auth_http` wrapper in `scripts/wp-curl-auth.sh` when capturing status codes. This keeps credentials out of argv, preserves 4xx/5xx bodies via `--fail-with-body`, returns real HTTP codes for REST errors, and reserves `000` for transport failures. See `references/wp-rest-curl-hardening.md` for the validation recipe and fake-curl probe.


### `resolve-credentials.sh <site_key>`
Reads `sites.json`, pulls the WordPress Application Password from 1Password via
`op item get`, and emits a JSON object:
```
{ "wp_url": "...", "username": "...", "password": "...", "author_id": 11 }
```

### `upload-image.sh <site_key> <image_path> <filename>`
Uploads `image_path` as `filename` to `/wp/v2/media` using Basic auth.
Emits: `{ "id": <int>, "source_url": "..." }`.

### `resolve-term.sh <site_key> <taxonomy> <name>`
`taxonomy` is `categories` or `tags`. Looks up the term by name (search); if
absent, creates it. Emits: `{ "id": <int>, "name": "...", "slug": "..." }`.

### `create-post.sh <site_key> <post_json_path>`
POSTs the JSON file at `post_json_path` to `/wp/v2/posts`.
Post JSON shape (caller responsibility):
```json
{
  "title": "...",
  "slug": "...",
  "content": "...",
  "status": "draft",
  "author": 11,
  "categories": [212],
  "tags": [456, 469, 214, 451, 219, 468],
  "featured_media": 61845,
  "meta": {
    "_yoast_wpseo_title": "...",
    "_yoast_wpseo_metadesc": "...",
    "_yoast_wpseo_focuskw": "..."
  }
}
```
Emits the full created post JSON from WP (includes `id`, `link`).

### `update-yoast.sh <site_key> <post_id> <yoast_json_path>`
Applies Yoast meta in the proven two-PUT pattern:
1. PUT `/wp/v2/posts/<id>` with only `{ meta: {...} }`
2. `sleep 2`
3. PUT `/wp/v2/posts/<id>` with `{ title, content, meta }` (content/title
   re-sent to trigger Yoast's `save_post` hook).
Emits `{ "ok": true, "post_id": <id> }` or a structured error.

The `yoast_json_path` file must contain:
```json
{
  "title": "...",
  "content": "...",
  "meta": {
    "_yoast_wpseo_title": "...",
    "_yoast_wpseo_metadesc": "...",
    "_yoast_wpseo_focuskw": "..."
  }
}
```

## Workflow a caller should follow

1. `resolve-credentials.sh eggbev` → cache in memory
2. `upload-image.sh eggbev /tmp/card.png card-aib-visa-gold.png` → card media
3. `upload-image.sh eggbev /tmp/featured.png featured-aib-visa-gold.png` → featured media
4. `resolve-term.sh eggbev categories "Credit Card"` → category id
5. For each tag: `resolve-term.sh eggbev tags "<name>"` → tag id
6. Caller assembles final post JSON (with raw HTML content containing LazyBlock
   comments) and writes to a tempfile
7. `create-post.sh eggbev /tmp/post.json` → `{id, link, ...}`
8. `update-yoast.sh eggbev <id> /tmp/yoast.json`
9. Return post link to the user

## Non-goals

- This skill does NOT generate text, headings, or LazyBlock payloads.
- This skill does NOT fetch images from the web or call Gemini.
- This skill does NOT decide tags, categories, or SEO copy — it only applies
  what the caller hands in.

## Logs

All scripts append to `/root/mgs-agent/logs/publish-wordpress.log` with
timestamp + action + HTTP status. On error, stderr receives a human-readable
message and exit code is non-zero.

## WP REST curl hardening

For scripts that call WordPress REST, use the centralized `wp_curl_auth_http` pattern documented in `references/wp-curl-http-wrapper.md`: preserve real HTTP 4xx/5xx status + body with `--fail-with-body`, return `000` only for transport failure, and keep credentials hidden via `curl -K` tempfiles.

## Querying WP post status from outside the pipeline (Zeus / audit use)

**Best source** — `logs/publish-wordpress.log`, grep for `create-post OK`:
```bash
grep "create-post OK" /root/mgs-agent/logs/publish-wordpress.log | tail -5
# e.g. → create-post OK http=201 site=eggbev id=61965
```
Gives the canonical post ID without touching WP REST API.

**Fetch post by ID** (no auth needed for published posts):
```bash
curl -s "https://eggbev.com/wp-json/wp/v2/posts/<ID>" | python3 -c "
import sys, json; p = json.load(sys.stdin)
print(p['id'], p['status'], p['slug'], p['title']['rendered'][:80])"
```

**eggbev.com REST API quirks (verified 2026-04-23)**:
- `Authorization: Basic <base64>` via `-H` fails silently on HTTP/2 (connection drops). Use `-u user:pass` instead.
- `GET /users/me` returns 401 even with valid app password — auth partially restricted.
- `?status=draft` / `?status=any` → 401 without working auth session.
- `?slug=<slug>` always returns `[]` — broken by plugin interference (known issue, see CLAUDE.md).
- `?search=rec` on public endpoint works but only returns published posts.
- Direct `GET /posts/<id>` is the most reliable query — works unauthenticated for published posts.
