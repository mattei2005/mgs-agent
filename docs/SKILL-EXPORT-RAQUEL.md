# Skills do MGS Agent — Export para Raquel

> **Data do export:** 2026-04-22  
> **Autor:** Atena (via Rodolfo)  
> **Destinatária:** Raquel Oliveira (gestão editorial MGS)  

## O que é esse documento

Esse arquivo consolida o **código-fonte integral** das 2 skills atualmente em produção do sistema de automação de conteúdo da MGS Digital Corp:

1. **`content-generate-rec`** — gera artigos REC (Recommendation) de cartão de crédito do zero: pesquisa o produto no site oficial do banco, gera imagem featured via Gemini, monta o artigo a partir do template da vertical, e publica no WordPress.
2. **`content-publish-wordpress`** — utilitário reusável que cuida da parte WP: autentica via 1Password, sobe mídia, cria/atualiza posts, configura Yoast SEO, resolve IDs de categoria/tag.

A Atena usa essas 2 skills juntas pra fechar o pipeline completo — do briefing do cartão até o rascunho publicado no WP.

## Como esse documento está organizado

Para cada skill, você vê:

- `SKILL.md` — descrição da skill (objetivo, triggers, passos do pipeline, regras editoriais)
- `templates/` — templates de artigo por vertical (formato país-nicho-idioma)
- `scripts/` — utilitários bash que a skill chama durante execução

Conteúdo transcrito **integralmente** dos arquivos reais em `/root/mgs-agent/skills/` no VPS MGS. Não foi resumido nem reinterpretado.

---

# Seção — SKILL `content-generate-rec`

**Path real no VPS:** `/root/mgs-agent/skills/content-generate-rec/`

## Arquivo: `SKILL.md`

**Tamanho:** 496 linhas, 23,522 caracteres

```markdown
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
  `{id, source_url}` — this is the **card_media**.

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
- Output: 16:9 PNG at `/tmp/featured-<slug>.png`.
- Upload via `upload-image.sh` → `{id, source_url}` — this is the
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

### 6. Validate word count
Run `scripts/validate-article.sh <body_html_file>`. If exit != 0, expand or
trim the article and re-validate. Never publish out-of-range content.

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

### 9. Yoast SEO fields
- `_yoast_wpseo_title` — Use a card benefit (NOT the word "Review", NOT the site name).
  Format: `"{Card Name}: {benefit phrase}"` — e.g. `"HSBC Premier: No Fee, Lounge Access"`
  **HARD LIMIT: ≤60 characters including spaces and punctuation. Must contain
  the focus keyphrase (card name). Count the EXACT character length before saving —
  never estimate. NEVER include the site name at the end. NEVER use the word "Review".**
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

### 12. Return

Emit a summary to the user:
- Post ID + WordPress edit link
- **Official source URL** used to research the card (card_official_url)
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
- `../content-publish-wordpress/scripts/resolve-button-color.sh <site_key> [override]`
  → validates and resolves the button color hex for this article. Returns
  `{hex, source, input}` (see Step 1b).

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
```

## Arquivo: `templates/rec-gb-cc-en.md`

**Tamanho:** 204 linhas, 6,576 caracteres

```markdown
FINAL PROMPT — REC (GB / EN)

WORD COUNT (CRITICAL — HARD LIMIT)

The FINAL PUBLISHED ARTICLE BODY must contain between 450 and 500 words.

STRICT HARD LIMITS:
Minimum: 450 words
Maximum: 500 words
Under 450 = FAIL
Over 500 = FAIL

WORD COUNT RULE:
Count ALL visible words including: subtitle (H2s), body paragraphs, and table content.
Do NOT count: LazyBlock card block, CTA buttons, spaces, punctuation, HTML tags,
formatting characters, comments, JSON blocks, or hidden metadata.

CRITICAL:
The validation must be done on the FINAL assembled article body.
Do NOT validate intermediate drafts.
Do NOT publish if final body is outside 450-500 words.

MANDATORY SELF-CHECK: Before publishing:
1. Assemble the full final article body
2. Count the visible words only
3. If under 450, expand the article
4. If over 500, reduce the article
5. Recount
6. Publish ONLY when final body is between 450 and 500 words

CONTEXT:
You are a professional content writer specialized in SEO, recommendation,
and conversion-focused blog content for credit cards in the United Kingdom (GB).
You must generate a REC (Recommendation Post), designed for top-of-funnel
traffic (attraction + click).

OBJECTIVE:
Create content that:
- Clearly presents the credit card
- Generates immediate interest
- Highlights real value without going too deep
- Drives users to the P1 page

INPUT DATA (ALWAYS CONSIDER):
- Card Name (exact name)
- Official URL (only source of truth)
- Domain URL
- Country: GB
- Language: EN
- Competitors: 2 real competitors

CRITICAL RULES:
- Only use information from the official page
- Never invent benefits
- Never assume missing data
- If something is not confirmed, do not include it

WRITING RULES:
- Never use emojis
- Avoid exaggerated promotional language
- Keep the tone clear, natural, and scannable
- Maximum 4 paragraphs per section
- Each paragraph max ~35 words
- Always leave one blank line between paragraphs

LINK LOGIC:
All buttons must point to: https://[domain]/apply-now-gb-cc-[card-name-slug]

TAGS (CRITICAL):
The tags array MUST include the following mandatory tags (always lowercase,
in this exact order first):
1. "rec" — the article type
2. "cc" — the vertical (credit card)
3. "gb" — the country code
4. The card name slug

After the 4 mandatory tags, add 2-4 additional SEO tags relevant to the card's
main benefits or category (e.g. "travel credit card", "airport lounge access",
"no annual fee", "cashback rewards").
Total: 6-8 tags per article.

## Subtitle Generation (MANDATORY)

Before writing the article body, generate a SUBTITLE at the very top.

Subtitle rules:
- MAX 100 characters (spaces and punctuation count)
- MUST contain the exact focus keyphrase: {keyphrase}
- MUST highlight ONE specific feature or benefit of the card
  (e.g., no foreign fees, interest-free period, credit limit,
  travel insurance, cashback rate, annual fee, rewards points)
- Editorial tone (punchy, like a news subhead), NOT descriptive
- Third person, no "you should"
- British spelling for UK cards
- No ellipsis, no trailing "..."
- No <strong> or <em> (plain text)

Examples (for AIB Visa Gold Card):
✓ "AIB Visa Gold Card offers no foreign fees and bundled travel insurance."
✓ "AIB Visa Gold Card: 56 days interest-free credit with £10,000 limit."
✓ "AIB Visa Gold Card rewards premium UK travellers with zero foreign fees."
✗ "AIB Visa Gold Card is a premium credit product aimed at UK customers." (generic, no benefit)
✗ "The AIB Visa Gold Card targets middle-tier consumers." (descriptive, no benefit)

Output format:
<!-- wp:paragraph -->
<p>{subtitle text, no <strong> tags}</p>
<!-- /wp:paragraph -->

This <p> is the FIRST element of the post content (before LazyBlock credit-card).

STRUCTURE (STRICT ORDER):
1. TITLE
2. FIRST PARAGRAPH
3. INTRODUCTION
4. H2 — Key Benefits of the Card
5. H2 — How Does It Work
6. H2 — Comparative Table
7. POSITIONING BLOCK
8. H2 — Who Is This Card Best For

NOTE: Card blocks (LazyBlocks) and CTA buttons are inserted automatically
by the publishing system. Do NOT include any markers or placeholders for them.

IMAGE EXECUTION MODE (CRITICAL)
You must execute tasks in SEQUENCE:
1. Write the full article first
2. Generate/select the card image
3. Generate the featured image using the SAME card
Do NOT mix these steps.

1) CARD IMAGE:
Find a real, accurate image of the credit card.
Rules:
- Must match correct bank and network
- Must be clean, high resolution
- Must show the full card (no hands, no scene)

Processing:
- Remove background completely (transparent PNG)
- Crop EXACTLY to the card edges (no margins)
- Keep horizontal orientation
- Keep the card flat (no distortion)

STRICT:
- Do NOT recreate the card
- Do NOT modify colors, logo, or layout

IMPORTANT: This image is the SINGLE SOURCE OF TRUTH.
It MUST be reused in the featured image.

2) FEATURED IMAGE (CRITICAL):
CRITICAL PIPELINE RULE: You MUST use the EXACT SAME card image from step 1.
You are NOT allowed to generate or recreate a card. This is a COMPOSITION task.

PROCESS:
- Take the existing card image
- Insert it into a realistic scene with ONE person

COMPOSITION:
- Format: horizontal 16:9 (1920x1080)
- ONE realistic person in the foreground (medium shot or bust shot)
- The card must appear LARGE, floating BEHIND the person (never held/touched)
- Card centered or slightly to the right
- Card in the midground, partially occluded by the person for depth
- Premium background with cinematic bokeh

CARD RULES:
- Must be IDENTICAL to the card image from step 1
- Same colors, layout, proportions
- No distortion, no redesign

STYLE:
- Ultra-realistic, professional commercial photography look (full-frame camera)
- Cinematic key light + soft fill light + subtle rim light
- Realistic reflections on the card
- Soft, natural shadows
- Premium campaign color grading

ENVIRONMENTS (vary between generations):
Modern financial district / Upscale café / Luxury hotel lounge / Premium office
/ Elegant home interior / Rooftop with skyline / Airport lounge / Contemporary
coworking / Urban street with cinematic blur / City at sunset / Nighttime metropolis

NEGATIVE (NEVER):
- Multiple people
- Person touching/holding the card
- Altered card design
- Distorted anatomy, extra fingers
- Fake smile, artificial skin
- Cartoon, illustration, CGI, 3D render
- Stock photo look
- Flat lighting

VALIDATION: If the card is not identical → REGENERATE

CARD INTEGRITY RULE:
The card must always be treated as ONE object.
Do NOT: extract logo, isolate elements, recreate from memory.
If broken → regenerate

OUTPUT FORMAT:
HTML ONLY
```

