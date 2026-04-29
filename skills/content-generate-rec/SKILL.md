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
- `status` — `draft` (default) or `publish`. **Always ask the user explicitly
  before starting** — do not assume draft. Include this as one of the 4 intake
  questions: "Should I publish it directly or save as a draft?"
- `overrides.button_color` — override for this article's button color. Accepts:
  - hex direct in `#RRGGBB` format (e.g. `#c9a227`)
  - friendly name in Portuguese (e.g. `dourado`) — resolved via `/root/mgs-agent/data/button-colors.json`

  Friendly color names are kept in Portuguese because they are user-facing —
  Raquel and the editorial team use them directly. The hex is internal.

  If omitted, uses `sites.json[site_key].default_button_color`.

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

### 1b. Resolve button color

> **PITFALL — NUNCA usar a cor da marca do cartão como cor do botão (CRÍTICO):**
> A cor do botão (`color-botao` no LazyBlock `credit-card` e `cor-botao` no `botao`)
> deve sempre vir do `default_button_color` do site em `sites.json` — ou de um
> override explicitamente solicitado pelo usuário. **Nunca inferir a cor da identidade
> visual do cartão** (ex: vermelho da Santander, azul da Barclaycard, verde da HSBC).
> Isso viola a consistência visual do site e requer correção manual posterior.
> Regra: se o usuário não pediu override de cor, use sempre `default_button_color`.


Run:
`../content-publish-wordpress/scripts/resolve-button-color.sh <site_key> [override]`

Returns `{hex, source, input}`:
- `hex` — validated `#RRGGBB` color to use in both LazyBlocks (Step 7)
- `source` — `request_override` or `site_default`
- `input` — the original override argument (or `null` if omitted)

Precedence (first match wins):
1. If `overrides.button_color` provided → hex direct (starts with `#`) or
   friendly name (looked up in `data/button-colors.json`) → validate → `source=request_override`
2. Else → `sites.json[site_key].default_button_color` → validate → `source=site_default`
3. Else (neither present) → abort

Validation: all paths must produce a value matching `^#[0-9A-Fa-f]{6}$`. Otherwise
the script aborts with exit 1 and a clear error on stderr.

Reserved for v2: `type_convention` source — auto-inference from card-name patterns
(e.g. "Gold" cards → `dourado`, "Platinum" → `prata`). Not implemented in v1; a
future run will slot in between (1) and (2) above.

### 2. Research the card
- Fetch `card_official_url` and extract:
  - Exact card name (verify against `card_name`)
  - Annual fee (numeric or "No annual fee")
  - 3–5 real benefits (never invent)
  - Representative APR if stated
  - 2 short benefit tags for LazyBlock (`tag10`, `tag2` — max ~25 chars each)
  - One short card descriptor sentence for LazyBlock `texto` field (50–100 chars)
- Identify 2 real competitor cards from the same country/segment
  (for the Comparative Table section).

> **PITFALL — major bank sites block curl/Python (CRITICAL):** Large UK/US
> banks (HSBC, Barclays, Lloyds, etc.) deploy bot-detection that returns
> empty HTML bodies or 0-byte responses to programmatic requests via curl,
> wget, or Python's urllib — even with realistic headers. The page will
> appear to return HTTP 200 but the body will be empty.
>
> **Always use `browser_navigate` + `browser_snapshot(full=true)`** to fetch
> official bank card pages. This is the only reliable method for these sites.
> Do NOT waste time adjusting headers or trying multiple curl approaches —
> if the first curl attempt returns 0 bytes, switch to the browser immediately.

> **PITFALL — Capital One UK: homepage is the only reliable data source (CRITICAL):**
> Capital One UK (`capitalone.co.uk`) returns "page not available" for almost all
> subpage URLs including `/credit-cards/classic`, `/credit-cards/classic-credit-card`,
> and `/credit-cards/credit-cards-for-bad-credit`. The **homepage** (`https://www.capitalone.co.uk/`)
> is the only page that reliably loads and contains key card data (credit limits,
> APR, benefits) for both the Classic Card and Balance Transfer Card.
>
> Card image: use `https://www.capitalone.co.uk/cloud_assets/webp/contactless-card-image.webp`
> (1154×724px RGBA webp) — clean isolated card shot, no hands. Download with a
> `Referer: https://www.capitalone.co.uk/` header. The image has no white borders
> so the crop step returns identical bounds (still run it for correctness).
>
> RGBA handling: when the downloaded image is RGBA mode (webp with alpha), the
> pixel loop must unpack 4 channels: `r, g, b, a = arr[x, y]`. Also gate on
> `a > 20` to skip fully transparent pixels before checking brightness thresholds.
> Otherwise the crop bounds will be wrong.

> **PITFALL — Barclays vs Barclaycard: two separate domains (CRITICAL):**
> Barclays Bank (`barclays.co.uk`) and Barclaycard (`barclaycard.co.uk`) are
> separate UK entities with separate card pages. Credit cards branded
> "Barclaycard" (Avios Plus, Avios, Rewards, Platinum, etc.) live at
> `https://www.barclaycard.co.uk/personal/credit-cards/<slug>`, NOT at
> `barclays.co.uk/credit-cards/<slug>` — that path 404s for Barclaycard
> products. Always confirm the correct domain before fetching card data.

### 3. Card image (single source of truth)

**CARD IMAGE PROCESSING IS BEST-EFFORT IN V1 — manual override expected in
draft review.** The Raquel (editor) will review the draft in WordPress and
swap the card image manually if quality is poor. V2 will add programmatic
background removal (rembg or remove.bg API).\n\n- Run `scripts/search-card-image.sh <card_name> <card_official_url>`
  which prioritizes (in order):
  1. A PNG with transparent background from the official bank page
  2. A PNG from the official bank page (even with background)
  3. A JPG from the official bank page
  4. Only then, a web-search result from an authoritative source
