---
name: content-generate-rec
description: Generates a REC (Recommendation) article for a credit card — fetches card data from the official URL, finds/processes the card image, generates a featured composition image via Gemini, assembles the article from the country/language/vertical-specific template, and publishes it to WordPress via content-publish-wordpress. Selects the right template automatically based on the site's template_key.
---

# content-generate-rec

Generates and publishes a REC (Recommendation) article for a credit card to a
WordPress site, using a per-site template selected from `template_key`.

## Inputs

Required:
- `card_name` — exact name of the card (e.g. "AIB Visa Gold Card")
- `card_official_url` — official bank page (source of truth)
- `site_key` — key in `/root/mgs-agent/data/sites.json` (e.g. "eggbev")

Optional:
- `status` — `draft` (default) or `publish`

## Template selection (CRITICAL)

Templates live in `./templates/` named `rec-{template_key}.md`.

Workflow:
1. Read `/root/mgs-agent/data/sites.json` and extract the entry at `site_key`
2. Read `template_key` from that entry (e.g. `gb-cc-en`)
3. Load `templates/rec-{template_key}.md`
4. If the file does NOT exist, FAIL immediately with a clear message:
   `No REC template for template_key '<template_key>'. Create templates/rec-<template_key>.md first.`

Adding support for a new country/vertical/language = adding a new template
file. No skill code changes required.

Current templates:
- `rec-gb-cc-en.md` — United Kingdom, Credit Cards, English

Future (examples, not yet present):
- `rec-us-cc-en.md`, `rec-mx-cc-es.md`, `rec-de-cc-de.md`, `rec-br-loans-pt.md`

## Workflow

Execute in this strict order. Never skip the word-count validation or the
image integrity check.

### 1. Load config & template
- Read `sites.json[site_key]` → `wp_url`, `publishing_user.id`, `template_key`,
  `default_category`, `domain`, `country`, `language`, `verticals`
- Load `templates/rec-{template_key}.md` → this IS the writer prompt

### 2. Research the card
- Fetch `card_official_url` (WebFetch) and extract:
  - Exact card name (verify against `card_name`)
  - Annual fee (numeric or "No annual fee")
  - 3–5 real benefits (never invent)
  - Representative APR if stated
  - 2 short benefit tags for LazyBlock (`tag10`, `tag2` — max ~25 chars each)
  - One short card descriptor sentence for LazyBlock `texto` field (50–100 chars)
- Identify 2 real competitor cards from the same country/segment
  (for the Comparative Table section).

### 3. Card image (single source of truth)

**CARD IMAGE PROCESSING IS BEST-EFFORT IN V1 — manual override expected in
draft review.** The Raquel (editor) will review the draft in WordPress and
swap the card image manually if quality is poor. V2 will add programmatic
background removal (rembg or remove.bg API).

- Run `scripts/search-card-image.sh <card_name> <card_official_url>`
  which prioritizes (in order):
  1. A PNG with transparent background from the official bank page
  2. A PNG from the official bank page (even with background)
  3. A JPG from the official bank page
  4. Only then, a web-search result from an authoritative source
- The script logs which priority tier was used. If tier 3 or 4, the log
  notes it so Raquel knows to expect manual review.
- The image is saved to `/tmp/card-<slug>.<ext>`.
- Upload via `content-publish-wordpress/scripts/upload-image.sh` →
  `{id, source_url}` — this is the **card_media**.

### 4. Featured image (composition)
- Run `scripts/generate-featured-image.sh <slug> <card_image_path>` which
  calls Gemini 2.5 Flash Image with the uploaded card image (as inline
  base64 reference) and a random scene from the environments list
  (modern financial district, upscale café, luxury hotel lounge, premium
  office, elegant home interior, rooftop with skyline, airport lounge,
  contemporary coworking, urban street with cinematic blur, city at sunset,
  nighttime metropolis).
- Output: 16:9 PNG at `/tmp/featured-<slug>.png`.
- Upload via `upload-image.sh` → `{id, source_url}` — this is the
  **featured_media**.
- VALIDATE: the card in the composition must be visually identical to the
  card_media. If not, regenerate (retry up to 2x). If still broken,
  abort with a clear message.