## Arquivo: `scripts/validate-article.sh`

**Tamanho:** 54 linhas, 1,792 caracteres

```bash
#!/bin/bash
set -e

HTML_FILE="${1:?usage: validate-article.sh <html_file>}"
MIN=450
MAX=500

[ -f "$HTML_FILE" ] || { echo "ERROR: file not found: $HTML_FILE" >&2; exit 1; }

# Count visible words in the article body.
# INCLUDES: subtitle (first paragraph), body paragraphs, H2 headings, table content.
# EXCLUDES: LazyBlock card block, LazyBlock CTA button, HTML tags, Gutenberg comments.
#
# Word token definition: any whitespace-separated token containing at least one
# letter or digit (matches human/WP word counter behaviour).
count=$(python3 - "$HTML_FILE" <<'PYEOF'
import sys, re

with open(sys.argv[1]) as f:
    content = f.read()

# Remove LazyBlock lines (single-line self-closing: <!-- wp:lazyblock/... /-->)
content = re.sub(r'<!--\s*wp:lazyblock/.*?/-->', '', content)

# Remove all Gutenberg block comments (<!-- wp:... --> and <!-- /wp:... -->)
content = re.sub(r'<!--.*?-->', ' ', content, flags=re.DOTALL)

# Remove HTML tags
content = re.sub(r'<[^>]+>', ' ', content)

# Decode common HTML entities
content = content.replace('&amp;', '&').replace('&nbsp;', ' ')
content = re.sub(r'&[a-zA-Z0-9#]+;', ' ', content)

# Normalise whitespace
content = re.sub(r'\s+', ' ', content).strip()

# Count tokens with at least one letter or digit — matches WP/human word count
# (includes numbers like 20,000 and £24, excludes pure punctuation like — or +)
tokens = [t for t in content.split() if re.search(r'[a-zA-Z0-9]', t)]
print(len(tokens))
PYEOF
)

if [ "$count" -ge "$MIN" ] && [ "$count" -le "$MAX" ]; then
  jq -n --argjson c "$count" --argjson mn "$MIN" --argjson mx "$MAX" \
    '{count:$c, min:$mn, max:$mx, status:"PASS"}'
  exit 0
else
  jq -n --argjson c "$count" --argjson mn "$MIN" --argjson mx "$MAX" \
    '{count:$c, min:$mn, max:$mx, status:"FAIL"}'
  exit 1
fi
```

## Arquivo: `scripts/search-card-image.sh`

**Tamanho:** 168 linhas, 6,091 caracteres