- The script logs which priority tier was used. If tier 3 or 4, the log
  notes it so Raquel knows to expect manual review.
- The image is saved to `/tmp/card-<slug>.<ext>`.

> **PITFALL — search-card-image.sh returns NEEDS_MANUAL or low-quality image:**
> Some bank pages (e.g. Santander UK) use only lifestyle photos and return no card image.
> The script returns `{"status":"NEEDS_MANUAL","reason":"dimensions_filter_all_rejected"}`.
> Also: the script may return a valid image that is too small to use (e.g. 130×80px) —
> always check the downloaded image dimensions and run `vision_analyze` to confirm quality.
> When either situation occurs:
> 1. Check `browser_get_images` on the official page — if no card image there, move on
> 2. Use a `delegate_task` subagent with browser + web toolsets to search for a direct
>    image URL from financial comparison sites (finder.com/uk, moneysupermarket.com,
>    money.co.uk) — ask for the highest-resolution card image URL available. This is
>    the preferred method because it can find CDN images from the bank itself.
> 3. Download the found image with curl using a Referer header to bypass 403:
>    ```bash
>    curl -L -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36" \
>      -H "Referer: https://www.finder.com/" "<image_url>" -o /tmp/card-<slug>.png
>    ```
> 4. Verify with `vision_analyze` before proceeding
> 5. Apply rotation + crop as normal (see other PITFALL notes below)
>
> **PITFALL — search-card-image.sh may select wrong card on multi-card pages (CRITICAL):**
> Some bank pages (especially Barclaycard) display multiple card images —
> e.g. a generic "Rewards" card thumbnail alongside the specific Avios Plus
> card. The scoring algorithm picks the highest-scoring PNG by keyword match,
> which may not be the correct card if a generic card image scores higher or
> equally due to naming conventions (e.g. `rewards-vertical-tombstone.png`
> outscoring `AviosPlus-front.png` due to keyword overlap).
>
> **Always verify the downloaded card image with `mcp_vision_analyze` before
> proceeding**, asking: "Is this the [exact card name] card?" If the script
> picked the wrong card, identify the correct image URL from
> `browser_get_images` output and download it manually with curl.
>
> Example for Barclaycard Avios Plus: the script may grab the generic
> Barclaycard Rewards PNG; the correct image is the one explicitly named
> `AviosPlus-front` in the page's image list.

> **PITFALL — card image must be HORIZONTAL (landscape) orientation (CRITICAL):**
> After downloading the candidate image, verify it is in landscape orientation
> (width > height) before uploading. Modern bank cards (HSBC, Barclays, etc.)
> increasingly use a vertical/portrait format on their websites, but the
> LazyBlock card component expects a horizontal card for correct layout.
>
> How to check: use `mcp_vision_analyze` on the downloaded image and ask
> "Is this card horizontal (landscape) or vertical (portrait)?"
>
> If the image is vertical → rotate it 90 degrees using Python/PIL:
> ```python
> from PIL import Image
> img = Image.open('/tmp/card-<slug>.<ext>')
> img_rotated = img.rotate(-90, expand=True)  # -90 = clockwise
> img_rotated.save('/tmp/card-<slug>.<ext>')
> ```
> **Do NOT search for alternative versions. Do NOT use images from other sources
> (e.g. business cards, old versions). Always rotate the official image.**
> **Do NOT upload a vertical card image.** It will render incorrectly in the
> LazyBlock and require a manual fix pass.
>
> **PITFALL — card image must be cropped to card edges (CRITICAL):**
> After downloading and rotating (if needed), always crop the image to remove
> any white borders or padding around the card. Use pixel-level detection:
> ```python
> from PIL import Image
> img = Image.open('/tmp/card-<slug>.<ext>')
> arr = img.load()
> w, h = img.size
> left, right, top, bottom = w, 0, h, 0
> for y in range(h):
>     for x in range(w):
>         r, g, b = arr[x, y]
>         if r < 235 or g < 235 or b < 235:
>             if x < left: left = x
>             if x > right: right = x
>             if y < top: top = y
>             if y > bottom: bottom = y
> pad = 3
> cropped = img.crop((max(0,left-pad), max(0,top-pad), min(w,right+pad), min(h,bottom+pad)))
> cropped.save('/tmp/card-<slug>.<ext>', quality=95)
> ```
> Verify the result with vision_analyze: "Does the card have white borders?" If yes, crop again.
> **Always crop before upload** — white borders render poorly in the LazyBlock card component.

- Upload via `content-publish-wordpress/scripts/upload-image.sh` →
  `{id, source_url, mime_type}` — this is the **card_media**.

> **PITFALL — WordPress auto-renames duplicate filenames (CRITICAL):**
> When you upload a file with a name that already exists in the media library,
> WordPress automatically appends a numeric suffix (e.g. `hsbc-premier-credit-card.jpg`
> becomes `hsbc-premier-credit-card-1.jpg`). The `source_url` returned by the
> upload response will contain the **renamed URL** (with the suffix), not the
> original filename you passed.
>
> **Always use the `source_url` AND `id` from the upload response** when building
> the LazyBlock `imagem` JSON — never hardcode or reconstruct the URL from the
> filename argument. The upload response is the single source of truth.
>
> Example:
> ```bash
> result=$(upload-image.sh eggbev /tmp/card.jpg "hsbc-premier-credit-card.jpg")
> card_id=$(echo $result | jq -r '.id')          # e.g. 61970
> card_url=$(echo $result | jq -r '.source_url') # e.g. .../hsbc-premier-credit-card-1.jpg
> ```
> Use `card_id` and `card_url` from this result — NEVER derive the URL from the
> filename string you passed.