### 5. Write the article
Follow the loaded template strictly. Word count is a HARD LIMIT:
**450–500 words** in the final visible body.

Structure (order is mandatory):
1. TITLE (post title, not H1 in body)
2. FIRST PARAGRAPH — intro, with `card_name` in `<strong>` in first sentence
3. INTRODUCTION — 2–3 more short paragraphs
4. H2 — Key Benefits of the Card
5. H2 — How Does It Work
6. H2 — Comparative Table — **MUST contain a real HTML `<table>`** comparing
   the main card with the 2 competitors (columns: card names; rows: annual
   fee, rewards, lounge access / relevant perks, APR). The table lives inside
   a Gutenberg `<!-- wp:html -->...<!-- /wp:html -->` block so the editor does
   not rewrite it. Positioning paragraphs go AFTER the table.
7. H2 — Who Is This Card Best For

Card LazyBlocks and the CTA LazyBlock are inserted by the skill (see step 7),
not by the writer — do NOT add placeholders in the writer output.

### 6. Validate word count
Run `scripts/validate-article.sh <body_html_file>`. If exit != 0, expand or
trim the article and re-validate. Never publish out-of-range content.

### 7. Assemble raw HTML
Build the final content (raw Gutenberg format) as:

```
<!-- wp:paragraph -->
<p><strong>{card_name}</strong> {first paragraph continues...}</p>
<!-- /wp:paragraph -->

<!-- wp:lazyblock/credit-card {<JSON payload>} /-->

<!-- wp:paragraph --> ... introduction paragraphs ... <!-- /wp:paragraph -->

<!-- wp:heading --><h2 class="wp-block-heading">Key Benefits of the Card</h2><!-- /wp:heading -->
... 3-4 paragraphs ...

<!-- wp:heading --><h2 class="wp-block-heading">How Does It Work</h2><!-- /wp:heading -->
... paragraphs ...

<!-- wp:heading --><h2 class="wp-block-heading">Comparative Table</h2><!-- /wp:heading -->
<!-- wp:html -->
<table> ... real HTML table with 2 competitors ... </table>
<!-- /wp:html -->
... positioning paragraphs ...

<!-- wp:heading --><h2 class="wp-block-heading">Who Is This Card Best For</h2><!-- /wp:heading -->
... paragraphs ...

<!-- wp:lazyblock/botao {<CTA JSON>} /-->
```

#### LazyBlock `credit-card` JSON payload

Minimum v1 shape (if frontend renders broken responsive sizes, v2 will
replicate the full shape by issuing `GET /wp/v2/media/<id>` after upload
and embedding the full media object including `description.rendered` and
`sizes`):

- `imagem` — **URL-encoded JSON string** describing the card media object.
  Minimum shape:
  `{"alt":"","title":"<media title>","caption":"","description":{"raw":"","rendered":""},"id":<media_id>,"link":"<media link>","url":"<source_url>","sizes":""}`.
  Apply `encodeURIComponent` to the JSON string before embedding.
- `categoria` — `"{default_category}"` from sites.json (e.g. "Credit Card")
- `titulo` — exact card_name
- `tag10` — first short benefit tag (≤25 chars)
- `tag2` — second short benefit tag (≤25 chars)
- `texto` — the short descriptor sentence (50–100 chars)
- `botao-texto` — `"How to Apply"`
- `siteXfora` — `"You will remain on this website."`
- `botao-url` — `"https://{domain}/apply-now-{country}-{vertical}-{card-slug}/"`
- `color-botao` — `"#27ae60"`
- `blockId` — random 6-char base62 (see below)
- `blockUniqueClass` — `"lazyblock-credit-card-<blockId>"`

#### LazyBlock `botao` (CTA at end) JSON payload

- `texto-botao` — `" HOW TO APPLY "` (note the leading/trailing spaces)
- `link-botao` — same as `botao-url` above
- `cor-botao` — `"#27ae60"`
- `texto-pequeno` — `"You will remain on this website."`
- `blockId` — random 6-char base62
- `blockUniqueClass` — `"lazyblock-botao-<blockId>"`