```bash
#!/bin/bash
set -e

CARD_NAME="${1:?usage: search-card-image.sh <card_name> <card_official_url>}"
OFFICIAL_URL="${2:?missing card_official_url}"
LOG="/root/mgs-agent/logs/generate-rec.log"

slug=$(echo "$CARD_NAME" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9]+/-/g; s/^-+|-+$//g')

# Dimension filter thresholds (env-overridable for calibration)
CARD_MIN_WIDTH="${CARD_MIN_WIDTH:-200}"
CARD_MIN_HEIGHT="${CARD_MIN_HEIGHT:-100}"
CARD_ASPECT_MIN="${CARD_ASPECT_MIN:-1.2}"
CARD_ASPECT_MAX="${CARD_ASPECT_MAX:-2.2}"

# Temp file tracking for unified cleanup
TEMP_FILES=()
cleanup_temps() {
  local f
  for f in "${TEMP_FILES[@]}"; do
    [ -n "$f" ] || continue
    rm -f "$f"
  done
}
trap 'cleanup_temps' EXIT

emit_needs_manual() {
  local reason="$1"
  echo "[$(date -Iseconds)] search-card-image NEEDS-MANUAL card=$CARD_NAME url=$OFFICIAL_URL reason=$reason" >>"$LOG"
  jq -n --arg r "$reason" --arg c "$CARD_NAME" --arg u "$OFFICIAL_URL" \
    '{path:null, mime:null, tier:0, source:null, status:"NEEDS_MANUAL", reason:$r, card_name:$c, url:$u}'
  exit 1
}

# Fetch official page
html=$(curl -sS -L -A "Mozilla/5.0" "$OFFICIAL_URL" 2>/dev/null) || emit_needs_manual "fetch_failed"
[ -z "$html" ] && emit_needs_manual "empty_page"

base_host=$(echo "$OFFICIAL_URL" | sed -E 's#^(https?://[^/]+).*#\1#')
candidates=$(echo "$html" | grep -oE '(src|data-src|data-lazy-src)="[^"]+\.(png|jpe?g|webp)"' \
  | sed -E 's/^[^"]+"([^"]+)".*/\1/' \
  | sort -u)

abs_candidates=$(while IFS= read -r u; do
  [ -z "$u" ] && continue
  case "$u" in
    http*) echo "$u" ;;
    //*)   echo "https:$u" ;;
    /*)    echo "$base_host$u" ;;
    *)     echo "$base_host/$u" ;;
  esac
done <<<"$candidates")

[ -z "$abs_candidates" ] && emit_needs_manual "no_image_tags_on_page"

kw=$(echo "$slug" | tr '-' '|')
scored=$(while IFS= read -r u; do
  [ -z "$u" ] && continue
  score=0
  low=$(echo "$u" | tr '[:upper:]' '[:lower:]')
  echo "$low" | grep -qE "($kw)" && score=$((score+5))
  echo "$low" | grep -qE '(card|visa|mastercard|amex|gold|platinum|classic|credit)' && score=$((score+2))
  [[ "$low" == *.png ]] && score=$((score+3))
  [[ "$low" == *.webp ]] && score=$((score+1))
  echo "$low" | grep -qE '(logo|icon|sprite|favicon|hero|banner)' && score=$((score-4))
  echo "$score $u"
done <<<"$abs_candidates" | sort -rn)

# Iterate scored candidates (score > 0) until one passes dimension + aspect filters
best=""
best_score=""
ext=""
out=""

while IFS= read -r line; do
  [ -z "$line" ] && continue
  cand_score=$(echo "$line" | awk '{print $1}')
  cand_url=$(echo "$line" | awk '{print $2}')
  [ "$cand_score" -le 0 ] && break   # scored list is sorted desc by score

  cand_ext="${cand_url##*.}"; cand_ext="${cand_ext%%\?*}"
  cand_ext=$(echo "$cand_ext" | tr '[:upper:]' '[:lower:]')
  case "$cand_ext" in png|jpg|jpeg|webp) ;; *) cand_ext="png" ;; esac
  cand_tmp="/tmp/card-candidate-$slug-$$-$RANDOM.$cand_ext"
  TEMP_FILES+=("$cand_tmp")

  if ! curl -sS -L -A "Mozilla/5.0" -o "$cand_tmp" "$cand_url" 2>/dev/null; then
    echo "[$(date -Iseconds)] search-card-image REJECT download_failed url=$cand_url" >>"$LOG"
    continue
  fi
  [ -s "$cand_tmp" ] || { echo "[$(date -Iseconds)] search-card-image REJECT download_empty url=$cand_url" >>"$LOG"; continue; }

  if ! command -v identify >/dev/null 2>&1; then
    echo "[$(date -Iseconds)] search-card-image WARN identify_unavailable accepting_without_dim_check url=$cand_url" >>"$LOG"
    best="$cand_url"; best_score="$cand_score"; ext="$cand_ext"; out="$cand_tmp"
    break
  fi

  dims=$(identify -format '%w %h' "$cand_tmp" 2>/dev/null || echo "")
  if [ -z "$dims" ]; then
    echo "[$(date -Iseconds)] search-card-image REJECT identify_failed url=$cand_url" >>"$LOG"
    continue
  fi
  w=$(echo "$dims" | awk '{print $1}')
  h=$(echo "$dims" | awk '{print $2}')

  if [ "$w" -lt "$CARD_MIN_WIDTH" ] || [ "$h" -lt "$CARD_MIN_HEIGHT" ]; then
    echo "[$(date -Iseconds)] search-card-image REJECT too_small w=${w} h=${h} (min ${CARD_MIN_WIDTH}x${CARD_MIN_HEIGHT}) url=$cand_url" >>"$LOG"
    continue
  fi

  aspect=$(awk -v w="$w" -v h="$h" 'BEGIN{ printf "%.3f", w/h }')
  in_range=$(awk -v a="$aspect" -v lo="$CARD_ASPECT_MIN" -v hi="$CARD_ASPECT_MAX" 'BEGIN{ print (a>=lo && a<=hi) ? "1" : "0" }')
  if [ "$in_range" != "1" ]; then
    echo "[$(date -Iseconds)] search-card-image REJECT aspect_out_of_range w=${w} h=${h} aspect=${aspect} (expected ${CARD_ASPECT_MIN}-${CARD_ASPECT_MAX}) url=$cand_url" >>"$LOG"
    continue
  fi

  echo "[$(date -Iseconds)] search-card-image ACCEPT w=${w} h=${h} aspect=${aspect} score=${cand_score} url=$cand_url" >>"$LOG"
  best="$cand_url"; best_score="$cand_score"; ext="$cand_ext"; out="$cand_tmp"
  break
done <<<"$scored"

if [ -z "$best" ]; then
  emit_needs_manual "dimensions_filter_all_rejected"
fi

# Move accepted candidate to canonical output path
final_out="/tmp/card-$slug.$ext"
if [ "$out" != "$final_out" ]; then
  mv "$out" "$final_out"
  out="$final_out"
fi
mime=$(file -b --mime-type "$out" 2>/dev/null || echo "image/$ext")

# Classify tier:
#  1 = official + PNG with alpha
#  2 = official + PNG (no alpha / unknown)
#  3 = official + JPG/webp (has background)
#  4 = non-official source
best_host=$(echo "$best" | sed -E 's#^(https?://[^/]+).*#\1#')
is_official=0
[ "$best_host" = "$base_host" ] && is_official=1

if [ "$is_official" = "1" ]; then
  if [ "$ext" = "png" ]; then
    tier=2
    if command -v identify >/dev/null 2>&1; then
      alpha=$(identify -format '%[channels]' "$out" 2>/dev/null || echo "")
      [[ "$alpha" == *a* ]] && tier=1
    fi
  else
    tier=3
  fi
else
  tier=4
fi

if [ "$tier" -ge 3 ]; then
  echo "[$(date -Iseconds)] search-card-image WARN MANUAL REVIEW RECOMMENDED tier=$tier card=$CARD_NAME path=$out src=$best (image may have background or be off-brand)" >>"$LOG"
else
  echo "[$(date -Iseconds)] search-card-image OK tier=$tier card=$CARD_NAME path=$out src=$best" >>"$LOG"
fi

jq -n --arg p "$out" --arg m "$mime" --argjson t "$tier" --arg s "$best" \
  --arg st "OK" \
  '{path:$p, mime:$m, tier:$t, source:$s, status:$st}'
```