> **PITFALL — upload-image filename argument (CRITICAL):** `upload-image.sh`
> determines the MIME type from the **third argument** (filename string), NOT
> from the file path. Always pass a filename **with the correct extension** as
> the third arg:
> ```
> upload-image.sh eggbev /tmp/card-foo.jpeg "hsbc-premier-credit-card.jpeg"
> ```
> Passing a bare title with no extension causes HTTP 500
> (`rest_upload_sideload_error`). The extension in the third arg must match
> one of: `.jpg`, `.jpeg`, `.webp`, `.png`.

### 4. Featured image (composition)
- Run `scripts/generate-featured-image.sh <slug> <card_image_path>` which
  calls Gemini 2.5 Flash Image with the uploaded card image (as inline
  base64 reference) and a random scene from the environments list
  (modern financial district, upscale café, luxury hotel lounge, premium
  office, elegant home interior, rooftop with skyline, airport lounge,
  contemporary coworking, urban street with cinematic blur, city at sunset,
  nighttime metropolis).
- Output: 16:9 JPEG at `/tmp/featured-<slug>.jpg` (auto-compressed via `compress-image.sh`: PNG 2 MB → JPEG ~150 KB, quality 88, max 1280px wide).
- Upload via `upload-image.sh` → `{id, source_url, mime_type}` — this is the
  **featured_media**.
- VALIDATE: the card in the composition must be visually identical to the
  card_media. If not, regenerate (retry up to 2x). If still broken,
  abort with a clear message.

### 4b. Theme HTML sanitization on eggbev (jbf-wp-theme-main)

> **PITFALL — theme strips div/style from wp:html blocks (CRITICAL):**
> The `jbf-wp-theme-main` theme used on eggbev applies aggressive `wp_kses`
> filtering at render time. Inside `<!-- wp:html -->` blocks, it strips:
> - `<div style="...">` — inline style removed, div may also be removed
> - `<div class="...">` — the div element itself is removed from output
> - `<style>` tags — removed entirely
>
> The HTML saves correctly to the database but is sanitized on page render.
> This means you CANNOT add responsive wrappers or scoped CSS inside `wp:html`.
>
> **What survives inside wp:html:** native table elements (`<table>`, `<thead>`,
> `<tbody>`, `<tr>`, `<th>`, `<td>`), and their standard attributes.
>
> **Where to put global CSS:** Customizer → Additional CSS (`Aparência →
> Customizar → CSS Adicional`) — this is injected into `<head>` by WordPress
> itself, before the theme's `wp_kses` filter runs, so it is safe. Any CSS
> that needs to affect post content (e.g. responsive table overflow) must go
> there. Example for responsive tables on all posts:
> ```css
> .jd-post-content table {
>   display: block;
>   overflow-x: auto;
>   -webkit-overflow-scrolling: touch;
>   max-width: 100%;
> }
> ```
> This requires manual action in the WP admin panel (cannot be applied via
> REST API on this site — the `/wp/v2/custom_css` and global-styles endpoints
> are not available for this classic theme).

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
   fee, rewards, lounge access / relevant perks, APR). The table MUST use
   the native Gutenberg `<!-- wp:table -->` block wrapped in
   `<figure class="wp-block-table">`. This is the ONLY format that
   receives the theme's `overflow-x: auto` on mobile — do NOT use
   `<!-- wp:html -->`, which the theme sanitizes and strips the wrapper.
   HTML must be compact (no indentation, no line breaks between tags).
   Positioning paragraphs go AFTER the table.

   **Table formatting rules (mobile readability):**
   - Always add `style="font-size:85%"` to the `<table>` element
   - Keep cell text short and concise — avoid wrapping. Conventions:
     - Rewards: `1.5pts/£1; 2pts/£1 abroad` (not `1.5 pts per £1 sterling; 2 pts per £1 on foreign currency`)
     - Lounge access: `Priority Pass £24/visit` (not `Priority Pass (£24/visit)`)
     - Unlimited lounge: `Unlimited PP` (not `Unlimited Priority Pass`)
     - APR: `29.9% var.` (not `29.9% variable`)
     - Approximate APR: `~29.9% var.`
     - Charge card: `N/A charge card`
   - Goal: cells fit in one line on mobile wherever possible
7. H2 — Who Is This Card Best For

Card LazyBlocks and the CTA LazyBlock are inserted by the skill (see step 7),
not by the writer — do NOT add placeholders in the writer output.

### 6. Validate word count and subtitle length
Run `scripts/validate-article.sh <body_html_file>`. If exit != 0, expand or
trim the article and re-validate. Never publish out-of-range content.

**Also validate the subtitle (excerpt) length before publishing:**
The subtitle — the first `<!-- wp:paragraph -->` block, placed before the
LazyBlock credit-card — is what WordPress renders as the post excerpt. It has
a **hard limit of 100 characters** (spaces and punctuation included).

> **PITFALL — subtitle IS the excerpt (CRITICAL):**
> The first paragraph of the post content (before the card LazyBlock) is
> displayed as the excerpt on listing pages, RSS feeds, and social previews.
> Exceeding 100 characters produces a truncated or broken excerpt.
>
> Measure with: `python3 -c "s='<subtitle text>'; print(len(s))"`
>
> If over 100 chars → rewrite to fit. Do NOT publish until ≤100 chars confirmed.

> **PITFALL — validate the EXACT content that will be published (CRITICAL):**
> The validator must be called on the **final assembled body** — the same string
> passed to `create-post.sh` or `update-yoast.sh`. If the article is rewritten
> for any reason after the first validation (image fix, LazyBlock correction,
> retry), the validator MUST be called again before publishing.
> Never assume a previous PASS still applies to modified content.
> Rule: one validate call per publish attempt, always on the final string.