#### blockId generation

Use exactly:
```bash
openssl rand -base64 6 | tr -d '/+=' | head -c 6
```
Each LazyBlock in the post gets its own freshly generated `blockId`.

### 8. Build slug and URLs
- `card_slug` — kebab-case of card_name with the common-noun part stripped
  if redundant (e.g. "AIB Visa Gold Card" → `aib-visa-gold`). When in doubt,
  keep the full kebab (`aib-visa-gold-card`). Lowercase, ASCII only.
- `post_slug` — `rec-{country}-{vertical}-{card_slug}`
  (e.g. `rec-gb-cc-aib-visa-gold`)
- `p1_url` (used in both LazyBlocks):
  `https://{domain}/apply-now-{country}-{vertical}-{card_slug}/`

### 9. Yoast SEO fields
- `_yoast_wpseo_title` — `"{Card Name}: {catchy phrase} | {Site Name}"`
  (≤60 chars ideal)
- `_yoast_wpseo_metadesc` — 140–155 chars, must include card name
- `_yoast_wpseo_focuskw` — the card name (e.g. "AIB Visa Gold Card")

### 10. Resolve taxonomy IDs

Mandatory tags (in order), coming from config + card_slug:
1. `"rec"` — the article type
2. `"{vertical}"` — e.g. `"cc"`
3. `"{country}"` — e.g. `"gb"`
4. `"{card_slug}"` — e.g. `"aib-visa-gold"`

Plus **2–4 SEO tags chosen by the writer** based on the card's main benefits
(examples: `"travel credit card"`, `"airport lounge access"`, `"no annual fee"`,
`"cashback rewards"`). Multi-word tags must be resolved as the human-readable
name (WP auto-slugs to kebab-case — e.g. `"travel credit card"` →
slug `travel-credit-card`). If you need the slug explicitly, compute:
lowercase, spaces → `-`, strip non-alphanumeric.

Total: 6–8 tags.

For each tag (and for the category):
- `content-publish-wordpress/scripts/resolve-term.sh <site_key> tags "<name>"`
- `content-publish-wordpress/scripts/resolve-term.sh <site_key> categories "{default_category}"`

### 11. Publish

1. Write post JSON to `/tmp/rec-post-<slug>.json` with all fields.
2. `content-publish-wordpress/scripts/create-post.sh <site_key> /tmp/rec-post-<slug>.json`
   → parse `{id, link}` from the response.
3. Write yoast JSON to `/tmp/rec-yoast-<slug>.json` with keys
   `title`, `content` (same raw HTML as the post content), and `meta`.
4. `content-publish-wordpress/scripts/update-yoast.sh <site_key> <post_id> /tmp/rec-yoast-<slug>.json verify`

Note: `update-yoast.sh` accepts `verify` (or `--verify`) as an optional
**4th positional argument**. When present, the script performs a final GET
on the post to confirm the three Yoast meta fields actually saved, and
exits 3 if any mismatch is found.

### 12. Return

Emit a summary to the user:
- Post ID + URL
- Featured media URL
- Card media URL (and the priority tier from search-card-image.sh)
- Final word count
- Tags applied (names + IDs)

## Scripts

- `scripts/search-card-image.sh <card_name> <card_official_url>`
  → downloads best-candidate card image, prints
  `{path, mime, tier}` where tier is 1–4 (see step 3).
- `scripts/generate-featured-image.sh <slug> <card_image_path>`
  → Gemini composition; saves `/tmp/featured-<slug>.png` and prints
  `{path, scene}`.
- `scripts/validate-article.sh <html_file>` → word-count validator
  (exit 0 if 450–500, exit 1 otherwise; prints count + status).

## Logs

All actions append to `/root/mgs-agent/logs/generate-rec.log`.

## Failure modes

- Template missing → abort
- Card page unfetchable → abort (never invent data)
- Card image not found in any tier → abort with message (ask user for image URL)
- Word count out of 450–500 after 2 retries → abort
- Gemini composition fails after 2 retries → abort
- WP publish failure → log full response, abort
- Yoast verify mismatch → log and surface to user (post still exists, but meta needs manual fix)