## Arquivo: `scripts/generate-featured-image.sh`

**Tamanho:** 127 linhas, 4,636 caracteres

```bash
#!/bin/bash
set -e

# Load env vars (OP_DEFAULT_VAULT, etc.) — runs under systemd/cron too
[ -f /root/mgs-agent/.env ] && set -a && . /root/mgs-agent/.env && set +a

SLUG="${1:?usage: generate-featured-image.sh <slug> <card_image_path>}"
CARD_IMG="${2:?missing card_image_path}"
LOG="/root/mgs-agent/logs/generate-rec.log"

TEMP_FILES=()
cleanup_temps() {
  local f
  for f in "${TEMP_FILES[@]}"; do
    [ -n "$f" ] || continue
    echo "[$(date -Iseconds)] generate-featured-image CLEANUP tmp=$f slug=$SLUG" >>"$LOG"
    rm -f "$f"
  done
}
trap 'cleanup_temps' EXIT

[ -f "$CARD_IMG" ] || { echo "ERROR: card image not found: $CARD_IMG" >&2; exit 1; }

api_key=$(op item get "Gemini API Key" --vault "${OP_DEFAULT_VAULT:-MGS Conteúdo}" --fields api_key --reveal 2>/dev/null) || {
  echo "ERROR: could not read Gemini API Key from 1Password" >&2
  exit 1
}

scenes=(
  "modern financial district"
  "upscale café"
  "luxury hotel lounge"
  "premium office"
  "elegant home interior"
  "rooftop with skyline"
  "airport lounge"
  "contemporary coworking"
  "urban street with cinematic blur"
  "city at sunset"
  "nighttime metropolis"
)
scene="${scenes[$RANDOM % ${#scenes[@]}]}"

mime=$(file -b --mime-type "$CARD_IMG" 2>/dev/null || echo "image/png")
b64_tmp=$(mktemp /tmp/gemini-b64-XXXXXX)
TEMP_FILES+=("$b64_tmp")
base64 -w0 "$CARD_IMG" | tr -d '\n' > "$b64_tmp"

prompt=$(cat <<PROMPT
You must compose a photo-realistic 16:9 (1920x1080) horizontal image using the
EXACT credit card provided as the reference image. Do NOT redesign, recolor,
or recreate the card — it must appear identical in colors, logo, layout and
proportions.

Scene: $scene.
Composition:
- ONE realistic person in the foreground (medium shot or bust shot).
- The card appears LARGE, floating BEHIND the person (never held or touched).
- Card centered or slightly to the right, in the midground, partially
  occluded by the person for depth.
- Premium background with cinematic bokeh.

Style: ultra-realistic commercial photography (full-frame camera), cinematic
key + soft fill + subtle rim light, realistic card reflections, soft natural
shadows, premium campaign color grading.

Negative: multiple people, person touching/holding the card, altered card
design, distorted anatomy, extra fingers, fake smile, cartoon, illustration,
CGI, 3D render, stock photo look, flat lighting.

Output: one image, 16:9, photo-realistic.
PROMPT
)

req_tmp=$(mktemp /tmp/gemini-req-XXXXXX)
TEMP_FILES+=("$req_tmp")
jq -n \
  --arg text "$prompt" \
  --arg mime "$mime" \
  --rawfile data "$b64_tmp" \
  '{contents:[{parts:[{text:$text},{inline_data:{mime_type:$mime,data:$data}}]}]}' \
  > "$req_tmp"

endpoint="https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-image:generateContent?key=$api_key"
out="/tmp/featured-$SLUG.png"

max_attempts=3
attempt=1
while [ "$attempt" -le "$max_attempts" ]; do
  tmp_body=$(mktemp)
  http_code=$(curl -sS -o "$tmp_body" -w '%{http_code}' \
    -H "Content-Type: application/json" -X POST -d @"$req_tmp" "$endpoint" || echo "000")
  body=$(cat "$tmp_body")
  rm -f "$tmp_body"

  if [ "$http_code" = "429" ] || [ "$http_code" = "503" ]; then
    echo "[$(date -Iseconds)] generate-featured-image RETRY attempt=$attempt http=$http_code slug=$SLUG" >>"$LOG"
    if [ "$attempt" -lt "$max_attempts" ]; then
      sleep 5
      attempt=$((attempt+1))
      continue
    else
      echo "[$(date -Iseconds)] generate-featured-image ABORT slug=$SLUG after $max_attempts attempts (rate-limit)" >>"$LOG"
      echo "ERROR: Gemini rate-limited after $max_attempts attempts. Last HTTP=$http_code body head: $(echo "$body" | head -c 400)" >&2
      exit 1
    fi
  fi

  if [ "$http_code" != "200" ]; then
    echo "[$(date -Iseconds)] generate-featured-image FAIL http=$http_code slug=$SLUG body=$(echo "$body" | head -c 500)" >>"$LOG"
    echo "ERROR: Gemini returned HTTP $http_code. Body head: $(echo "$body" | head -c 500)" >&2
    exit 1
  fi

  img_b64=$(jq -r '.candidates[0].content.parts[]? | (.inlineData // .inline_data) | .data // empty' <<<"$body" | head -n1)
  if [ -z "$img_b64" ] || [ "$img_b64" = "null" ]; then
    echo "[$(date -Iseconds)] generate-featured-image NO-IMAGE slug=$SLUG body=$(echo "$body" | head -c 500)" >>"$LOG"
    echo "ERROR: Gemini returned no image. Response head: $(echo "$body" | head -c 500)" >&2
    exit 1
  fi

  echo "$img_b64" | base64 -d >"$out"
  echo "[$(date -Iseconds)] generate-featured-image OK slug=$SLUG scene=$scene attempt=$attempt path=$out" >>"$LOG"
  jq -n --arg p "$out" --arg s "$scene" --argjson a "$attempt" '{path:$p, scene:$s, attempt:$a}'
  exit 0
done
```

---

# Seção — SKILL `content-publish-wordpress`

**Path real no VPS:** `/root/mgs-agent/skills/content-publish-wordpress/`

## Arquivo: `SKILL.md`

**Tamanho:** 115 linhas, 4,124 caracteres

```markdown
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

All scripts live in `./scripts/` and must be invoked via absolute path:

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
```