> **PITFALL — word count must include table content (CRITICAL):**
> The validator counts ALL visible text including H2 subtitles, body paragraphs,
> and table cell content. LazyBlock card and CTA blocks are excluded.
> Token = any whitespace-separated string containing at least one letter or digit
> (matches WP's native word counter). This means a table with 3 rows × 5 columns
> easily adds 50–60 words. Always write the article body (with the table already
> included) and validate the complete body file — not a "prose-only" version.
>
> **Practical rule:** When the article includes a Comparative Table, budget for it.
> Target the prose content at ~420–440 words, then the table brings the total to
> the 450–500 range. Validate the whole body file (including `<!-- wp:html -->` table)
> in a single pass — do NOT validate prose and table separately.

### 7. Assemble raw HTML
Build the final content (raw Gutenberg format) as:

> **PITFALL — splitting article body blocks:** When splitting the article HTML
> into Gutenberg blocks with `re.split(r'(?=<!-- wp:)', body)`, the result
> starts with an empty string if the body begins with `<!-- wp:`. Always
> filter empty strings after splitting:
> ```python
> blocks = [b.strip() for b in re.split(r'(?=<!-- wp:)', body.strip()) if b.strip()]
> subtitle_block = blocks[0]   # first <!-- wp:paragraph --> = subtitle
> rest_blocks = '\n\n'.join(blocks[1:])
> ```
> Do NOT rely on index position without filtering; inserting the LazyBlock
> between subtitle and body will silently break if the empty element is
> left in the list.

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
<!-- wp:table -->
<figure class="wp-block-table"><table class="has-fixed-layout" style="font-size:85%"><thead><tr><th>...</th></tr></thead><tbody><tr><td>...</td></tr></tbody></table></figure>
<!-- /wp:table -->
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
- `color-botao` — resolved hex from Step 1b (not hardcoded)
- `blockId` — random 6-char base62 (see below)
- `blockUniqueClass` — `"lazyblock-credit-card-<blockId>"`

#### LazyBlock `botao` (CTA at end) JSON payload

- `texto-botao` — `" HOW TO APPLY "` (note the leading/trailing spaces)
- `link-botao` — same as `botao-url` above
- `cor-botao` — same resolved hex as `color-botao` (from Step 1b)
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

### 9. Title and Yoast SEO fields — GLOBAL RULES (all MGS sites)

Writing rules for these fields are defined in the template (see `templates/rec-{template_key}.md`,
section **SEO FIELDS**). The template is the single source of truth for content
tone and language.

**Technical constraints (pipeline-level — apply to ALL MGS sites, regardless of template/country/language):**

#### `post_title` (post title in WordPress, renders as `<h1>`)
- HARD LIMIT: max 60 chars (incluindo espacos e pontuacao) — count exact length before saving
- MUST contain the focus keyphrase
- NEVER include site name (ex: " | Eggbev"), separators (" - ", " | "), or sufixos
- Each MGS site has its Yoast global template configured to render only the title (no suffixes)
- If card name >60 chars, abbreviate while keeping the focus keyphrase
  - Example BAD: "Capital One Classic Credit Card: No Fee & Credit Limit Up to GBP4,000" (67 chars)
  - Example GOOD: "Capital One Classic: Build Credit, No Annual Fee" (48 chars)

#### `_yoast_wpseo_title` (Yoast SEO Title meta)
- LEAVE EMPTY. Do NOT fill manually.
- Yoast inherits the site global template automatically (configured per-site to show only the post title)
- Filling manually overrides the global template and breaks consistency across the site
- PITFALL real: Atena once filled this with a custom 48-char title while `post_title` had 67 chars (post 62026, eggbev.com, 2026-04-28). Result: two different titles for the same article. NEVER do this.

#### `_yoast_wpseo_metadesc` (Yoast meta description)
- LIMIT: 120-135 chars (min 120, max 135) — count exact length before saving
- Sweet spot: 130 chars
- MUST contain the focus keyphrase within the first 100 chars
- If draft <120 chars: REWRITE to add context, CTA, or specific benefit
- If draft >135 chars: trim to 130 keeping keyphrase intact

#### `_yoast_wpseo_focuskw` (focus keyphrase)
- HARD LIMIT: max 4 words (Yoast scorer requirement)
- MUST appear in `post_title`
- MUST appear in `_yoast_wpseo_metadesc` (first 100 chars)
- MUST appear in the article first paragraph
- If card name has >4 words, abbreviate while keeping the brand identifiable
  - Example: "Capital One Classic Credit Card" (5 words) -> "Capital One Classic" (3 words)
  - Example: "Barclaycard Avios Plus Credit Card" (5 words) -> "Barclaycard Avios Plus" (3 words)
### 10. Resolve taxonomy IDs

Mandatory tags (in order), coming from config + card_slug:
1. `"rec"` — the article type
2. `"{vertical}"` — e.g. `"cc"`
3. `"{country}"` — e.g. `"gb"`
4. `"{card_slug}"` — e.g. `"aib-visa-gold"`
5. `"lang_{language}"` — derived from the last segment of `template_key` (e.g. `gb-cc-en` → `"lang_en"`, `mx-cc-es` → `"lang_es"`, `br-loans-pt` → `"lang_pt"`). **Always include. Applies to all sites and verticals.**

Plus **2–4 SEO tags chosen by the writer** based on the card's main benefits
(examples: `"travel credit card"`, `"airport lounge access"`, `"no annual fee"`,
`"cashback rewards"`). Multi-word tags must be resolved as the human-readable
name (WP auto-slugs to kebab-case — e.g. `"travel credit card"` →
slug `travel-credit-card`). If you need the slug explicitly, compute:
lowercase, spaces → `-`, strip non-alphanumeric.

> **PITFALL — tags CANNOT contain hyphens (CRITICAL):** Tag names must use
> spaces, never hyphens. Example: `"travel credit card"` ✅, `"travel-credit-card"` ❌.
> This applies to ALL tags including the card_slug tag — use the card name words
> with spaces (e.g. `"hsbc premier credit card"`, NOT `"hsbc-premier-credit-card"`).

> **PITFALL — resolve-term.sh returns HTTP 400 when tag already exists:** The script
> errors out with `term_exists` even though it includes the term_id in the error body.
> When this happens, fetch the tag ID directly via the REST API:
> ```bash
> curl -s -u "$WP_USER:$WP_PASS" \
>   "$WP_URL/wp-json/wp/v2/tags?search=travel%20credit%20card&per_page=5" \
>   | python3 -c "import sys,json; t=[x for x in json.load(sys.stdin) if x['name'].lower()=='travel credit card']; print(t[0]['id'])"
> ```
> Do NOT assume the tag is missing just because resolve-term.sh errored — always
> verify via GET before attempting to create.

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

### 12. Score (Yoast background scorer)

After publishing (step 11), trigger the Yoast scorer para computar scores reais
de SEO e legibilidade e gravá-los no banco. Elimina o ponto cinza na lista de posts
(aparece quando os scores não estão no postmeta).

```bash
bash /root/mgs-agent/skills/content-generate-rec/scripts/yoast-score-post.sh \
  <site_key> <post_id>
```

Expected output:
```json
{"status":"ok","post_id":<id>,"seo_score":<0-100>,"readability_score":<0-100>,"indexable_seo":"<val>","indexable_read":"<val>","wpcli_ok":true}
```

- `seo_score` + `readability_score`: calculados pela lib `yoastseo` (mesma do editor)
- `indexable_seo` + `indexable_read`: confirmados escritos em `wp_yoast_indexable` via SSH/DB
- `wpcli_ok`: true = WP-CLI meta update + rebuild do indexable executados com sucesso

Se `wpcli_ok` for false → log a falha. Post continua no ar; scores serão preenchidos
quando Raquel abrir o editor. Incluir o resultado do scorer no summary final.

> **Note — scores não expostos via REST:** `_yoast_wpseo_linkdex` e
> `_yoast_wpseo_content_score` NÃO estão em `register_post_meta` no mu-plugin v4
> (por design). São gravados em postmeta e `wp_yoast_indexable` mas não expostos
> via REST API. Verificação é feita via SSH/DB. Os valores `indexable_seo` /
> `indexable_read` no JSON confirmam o estado no banco.

> **PITFALL — yoastseo v3.6 API quirks (descobertos por trial & error):**
> - `require('yoastseo')` exporta `{ Paper, assessors, ... }` — os assessors ficam
>   dentro do namespace `assessors`: `const { SEOAssessor, ContentAssessor } = assessors`
> - Assessor constructor: `new SEOAssessor(researcher)` — researcher é o **primeiro** argumento (não segundo)
> - `Researcher` do `_default` não tem `getHelper()` e retorna scores errados → usar sempre o específico do idioma:
>   `require('./node_modules/yoastseo/build/languageProcessing/languages/en/Researcher').default`
> - O módulo Researcher exporta `.default` (ES module wrapped em CJS): sempre acessar `.default`
> - O scorer DEVE ser executado com `cd "$SCORER_DIR" && node yoast-scorer.js ...`
>   (não `node "$SCORER_DIR/yoast-scorer.js"`) — o segundo não resolve `node_modules` relativo ao script

> **PITFALL — RunCloud ASCII art interfere com grep em output SQL (CRÍTICO):**
> O banner de boas-vindas do RunCloud contém a string `8888888b...888` (arte ASCII).
> Qualquer grep com padrão `^[0-9]+` ou `^\s*[0-9]+\s+[0-9]+` vai CASAR com essas
> linhas e retornar os dígitos do banner (ex: `888` em vez do valor real `84`).
>
> **Solução**: sempre fazer grep pelo `POST_ID` exato na linha, ou usar Python com
> `PARSE_ID` env var e um arquivo temp (NÃO heredoc dentro de `$(...)` — falha
> silenciosamente). Exemplo correto:
> ```bash
> cat > /tmp/_parse.py << 'PYEOF'
> import sys, re, os
> pid = os.environ.get("PARSE_ID","")
> data = sys.stdin.read()
> for line in data.replace('\r','').split('\n'):
>     m = re.match(r'\|\s*' + re.escape(pid) + r'\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|', line.strip())
>     if m:
>         print(m.group(1), m.group(2)); sys.exit(0)
> print("? ?")
> PYEOF
> _IDX=$(echo "$SSH_OUT" | PARSE_ID="$POST_ID" python3 /tmp/_parse.py)
> rm -f /tmp/_parse.py
> ```

> **PITFALL — `wp yoast index` não aceita `--object-id` (CRÍTICO):**
> O WP-CLI do Yoast v27.x não suporta reindex de post individual via `--object-id`.
> Usar `wp yoast index --reindex` reindexaria o site inteiro (lento, perigoso).
>
> **Solução**: SQL UPDATE direto no `wp_yoast_indexable`:
> ```sql
> UPDATE wp_yoast_indexable
>   SET primary_focus_keyword_score=84, readability_score=90
>   WHERE object_id=62008 AND object_type='post'
> ```
> Seguido de `post meta update` para manter postmeta em sincronia.

> **PITFALL — yoastseo v3.6 API e `node_modules` path:**
> A lib `yoastseo` deve ser `require`d do diretório que contém `node_modules/`.
> Sempre executar o scorer com `cd "$SCORER_DIR" && node yoast-scorer.js ...`
> em vez de `node "$SCORER_DIR/yoast-scorer.js"` (o segundo não resolve `node_modules`
> relativo ao script). API usada: `{ Paper, SeoAssessor, ContentAssessor, Researcher }`.
> `Researcher` recebe `(paper, i18n)` e é passado para os assessors como segundo arg.


> **PITFALL — guardar URLs e scene durante workflow (CRITICAL):**
>
> O Step 13 exige URLs completas das imagens E o nome da scene da featured. Esses dados são produzidos durante Steps 3 e 4 mas frequentemente são esquecidos quando o summary é montado. Resultado: Atena posta IDs das imagens mas SEM URLs, ou inventa URLs (ainda pior).
>
> **Regra:** durante o workflow, capturar e GUARDAR explicitamente:
> - Step 3 (card image upload): `card_id`, `card_url` (do `source_url` retornado pelo upload-image.sh)
> - Step 4 (featured image): `featured_id`, `featured_url`, `featured_scene` (do output de generate-featured-image.sh: `{path, scene}`)
> - Step 6 (validate-article.sh): `subtitle_chars` da contagem da string do primeiro `<!-- wp:paragraph -->`
>
> Use variáveis Python claras tipo `card_url`, `featured_url`, `featured_scene`, `subtitle_chars` e referencie no template do Step 13. Não tente reconstruir URLs a partir de slugs (PITFALL conhecido — WP renomeia duplicates com -1, -2).

### 13. Return (CRITICAL - SINGLE MESSAGE ONLY)

Emit EXACTLY ONE summary message to the user. NEVER send two messages (one announcement + one summary). NEVER duplicate information across messages. UMA mensagem com TUDO consolidado.

> **PITFALL — duplicate messages waste tokens (CRITICAL):**
> Atena historically sent 2 messages: one announcing the publish + another summarizing details. This wastes ~500 output tokens per REC and degrades UX (user has to scroll twice through nearly identical content).
>
> **The rule is strict:** ONE message after publish. Combine announcement, details, and Raquel mention in a single block.

Required fields in the single message:
- Confirmação de publicação (uma linha)
- Post ID + WordPress edit link + public URL
- Yoast scores (SEO + Readability) com emoji 🟢/🟡/🔴 conforme score
- Word count + title char count + SUB-TITLE char count + meta desc char count
- Focus keyword
- Tags applied (confirm lang_{language} tag presente, lista CSV)
- Imagens com IDs E URLs completas (card + featured + scene da featured)
- Cost reporting (Step 14 — duração, API calls, custo USD)
- @Raquel mention (<@1496254952501280974>) for review notification

Format example (1 single Discord message):

@Rodolfo ✅ {Card Name} publicado no {site}!

📄 Post ID: {id}
🔗 {public_url}
✏️ Edit: {edit_url}

📊 Yoast: SEO {seo}🟢 | Readability {read}🟢
📝 {words} palavras | Title {title_chars}c | Sub-Title {subtitle_chars}c | Meta {meta_chars}c
🔍 Focus: "{focus_kw}"
🏷️ Tags: {tags_csv}

🖼️ Imagens:
• Card image ID: {card_id} — {card_url}
• Featured image ID: {featured_id} — {featured_url} (cena: {featured_scene})

💰 Custo: ${cost} USD ({duration}, {api_calls} API calls)

@Raquel artigo pronto para revisão! 👀

**NUNCA** envie uma segunda mensagem com versão "resumida" do mesmo conteúdo. UMA MENSAGEM SÓ.

## Scripts

- `scripts/search-card-image.sh <card_name> <card_official_url>`
  → downloads best-candidate card image, prints
  `{path, mime, tier}` where tier is 1–4 (see step 3).
- `scripts/generate-featured-image.sh <slug> <card_image_path>`
  → Gemini composition; saves `/tmp/featured-<slug>.jpg` (auto-compressed) and prints
  `{path, scene}`.
- `scripts/validate-article.sh <html_file>` → word-count validator
  (exit 0 if 450–500, exit 1 otherwise; prints count + status).
- `../content-publish-wordpress/scripts/resolve-button-color.sh <site_key> [override]`
  → validates and resolves the button color hex for this article. Returns
  `{hex, source, input}` (see Step 1b).

## Logs

All actions append to `/root/mgs-agent/logs/generate-rec.log`.

## Finding a post ID when REST API returns empty for a slug

When `GET /wp/v2/posts?slug=<slug>` returns `[]` (even with `status=any` or
`context=edit`), the post may still exist. Use the public HTML to get the ID:

```bash
curl -s "https://<domain>/<slug>/" | grep -oE 'post-[0-9]+' | head -1
```

WordPress embeds the post ID in the `<body>` class (e.g. `class="post-62013 ..."`).
Extract the number: `post-62013` → ID is `62013`.

Then fetch via `GET /wp/v2/posts/62013?context=edit` to get the full raw content.

---

## Post deletion (re-publish flow)

Whenever a post is deleted — **for any reason** (re-publish, slug conflict, test cleanup,
or explicit user request) — **always delete the media attachments together with the post** — before or at the
same time. If the media files are left orphaned in the library, WordPress
auto-renames the re-uploaded versions with numeric suffixes (`-1`, `-2`, `-3`...),
which breaks the canonical URLs and pollutes the media library.

**Delete order:**
1. Fetch the post to get `featured_media` ID + parse card media ID from content
2. DELETE `/wp/v2/posts/<id>?force=true`
3. DELETE `/wp/v2/media/<featured_id>?force=true`
4. DELETE `/wp/v2/media/<card_id>?force=true`

```bash
# Example
curl -s -u "$WP_USER:$WP_PASS" -X DELETE "$WP_URL/wp-json/wp/v2/posts/62004?force=true"
curl -s -u "$WP_USER:$WP_PASS" -X DELETE "$WP_URL/wp-json/wp/v2/media/61999?force=true"
curl -s -u "$WP_USER:$WP_PASS" -X DELETE "$WP_URL/wp-json/wp/v2/media/62000?force=true"
```

Confirm each DELETE returns `{"deleted":true}` before re-uploading.

## Failure modes

- Template missing → abort
- Card page unfetchable → abort (never invent data)
- Card image not found in any tier → abort with message (ask user for image URL)
- Word count out of 450–500 after 2 retries → abort
- Gemini composition fails after 2 retries → abort
- WP publish failure → log full response, abort
- Yoast verify mismatch → log and surface to user (post still exists, but meta needs manual fix)

## Step 14 - Cost reporting (mandatory after publish)

Apos completar Step 13 (Return summary), SEMPRE executar estes 2 sub-passos para reportar custo do REC no Discord:

### 14a - Forcar atualizacao do DB de tracking

O cron track-article-cost.sh roda a cada 15min. Apos publicar, forcar update imediato:

    bash /root/mgs-agent/scripts/track-article-cost.sh
    sleep 5

Custo: 0 tokens (script shell puro, sem LLM).

### 14b - Consultar custo e incluir no summary

Apos track-article-cost.sh rodar:

    POST_ID=<id_do_post_publicado>
    sqlite3 /root/mgs-agent/data/article-tracker.db "SELECT post_id, site, duration_sec, api_calls, printf(\"%.4f\", cost_usd_estimated) AS cost FROM article_publications WHERE post_id = $POST_ID;"

Resultado tipico: 62042|eggbev|425|41|2.1234

### Bloco a incluir no summary final ao usuario

No final do summary que ja inclui post_id, link, scores Yoast, etc., adicionar:

    Custo desta publicacao:
      - Duracao: 7m 5s
      - API calls: 41
      - Custo estimado: $2.12 USD

Se o DB ainda nao tiver registro do post, omitir o bloco e adicionar uma linha:

    Custo: ainda calculando (track-article-cost.sh rodara no proximo tick)

### Custo desta secao (overhead)

- bash track-article-cost.sh: 0 tokens (shell)
- sqlite3 query: 0 tokens (shell)
- Bloco no Discord: ~50 tokens output

Total: ~50 tokens output adicionais por REC. Negligenciavel vs custo do REC ($2-3).


## Step 1c - CACHE LOOKUP (CRITICAL - DO BEFORE BROWSER)

ANTES de pesquisar o cartao no site oficial (Step 2), SEMPRE consultar o card cache local. Cache hits economizam ~5min de browser navigation + ~$1 USD por REC.

### Como consultar

1. Calcular card_slug a partir do card_name (kebab-case, sem palavra "card" se redundante):
   - "AIB Visa Gold Card" -> "aib-visa-gold"
   - "HSBC Premier Credit Card" -> "hsbc-premier-credit-card"
   - "Tesco Bank Clubcard" -> "tesco-bank-clubcard"

2. Executar:

    bash /root/mgs-agent/skills/content-generate-rec/scripts/card-cache-lookup.sh "$CARD_SLUG"

Output:
   HIT  -> JSON completo com card_name, annual_fee, apr, benefits, competitors, etc
   MISS -> {"hit": false, "card_slug": "..."}

### Decisao apos lookup

**Se HIT (exit 0):**
   - Usar dados do cache diretamente
   - PULAR Step 2 (research do cartao via browser)
   - PULAR Step 3 se cache tiver card_image_uploaded_url (reutilizar imagem ja no WP)
   - Ir direto pro Step 4 (gerar featured image)
   - Economia tipica: ~5 minutos + ~$1 USD por REC

**Se MISS (exit 1):**
   - Continuar workflow normal (Step 2 - research via browser)
   - APOS Step 3 (download imagem), salvar tudo no cache (ver Step 2.5 abaixo)

### Campos do cache que substituem browser research

   annual_fee   -> usado direto (Step 2)
   apr          -> usado direto (Step 2)
   benefits     -> JSON array com 3-5 benefits ja extraidos
   tag10        -> LazyBlock tag (Step 7)
   tag2         -> LazyBlock tag (Step 7)
   descriptor   -> LazyBlock texto (Step 7)
   competitors  -> array com 2 cartoes pra Comparative Table
   card_image_uploaded_url -> URL no WordPress (se HIT, pular upload)
   card_image_uploaded_id  -> media ID (Step 7 imagem JSON)

### Campos que podem estar null no cache (precisam ser preenchidos)

Cache populado retroativamente pode ter alguns campos vazios. Se tag10/tag2/descriptor estao null:
   - Atena gera baseado nos benefits do cache (rapido, sem browser)
   - Salva no cache de novo no Step 2.5 pra proximas execucoes

## Step 2.5 - CACHE SAVE (CRITICAL - APOS RESEARCH)

Apos completar Step 2 (research) e Step 3 (card image upload), SEMPRE salvar dados no cache pra futuros RECs do mesmo cartao.

### Quando executar

   - Apos Step 3 (card image uploaded, temos uploaded_id e uploaded_url)
   - Antes do Step 4 (featured image generation)

### Como salvar

1. Montar JSON com todos os campos coletados:

    cat > /tmp/cache-save-${CARD_SLUG}.json << JSON
    {
      "card_slug": "tesco-bank-clubcard",
      "card_name": "Tesco Bank Clubcard Credit Card",
      "card_official_url": "https://www.tescobank.com/...",
      "country": "gb",
      "vertical": "cc",
      "language": "en",
      "annual_fee": "No annual fee",
      "apr": "12.9% var.",
      "benefits": ["Benefit 1...", "Benefit 2...", "Benefit 3..."],
      "tag10": "Clubcard rewards",
      "tag2": "No annual fee",
      "descriptor": "Earn Clubcard points on every purchase.",
      "competitors": [{"name": "Sainsburys Nectar"}, {"name": "Asda Money"}],
      "card_image_local_path": "/tmp/card-tesco-bank-clubcard.jpg",
      "card_image_url_orig": "https://www.tescobank.com/.../card.png",
      "card_image_uploaded_id": 62033,
      "card_image_uploaded_url": "https://eggbev.com/wp-content/.../card.jpg",
      "ttl_days": 30,
      "source": "browser"
    }
    JSON

2. Salvar no cache:

    bash /root/mgs-agent/skills/content-generate-rec/scripts/card-cache-save.sh /tmp/cache-save-${CARD_SLUG}.json

### Politica de TTL

   - Default: 30 dias
   - Apos TTL expirar, proximo lookup retorna MISS e Atena re-pesquisa (info de cartao pode ter mudado: APR, benefits)
   - Para cartoes muito estaveis (Visa Gold tradicional), pode passar ttl_days=90 no JSON

### Beneficio

Proximo REC do mesmo cartao em outro site MGS (fincgriffin, futuros sites GB) reutiliza tudo:
   - Pula browser navigation (~5 min)
   - Pula card image download/processing (~2 min)
   - Custo: ~$0.30 (vs $3.16 sem cache)
   - Economia: 90% por REC repetido


## Step 5b - USE MGS REC API (CRITICAL - PREFER OVER MANUAL GENERATION)

A partir de 29/04/2026, a geracao do article HTML deve SEMPRE usar a API local mgs-rec-api ao inves de gerar inline. Isso reduz custo de $3.16/REC para $0.03/REC (99% menos) e tempo de 10min para 20s.

### Quando usar

SEMPRE - substitui completamente o Step 5 (Write the article).

Excecoes (raras):
   - API down (health check falha): cair pro modo legacy (Step 5 manual)
   - Cartao com requisitos especiais nao suportados pelo template

### Como chamar

Apos Step 4 (featured image generation), chamar a API:

    # Validar que API esta up
    curl -s http://127.0.0.1:8001/health || echo "API DOWN - cair pro modo legacy"

    # Montar payload com dados do cartao
    cat > /tmp/api-request-${CARD_SLUG}.json << JSON
    {
      "site": "eggbev",
      "card_slug": "tesco-bank-clubcard",
      "card_name": "Tesco Bank Clubcard Credit Card",
      "card_official_url": "https://www.tescobank.com/...",
      "annual_fee": "No annual fee",
      "apr": "12.9% var.",
      "benefits": ["Benefit 1...", "Benefit 2...", "Benefit 3..."],
      "competitors": [{"name": "Sainsburys Nectar"}, {"name": "Asda Money"}]
    }
    JSON

    # Chamar API (timeout 60s, retry 1x)
    RESPONSE=$(curl -s --max-time 60 -X POST http://127.0.0.1:8001/generate \
         -H "Content-Type: application/json" \
         -d @/tmp/api-request-${CARD_SLUG}.json)

    # Validar resposta
    SUCCESS=$(echo "$RESPONSE" | jq -r .success)
    if [ "$SUCCESS" != "true" ]; then
      echo "API failed: $RESPONSE"
      # CAIR PRO MODO LEGACY (Step 5 original)
    fi

    # Extrair HTML pronto
    ARTICLE_HTML=$(echo "$RESPONSE" | jq -r .article_html)
    COST=$(echo "$RESPONSE" | jq -r .cost_usd)
    DURATION=$(echo "$RESPONSE" | jq -r .duration_sec)

    echo "Article generated via API: cost=\$$COST duration=${DURATION}s"

### O que a API faz por voce

1. Consulta cache (card-cache.db) automaticamente
2. Carrega template correto (rec-{template_key}.md)
3. Carrega config do site (sites.json)
4. Gera article HTML em formato Gutenberg (450-500 palavras)
5. Retorna HTML + custo + tempo + tokens
6. Loga tudo em /root/mgs-agent/api/usage.db

### O que VOCE (Atena) ainda faz APOS receber HTML da API

A API gera APENAS o body HTML. Voce ainda precisa:

1. Inserir LazyBlock credit-card no posicao correta (apos primeiro paragrafo)
   - Substituir comentario placeholder com JSON LazyBlock real
   - Usar dados do cache (tag10, tag2, descriptor) ou gerar baseado em benefits
2. Inserir LazyBlock botao no final
3. Step 6: Validar word count (rodar validate-article.sh)
4. Step 7-8: Build slugs e URLs
5. Step 9: SEO fields (title, metadesc, focuskw)
6. Step 10: Resolver tags + categoria via WP REST
7. Step 11: Publicar via create-post.sh + update-yoast.sh
8. Step 12: Trigger Yoast scorer
9. Step 13: Return summary (incluindo Step 14 cost reporting)

### Tratamento de erros

API pode retornar:
   - HTTP 200 success=true: HTML pronto
   - HTTP 200 success=false: erro logico (ex: cache MISS sem dados)
   - HTTP 500: erro interno (ex: Anthropic API down)
   - HTTP 404: site/template nao encontrado
   - Timeout: API demorou >60s

Em qualquer erro nao recuperavel: cair pro Step 5 original (gerar inline). Reportar erro ao Rodolfo no Discord.

### Logs e debug

   API logs:    /root/mgs-agent/api/logs/api.log
   Systemd log: /root/mgs-agent/api/logs/systemd.log
   Usage DB:    /root/mgs-agent/api/usage.db
   Stats:       curl http://127.0.0.1:8001/stats
   Restart:     systemctl restart mgs-rec-api.service

### Custo desta etapa

   - Geracao via API: $0.03 por REC (vs $3.16 inline)
   - Tempo: 20s por REC (vs 10min inline)
   - Economia: 99% custo + 97% tempo