## Arquivo: `scripts/resolve-credentials.sh`

**Tamanho:** 33 linhas, 1,024 caracteres

```bash
#!/bin/bash
set -e

# Load env vars (for systemd/cron use)
[ -f /root/mgs-agent/.env ] && set -a && . /root/mgs-agent/.env && set +a

SITE_KEY="${1:?usage: resolve-credentials.sh <site_key>}"
SITES_JSON="/root/mgs-agent/data/sites.json"

site=$(jq -e ".\"$SITE_KEY\"" "$SITES_JSON") || {
  echo "ERROR: site_key '$SITE_KEY' not found in $SITES_JSON" >&2
  exit 1
}

wp_url=$(jq -r '.wp_url' <<<"$site")
username=$(jq -r '.publishing_user.username' <<<"$site")
author_id=$(jq -r '.publishing_user.id' <<<"$site")
vault=$(jq -r '.credentials_ref.vault' <<<"$site")
item=$(jq -r '.credentials_ref.item' <<<"$site")
field=$(jq -r '.credentials_ref.field' <<<"$site")

password=$(op item get "$item" --vault "$vault" --fields "$field" --reveal 2>/dev/null) || {
  echo "ERROR: could not read '$field' from 1Password item '$item' in vault '$vault'" >&2
  exit 1
}

jq -n \
  --arg wp "$wp_url" \
  --arg u "$username" \
  --arg p "$password" \
  --argjson a "$author_id" \
  '{wp_url:$wp, username:$u, password:$p, author_id:$a}'
```

## Arquivo: `scripts/resolve-button-color.sh`

**Tamanho:** 55 linhas, 1,683 caracteres

```bash
#!/bin/bash
set -e

# Load env vars (OP_DEFAULT_VAULT, etc.) — runs under systemd/cron too
[ -f /root/mgs-agent/.env ] && set -a && . /root/mgs-agent/.env && set +a

SITE_KEY="${1:?usage: resolve-button-color.sh <site_key> [override]}"
OVERRIDE="${2:-}"
SITES_JSON="/root/mgs-agent/data/sites.json"
COLORS_JSON="/root/mgs-agent/data/button-colors.json"

[ -f "$SITES_JSON" ] || { echo "ERROR: sites.json not found: $SITES_JSON" >&2; exit 1; }
[ -f "$COLORS_JSON" ] || { echo "ERROR: button-colors.json not found: $COLORS_JSON" >&2; exit 1; }

HEX_RE='^#[0-9A-Fa-f]{6}$'

validate_hex() {
  local v="$1"
  if [[ ! "$v" =~ $HEX_RE ]]; then
    echo "ERROR: Invalid hex color: '$v' (expected #RRGGBB)" >&2
    exit 1
  fi
}

if [ -n "$OVERRIDE" ]; then
  if [[ "$OVERRIDE" == \#* ]]; then
    hex="$OVERRIDE"
    validate_hex "$hex"
  else
    hex=$(jq -r --arg n "$OVERRIDE" '.[$n] // empty' "$COLORS_JSON")
    if [ -z "$hex" ]; then
      valid_names=$(jq -r 'keys | join(", ")' "$COLORS_JSON")
      echo "ERROR: Unknown button color name: '$OVERRIDE'. Valid names: $valid_names" >&2
      exit 1
    fi
    validate_hex "$hex"
  fi
  source="request_override"
else
  site=$(jq -e --arg k "$SITE_KEY" '.[$k]' "$SITES_JSON") || {
    echo "ERROR: site_key '$SITE_KEY' not found in $SITES_JSON" >&2
    exit 1
  }
  hex=$(jq -r '.default_button_color // empty' <<<"$site")
  if [ -z "$hex" ]; then
    echo "ERROR: site '$SITE_KEY' has no default_button_color and no override provided" >&2
    exit 1
  fi
  validate_hex "$hex"
  source="site_default"
fi

jq -n --arg h "$hex" --arg s "$source" --arg i "$OVERRIDE" \
  '{hex:$h, source:$s, input:(if $i == "" then null else $i end)}'
```

## Arquivo: `scripts/resolve-term.sh`

**Tamanho:** 69 linhas, 2,960 caracteres

```bash
#!/bin/bash
set -e

SITE_KEY="${1:?usage: resolve-term.sh <site_key> <taxonomy> <name> [strict]}"
TAX="${2:?missing taxonomy (categories|tags)}"
NAME="${3:?missing name}"
MODE="${4:-create}"   # "strict" = fail with exit 2 if term doesn't exist (no creation)
LOG="/root/mgs-agent/logs/publish-wordpress.log"
DIR="$(cd "$(dirname "$0")" && pwd)"

case "$TAX" in categories|tags) ;; *) echo "ERROR: taxonomy must be categories or tags" >&2; exit 1 ;; esac
case "$MODE" in strict|--strict) MODE="strict" ;; create|"") MODE="create" ;; *) echo "ERROR: 4th arg must be 'strict' or omitted" >&2; exit 1 ;; esac

creds=$("$DIR/resolve-credentials.sh" "$SITE_KEY")
wp=$(jq -r '.wp_url' <<<"$creds")
user=$(jq -r '.username' <<<"$creds")
pass=$(jq -r '.password' <<<"$creds")

search=$(jq -rn --arg n "$NAME" '$n|@uri')
tmp_list=$(mktemp)
h_list=$(curl -sS -o "$tmp_list" -w '%{http_code}' -u "$user:$pass" "$wp/wp-json/wp/v2/$TAX?search=$search&per_page=100" || echo "000")
list=$(cat "$tmp_list")
rm -f "$tmp_list"

if [ "${h_list:0:1}" != "2" ]; then
  echo "[$(date -Iseconds)] resolve-term SEARCH FAIL http=$h_list site=$SITE_KEY tax=$TAX name=$NAME resp=$(echo "$list" | head -c 500)" >>"$LOG"
  echo "ERROR: resolve-term search HTTP $h_list: $(echo "$list" | head -c 500)" >&2
  exit 1
fi

match=$(jq --arg n "$NAME" '[.[] | select(.name==$n)][0] // empty' <<<"$list" 2>/dev/null)

if [ -n "$match" ]; then
  id=$(jq -r '.id' <<<"$match")
  slug=$(jq -r '.slug' <<<"$match")
  echo "[$(date -Iseconds)] resolve-term HIT site=$SITE_KEY tax=$TAX name=$NAME id=$id" >>"$LOG"
  jq -n --argjson id "$id" --arg n "$NAME" --arg s "$slug" '{id:$id, name:$n, slug:$s}'
  exit 0
fi

if [ "$MODE" = "strict" ]; then
  echo "[$(date -Iseconds)] resolve-term MISS-STRICT site=$SITE_KEY tax=$TAX name=$NAME" >>"$LOG"
  echo "ERROR: strict mode — term '$NAME' not found in $TAX on $SITE_KEY" >&2
  exit 2
fi

body=$(jq -n --arg n "$NAME" '{name:$n}')
tmp_c=$(mktemp)
h_c=$(curl -sS -o "$tmp_c" -w '%{http_code}' -u "$user:$pass" -H "Content-Type: application/json" \
  -X POST -d "$body" "$wp/wp-json/wp/v2/$TAX" || echo "000")
resp=$(cat "$tmp_c")
rm -f "$tmp_c"

if [ "${h_c:0:1}" != "2" ]; then
  echo "[$(date -Iseconds)] resolve-term CREATE FAIL http=$h_c site=$SITE_KEY tax=$TAX name=$NAME resp=$(echo "$resp" | head -c 500)" >>"$LOG"
  echo "ERROR: resolve-term create HTTP $h_c: $(echo "$resp" | head -c 500)" >&2
  exit 1
fi

id=$(jq -r '.id // empty' <<<"$resp")
if [ -z "$id" ]; then
  echo "[$(date -Iseconds)] resolve-term CREATE FAIL http=$h_c no_id site=$SITE_KEY tax=$TAX name=$NAME resp=$(echo "$resp" | head -c 500)" >>"$LOG"
  echo "ERROR: resolve-term create got HTTP $h_c but no id in response: $(echo "$resp" | head -c 500)" >&2
  exit 1
fi
slug=$(jq -r '.slug' <<<"$resp")
echo "[$(date -Iseconds)] resolve-term NEW site=$SITE_KEY tax=$TAX name=$NAME id=$id" >>"$LOG"
jq -n --argjson id "$id" --arg n "$NAME" --arg s "$slug" '{id:$id, name:$n, slug:$s}'
```

## Arquivo: `scripts/upload-image.sh`

**Tamanho:** 49 linhas, 1,680 caracteres

```bash
#!/bin/bash
set -e

SITE_KEY="${1:?usage: upload-image.sh <site_key> <image_path> <filename>}"
IMAGE_PATH="${2:?missing image_path}"
FILENAME="${3:?missing filename}"
LOG="/root/mgs-agent/logs/publish-wordpress.log"
DIR="$(cd "$(dirname "$0")" && pwd)"

[ -f "$IMAGE_PATH" ] || { echo "ERROR: image not found: $IMAGE_PATH" >&2; exit 1; }

creds=$("$DIR/resolve-credentials.sh" "$SITE_KEY")
wp=$(jq -r '.wp_url' <<<"$creds")
user=$(jq -r '.username' <<<"$creds")
pass=$(jq -r '.password' <<<"$creds")

mime="image/png"
case "${FILENAME,,}" in
  *.jpg|*.jpeg) mime="image/jpeg" ;;
  *.webp) mime="image/webp" ;;
esac

tmp=$(mktemp)
http=$(curl -sS -o "$tmp" -w '%{http_code}' -u "$user:$pass" \
  -H "Content-Disposition: attachment; filename=\"$FILENAME\"" \
  -H "Content-Type: $mime" \
  --data-binary "@$IMAGE_PATH" \
  "$wp/wp-json/wp/v2/media" || echo "000")
resp=$(cat "$tmp")
rm -f "$tmp"

if [ "${http:0:1}" != "2" ]; then
  echo "[$(date -Iseconds)] upload-image FAIL http=$http site=$SITE_KEY file=$FILENAME resp=$(echo "$resp" | head -c 500)" >>"$LOG"
  echo "ERROR: upload-image HTTP $http: $(echo "$resp" | head -c 500)" >&2
  exit 1
fi

id=$(jq -r '.id // empty' <<<"$resp")
url=$(jq -r '.source_url // empty' <<<"$resp")

if [ -z "$id" ]; then
  echo "[$(date -Iseconds)] upload-image FAIL http=$http no_id site=$SITE_KEY file=$FILENAME resp=$(echo "$resp" | head -c 500)" >>"$LOG"
  echo "ERROR: upload-image got HTTP $http but no id in response: $(echo "$resp" | head -c 500)" >&2
  exit 1
fi

echo "[$(date -Iseconds)] upload-image OK http=$http site=$SITE_KEY file=$FILENAME id=$id" >>"$LOG"
jq -n --argjson id "$id" --arg url "$url" '{id:$id, source_url:$url}'
```

## Arquivo: `scripts/check-slug-conflict.sh`

**Tamanho:** 71 linhas, 2,727 caracteres

```bash
#!/bin/bash
set -e

# Load env vars (OP_DEFAULT_VAULT, etc.) — runs under systemd/cron too
[ -f /root/mgs-agent/.env ] && set -a && . /root/mgs-agent/.env && set +a

SITE_KEY="${1:?usage: check-slug-conflict.sh <site_key> <slug> [post_types_csv]}"
SLUG="${2:?missing slug}"
POST_TYPES="${3:-posts,media}"
DIR="$(cd "$(dirname "$0")" && pwd)"
LOG="/root/mgs-agent/logs/publish-wordpress.log"

creds=$("$DIR/resolve-credentials.sh" "$SITE_KEY")
wp=$(jq -r '.wp_url' <<<"$creds")
user=$(jq -r '.username' <<<"$creds")
pass=$(jq -r '.password' <<<"$creds")

slug_enc=$(jq -nr --arg s "$SLUG" '$s | @uri')

conflicting="[]"
IFS=',' read -ra TYPES <<<"$POST_TYPES"
for pt in "${TYPES[@]}"; do
  # Attempt 1: with status=any,trash,auto-draft
  tmp=$(mktemp)
  http=$(curl -sS -o "$tmp" -w '%{http_code}' \
    -u "$user:$pass" \
    "$wp/wp-json/wp/v2/$pt?slug=$slug_enc&status=any,trash,auto-draft&per_page=20" 2>/dev/null || echo "000")
  body=$(cat "$tmp")
  rm -f "$tmp"

  # Retry without status filter if the first call rejected it (e.g. media doesn't accept auto-draft)
  if [ "${http:0:1}" != "2" ]; then
    tmp=$(mktemp)
    http=$(curl -sS -o "$tmp" -w '%{http_code}' \
      -u "$user:$pass" \
      "$wp/wp-json/wp/v2/$pt?slug=$slug_enc&per_page=20" 2>/dev/null || echo "000")
    body=$(cat "$tmp")
    rm -f "$tmp"
  fi

  # Fail-closed: any remaining non-2xx is a hard error
  if [ "${http:0:1}" != "2" ]; then
    echo "ERROR: check-slug-conflict '$pt' endpoint returned HTTP $http on $wp/wp-json/wp/v2/$pt?slug=$slug_enc" >&2
    echo "Response head: $(echo "$body" | head -c 400)" >&2
    exit 1
  fi

  # Response shape must be an array
  if [ "$(jq -r 'type' <<<"$body" 2>/dev/null)" != "array" ]; then
    echo "ERROR: check-slug-conflict '$pt' response is not an array — malformed API response" >&2
    echo "Response head: $(echo "$body" | head -c 400)" >&2
    exit 1
  fi

  hits=$(jq --arg pt "$pt" '[.[] | {id, post_type:$pt, status, slug}]' <<<"$body")
  conflicting=$(jq -s '.[0] + .[1]' <(echo "$conflicting") <(echo "$hits"))
  if [ "$pt" = "posts" ]; then
    posts_hits=$(jq 'length' <<<"$hits")
  fi
done

# WARN if /posts query returned 0 results — possible plugin interference in
# rest_post_query filter. See CLAUDE.md "Known Issue: WP REST /posts?slug=".
if [[ ",$POST_TYPES," == *,posts,* ]] && [ "${posts_hits:-0}" -eq 0 ]; then
  echo "[$(date -Iseconds)] check-slug-conflict WARN posts_query_zero_results slug=$SLUG site=$SITE_KEY (possible plugin interference in rest_post_query — see CLAUDE.md known issue)" >>"$LOG"
fi

available=$(jq 'length == 0' <<<"$conflicting")
jq -n --argjson a "$available" --argjson c "$conflicting" --arg s "$SLUG" \
  '{slug:$s, available:$a, conflicting:$c}'
```

## Arquivo: `scripts/create-post.sh`

**Tamanho:** 64 linhas, 2,598 caracteres

```bash
#!/bin/bash
set -e

SITE_KEY="${1:?usage: create-post.sh <site_key> <post_json_path>}"
POST_JSON="${2:?missing post_json_path}"
LOG="/root/mgs-agent/logs/publish-wordpress.log"
DIR="$(cd "$(dirname "$0")" && pwd)"

[ -f "$POST_JSON" ] || { echo "ERROR: post JSON not found: $POST_JSON" >&2; exit 1; }

creds=$("$DIR/resolve-credentials.sh" "$SITE_KEY")
wp=$(jq -r '.wp_url' <<<"$creds")
user=$(jq -r '.username' <<<"$creds")
pass=$(jq -r '.password' <<<"$creds")

# Slug pre-check (fail-closed): abort if slug is taken or if check itself fails.
# Bypass with ALLOW_DISAMBIGUATION=1 to let WP auto-disambiguate (append -N).
req_slug=$(jq -r '.slug // empty' "$POST_JSON")
if [ -n "$req_slug" ] && [ "${ALLOW_DISAMBIGUATION:-0}" != "1" ]; then
  check_err=$(mktemp)
  set +e
  check_out=$("$DIR/check-slug-conflict.sh" "$SITE_KEY" "$req_slug" 2>"$check_err")
  check_rc=$?
  set -e
  if [ "$check_rc" -ne 0 ]; then
    echo "[$(date -Iseconds)] create-post ABORT slug_check_failed slug=$req_slug rc=$check_rc" >>"$LOG"
    echo "ERROR: slug pre-check failed for '$req_slug' (exit $check_rc):" >&2
    cat "$check_err" >&2
    rm -f "$check_err"
    echo "To bypass the pre-check and let WP auto-disambiguate, re-run with ALLOW_DISAMBIGUATION=1" >&2
    exit 2
  fi
  rm -f "$check_err"
  avail=$(jq -r '.available' <<<"$check_out")
  if [ "$avail" != "true" ]; then
    echo "[$(date -Iseconds)] create-post ABORT slug_conflict slug=$req_slug conflicts=$(jq -c '.conflicting' <<<"$check_out")" >>"$LOG"
    echo "ERROR: slug '$req_slug' is not available. Conflicting entries:" >&2
    jq '.conflicting' <<<"$check_out" >&2
    echo "To override and let WP auto-disambiguate (-N suffix), re-run with ALLOW_DISAMBIGUATION=1" >&2
    exit 2
  fi
fi

tmp=$(mktemp)
http=$(curl -sS -o "$tmp" -w '%{http_code}' -u "$user:$pass" -H "Content-Type: application/json" \
  -X POST --data-binary "@$POST_JSON" "$wp/wp-json/wp/v2/posts" || echo "000")
resp=$(cat "$tmp")
rm -f "$tmp"

if [ "${http:0:1}" != "2" ]; then
  echo "[$(date -Iseconds)] create-post FAIL http=$http site=$SITE_KEY resp=$(echo "$resp" | head -c 500)" >>"$LOG"
  echo "ERROR: create-post HTTP $http: $(echo "$resp" | head -c 500)" >&2
  exit 1
fi

id=$(jq -r '.id // empty' <<<"$resp")
if [ -z "$id" ]; then
  echo "[$(date -Iseconds)] create-post FAIL http=$http no_id site=$SITE_KEY resp=$(echo "$resp" | head -c 500)" >>"$LOG"
  echo "ERROR: create-post got HTTP $http but no id in response: $(echo "$resp" | head -c 500)" >&2
  exit 1
fi
echo "[$(date -Iseconds)] create-post OK http=$http site=$SITE_KEY id=$id" >>"$LOG"
echo "$resp"
```

## Arquivo: `scripts/update-yoast.sh`

**Tamanho:** 92 linhas, 4,072 caracteres

```bash
#!/bin/bash
set -e

SITE_KEY="${1:?usage: update-yoast.sh <site_key> <post_id> <yoast_json_path> [verify]}"
POST_ID="${2:?missing post_id}"
YOAST_JSON="${3:?missing yoast_json_path}"
VERIFY="${4:-}"   # "verify" or "--verify" = GET after PUTs to confirm Yoast fields were saved
LOG="/root/mgs-agent/logs/publish-wordpress.log"
DIR="$(cd "$(dirname "$0")" && pwd)"

[ -f "$YOAST_JSON" ] || { echo "ERROR: yoast JSON not found: $YOAST_JSON" >&2; exit 1; }
case "$VERIFY" in verify|--verify) VERIFY="1" ;; "") VERIFY="" ;; *) echo "ERROR: 4th arg must be 'verify' or omitted" >&2; exit 1 ;; esac

creds=$("$DIR/resolve-credentials.sh" "$SITE_KEY")
wp=$(jq -r '.wp_url' <<<"$creds")
user=$(jq -r '.username' <<<"$creds")
pass=$(jq -r '.password' <<<"$creds")

# PUT 1: only meta
meta_only=$(jq '{meta: .meta}' "$YOAST_JSON")
tmp1=$(mktemp)
h1=$(curl -sS -o "$tmp1" -w '%{http_code}' -u "$user:$pass" -H "Content-Type: application/json" \
  -X PUT -d "$meta_only" "$wp/wp-json/wp/v2/posts/$POST_ID" || echo "000")
r1=$(cat "$tmp1")
rm -f "$tmp1"

if [ "${h1:0:1}" != "2" ]; then
  echo "[$(date -Iseconds)] update-yoast PUT1 FAIL http=$h1 id=$POST_ID resp=$(echo "$r1" | head -c 500)" >>"$LOG"
  echo "ERROR: update-yoast PUT1 HTTP $h1: $(echo "$r1" | head -c 500)" >&2
  exit 1
fi
if ! jq -e '.id' <<<"$r1" >/dev/null 2>&1; then
  echo "[$(date -Iseconds)] update-yoast PUT1 FAIL http=$h1 no_id id=$POST_ID resp=$(echo "$r1" | head -c 500)" >>"$LOG"
  echo "ERROR: update-yoast PUT1 got HTTP $h1 but no id in response: $(echo "$r1" | head -c 500)" >&2
  exit 1
fi

sleep 2

# PUT 2: title + content + meta to trigger save_post
full=$(jq '{title: .title, content: .content, meta: .meta}' "$YOAST_JSON")
tmp2=$(mktemp)
h2=$(curl -sS -o "$tmp2" -w '%{http_code}' -u "$user:$pass" -H "Content-Type: application/json" \
  -X PUT -d "$full" "$wp/wp-json/wp/v2/posts/$POST_ID" || echo "000")
r2=$(cat "$tmp2")
rm -f "$tmp2"

if [ "${h2:0:1}" != "2" ]; then
  echo "[$(date -Iseconds)] update-yoast PUT2 FAIL http=$h2 id=$POST_ID resp=$(echo "$r2" | head -c 500)" >>"$LOG"
  echo "ERROR: update-yoast PUT2 HTTP $h2: $(echo "$r2" | head -c 500)" >&2
  exit 1
fi
if ! jq -e '.id' <<<"$r2" >/dev/null 2>&1; then
  echo "[$(date -Iseconds)] update-yoast PUT2 FAIL http=$h2 no_id id=$POST_ID resp=$(echo "$r2" | head -c 500)" >>"$LOG"
  echo "ERROR: update-yoast PUT2 got HTTP $h2 but no id in response: $(echo "$r2" | head -c 500)" >&2
  exit 1
fi

if [ -n "$VERIFY" ]; then
  sleep 1
  tmp3=$(mktemp)
  h3=$(curl -sS -o "$tmp3" -w '%{http_code}' -u "$user:$pass" "$wp/wp-json/wp/v2/posts/$POST_ID?context=edit" || echo "000")
  got=$(cat "$tmp3")
  rm -f "$tmp3"

  if [ "${h3:0:1}" != "2" ]; then
    echo "[$(date -Iseconds)] update-yoast VERIFY-GET FAIL http=$h3 id=$POST_ID resp=$(echo "$got" | head -c 500)" >>"$LOG"
    echo "ERROR: update-yoast verify GET HTTP $h3: $(echo "$got" | head -c 500)" >&2
    exit 1
  fi
  want_t=$(jq -r '.meta._yoast_wpseo_title // ""' "$YOAST_JSON")
  want_d=$(jq -r '.meta._yoast_wpseo_metadesc // ""' "$YOAST_JSON")
  want_f=$(jq -r '.meta._yoast_wpseo_focuskw // ""' "$YOAST_JSON")
  got_t=$(jq -r '.meta._yoast_wpseo_title // ""' <<<"$got")
  got_d=$(jq -r '.meta._yoast_wpseo_metadesc // ""' <<<"$got")
  got_f=$(jq -r '.meta._yoast_wpseo_focuskw // ""' <<<"$got")
  miss=()
  [ "$got_t" = "$want_t" ] || miss+=("_yoast_wpseo_title (got='$got_t' want='$want_t')")
  [ "$got_d" = "$want_d" ] || miss+=("_yoast_wpseo_metadesc (got='$got_d' want='$want_d')")
  [ "$got_f" = "$want_f" ] || miss+=("_yoast_wpseo_focuskw (got='$got_f' want='$want_f')")
  if [ ${#miss[@]} -gt 0 ]; then
    echo "[$(date -Iseconds)] update-yoast VERIFY FAIL id=$POST_ID missing=${miss[*]}" >>"$LOG"
    echo "ERROR: Yoast verify mismatch on post $POST_ID:" >&2
    for m in "${miss[@]}"; do echo "  - $m" >&2; done
    exit 3
  fi
  echo "[$(date -Iseconds)] update-yoast VERIFY OK id=$POST_ID" >>"$LOG"
fi

echo "[$(date -Iseconds)] update-yoast OK id=$POST_ID" >>"$LOG"
jq -n --argjson id "$POST_ID" --arg v "$VERIFY" '{ok:true, post_id:$id, verified: ($v != "")}'
```

---

# Notas pra adaptar a outras verticais/skills

## Criando template para nova vertical

Hoje só existe **1 template**: `rec-gb-cc-en.md` (UK / cartões de crédito / inglês).

Pra criar uma nova vertical (ex: `rec-mx-cc-es` = México / cartões de crédito / espanhol):

1. Copiar `rec-gb-cc-en.md` pra `rec-mx-cc-es.md` na pasta `templates/`
2. Traduzir os textos pro espanhol mexicano (usa variante LATAM, não Espanha)
3. Ajustar:
   - Moedas (GBP → MXN)
   - Disclosures legais do país (FCA UK → CNBV MX)
   - Tom cultural (menos formal que UK)
   - Palavras-chave de busca ("tarjeta de crédito" em vez de "credit card")
4. Atualizar `/root/mgs-agent/data/sites.json` com o `template_key: rec-mx-cc-es` pros sites que rodam MX-CC-ES

## Criando nova skill (ex: content-generate-p1)

Segue o padrão de `content-generate-rec`:

```
/root/mgs-agent/skills/content-generate-p1/
├── SKILL.md                    # descrição + pipeline
├── templates/
│   ├── p1-gb-cc-en.md
│   └── ... (outras verticais)
└── scripts/
    ├── helper-1.sh
    └── ... (utilitários específicos)
```

SKILL.md **precisa** ter frontmatter YAML no topo indicando `name:`, `description:`, `platforms:` pra Hermes reconhecer.

## Credenciais (sem duplicar)

Toda skill MGS que fala com API deve usar o pattern de `resolve-credentials.sh`:

- Lê `/root/mgs-agent/data/sites.json` com o `credentials_ref` do site
- Busca o secret no 1Password via `op item get --vault "MGS Conteúdo"`
- Retorna JSON com campos `{wp_url, username, password, author_id}`

**Nunca** hardcodar credenciais em scripts ou commits.

## Dúvidas técnicas

Pedir pro Rodolfo. Dúvidas editoriais (subtitle, tom, regras canônicas de conteúdo): editar o próprio `SKILL.md` — as regras são lidas pela Atena em cada execução.
