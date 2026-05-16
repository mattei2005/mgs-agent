---
name: content-generate-rec
description: Generates a REC (Recommendation) article for a credit card — fetches card data from the official URL, finds/processes the card image, generates a featured composition image via Gemini, assembles the article from the country/language/vertical-specific template, and publishes it to WordPress via content-publish-wordpress. Selects the right template automatically based on the site's template_key.
---

# content-generate-rec

Generates and publishes a REC (Recommendation) article for a credit card to a
WordPress site, using a per-site template selected from `template_key`.

## Fast Runner default (CRITICAL)

For normal REC requests, Atena must use the deterministic runner instead of
executing the full workflow manually through many tool-calling turns.

Default command shape:

```bash
/root/mgs-agent/scripts/mgs-rec-runner.py \
  --site <site_key> \
  --card "<exact card name>" \
  --status <draft|publish> \
  --source-url "<official URL>"
```

Operational rule:
- If the user provides site, REC type, exact card name, status, and official URL,
  call `mgs-rec-runner.py` directly and return the JSON summary.
- Do not manually repeat Steps 1-14 unless the runner fails with a clear error.
- If no official URL is provided and cache MISS is likely, ask for the official
  URL first; this keeps the process fast and avoids browser-search loops.
- Use `--dry-run` only for diagnostics requested by Rodolfo/Zeus, not for normal
  editorial publishing.

Why: the runner consolidates config, cache lookup, image download/upload,
featured generation, article API, LazyBlock assembly, validation, WP publish,
Yoast update/scoring, cache save, and public URL verification into one command.
This reduces agent LLM roundtrips from ~30+ to ~1-3.

> **REFERENCE - fast runner optimization:** For the Amex baseline, runner rollout
> validation order, deterministic repair lessons, browser/Playwright policy, and
> Rodolfo → Atena request template, see `references/fast-runner-optimization.md`.
> Load it when auditing REC speed/cost or tuning the runner.
>
> **REFERENCE - artifact audit/cleanup:** For the required post-run media manifest,
> safe auto-delete gates for extra WordPress media, and final-summary UX rule, see
> `references/rec-artifact-audit-cleanup.md`. Load it when changing runner media
> handling, investigating Media Library clutter, or reviewing REC loop/error fallout.

## Inputs

Required:
- `card_name` — exact name of the card (e.g. "AIB Visa Gold Card")
- `card_official_url` — official bank page (source of truth)
- `site_key` — key in `/root/mgs-agent/data/sites.json` (e.g. "eggbev")

## Pre-REC duplicate analysis / candidate selection

Use this section when the user asks for card options, pipeline ideas, or a duplicate check before choosing the next REC (e.g. "quais cartões ainda não fizemos?", "não quero duplicar", "me dá opções para gb-cc-en").

1. Resolve WordPress credentials for the requested `site_key`, but never print credentials.
2. Query recent WordPress posts via REST with auth when possible:
   - Prefer `_fields=id,date,status,slug,title,link` to keep output small.
   - If `status=any` is forbidden by the site, fall back to public published posts and clearly treat the result as a published-content scan.
3. Classify existing posts by slug pattern:
   - REC: `rec-{country}-{vertical}-{card_slug}`
   - P1/apply page: `apply-now-{country}-{vertical}-{card_slug}`
4. Normalize card slugs before comparing. Watch for WordPress disambiguation suffixes such as `-2` on REC slugs; compare both exact slug and a suffix-stripped version when assessing duplicates.
5. Report:
   - RECs already published for that vertical/site.
   - P1/apply pages that do not yet have matching REC coverage — these are usually the best next candidates because the user flow already exists.
   - New card opportunities without visible P1, separated from the high-priority list.
6. Lightly validate official source URLs for recommended candidates with a single `curl -L --max-time 10-12` probe only to avoid obviously dead links (404/403/5xx). Do not start full research or browser scraping during candidate analysis.
7. In the user-facing answer, keep it strategic and concise: use a table with priority, card name, and why it is worth doing; avoid exposing credentials, internal file paths, scripts, or raw API errors.

> **Pitfall — duplicate checks are not a publishing pipeline:** Do not ask the 4 REC intake questions just to provide options. The intake questions apply when the user chooses a specific card to create/publish. For option analysis, scan existing posts first, return candidates, and wait for the user's selection.

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

Step 1b enxuto - script faz tudo (validacao, precedencia, fallback).

**Como chamar:**
```bash
../content-publish-wordpress/scripts/resolve-button-color.sh <site_key> [override]
```

Retorna `{hex, source, input}`:
- `hex` - cor `#RRGGBB` validada (usar em `color-botao` do LazyBlock credit-card e `cor-botao` do botao - Step 7)
- `source` - `request_override` ou `site_default`
- `input` - argumento original (ou null)

Override pode ser: hex direto (`#c9a227`) ou nome amigavel em PT (`dourado`, lista em `data/button-colors.json`).
Sem override -> usa `default_button_color` do site em `sites.json`.

> **PITFALL CRITICO - NUNCA inferir cor da marca do cartao:**
> NAO usar vermelho da Santander, azul da Barclaycard, verde da HSBC, etc.
> Sempre usar `default_button_color` do site (consistencia visual da marca eggbev/etc).
> Override so se Rodolfo/Raquel pedirem explicitamente.

### 1.5. Validate URL/Source if provided (CRITICAL - fail fast)

Se a mensagem do usuario contem `URL/Fonte:`, `URL:`, `Fonte:`, `Source:`
(case-insensitive), Atena DEVE validar a URL ANTES de qualquer pesquisa.

**Por que:** evita gastar 30-60s + ~\$0.30 pesquisando cartao quando URL informada
ja resolve direto. Se URL invalida, falha em 1s em vez de 5min de browser_navigate.

**Como detectar URL na mensagem:**
- Padroes aceitos: `URL/Fonte:`, `URL:`, `Fonte:`, `Source:`, `Site:` (case-insensitive)
- Extrair primeiro link http/https que aparecer apos um desses prefixos
- Se mensagem nao tem prefixo URL mas contem 1 unica URL claramente sendo do banco
  (ex: barclaycard.co.uk, hsbc.co.uk), tratar como URL/Fonte fornecida

**Validacao (executar ANTES de Step 2 Research):**

```bash
URL="<url_fornecida>"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
  --max-time 10 -L \
  -A "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36" \
  "$URL")
echo "URL: $URL"
echo "HTTP: $HTTP_CODE"
```

**Decisao baseada em HTTP status:**

| Code | Acao |
|---|---|
| 200 | Continuar pipeline normal, usar URL direto em Step 2 (browser_navigate) |
| 301/302 (com -L curl) | Ja seguiu redirect, usar URL final retornada |
| 403 | Cloudflare/bot block - PARAR e reportar |
| 404 | Cartao nao existe nessa URL - PARAR e reportar |
| 5xx | Tentar 1x apos 30s. Se falhar PARAR |
| timeout/network error | PARAR e reportar |

**Mensagem de PARADA (publicar no Discord, NAO continuar pipeline):**

```
@<solicitante> URL/Fonte fornecida nao acessivel

URL: <url_fornecida>
Status: <http_code> (<descricao>)

Verifique:
1. URL esta correta? (typo, parametros)
2. Cartao ainda existe nesse site?
3. Cole URL atualizada e tento de novo

Pipeline NAO inicia ate URL ser validada (economia ~\$0.30 e 5min).
```

**Quando validacao passa (HTTP 200):**

- Pular DIRETAMENTE para Step 2 com `browser_navigate <URL>`
- NAO pesquisar URL alternativa
- NAO usar Google/web search pra achar pagina
- NAO fazer research preliminar do cartao
- Step 2 (Research) usa essa URL como ponto de partida unico

**PITFALLS criticos:**

> **NUNCA inventar URL alternativa** se a fornecida falhar. Sempre PARAR e pedir nova URL.
> Razao: usuario forneceu URL especifica = espera que Atena use ESSA. Inventar
> URL "parecida" pode levar a cartao errado (ex: barclaycard.co.uk vs barclays.co.uk).

> **NUNCA assumir cartao "similar"** se URL 404. Pode ser nome diferente, produto
> descontinuado, ou troca regional (UK vs US). Reportar e parar.

> **NUNCA pular esta validacao** quando URL fornecida. Mesmo que cartao pareca
> obvio, validar URL primeiro evita 5+ minutos de tentativas se URL ruim.

**Quando NAO ha URL fornecida (mensagem soh tem nome do cartao):**

Comportamento atual continua valendo - Atena pesquisa normalmente em Step 2.
Esta regra eh apenas para o cenario "URL fornecida" (preferred workflow).

**Beneficio mensuravel:**
- Com URL boa: economia ~30-60s + ~\$0.30 por REC
- Com URL ruim: economia ~5min + ~\$1.00 (falha rapida em vez de loop)
- 15 RECs/semana com URL: ~\$4.50 + 15min economizados

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
  - **Tentativa 1:** scraping do site oficial do banco
  - **Tentativa 2 (fallback automático):** Bing Images via Playwright LOCAL (`search-card-image-bing.py`) — acionado quando Tentativa 1 falha (site bloqueia por geo-IP, Cloudflare, etc). Playwright roda headless local, NÃO Browserbase — mais barato e sem bloqueio de geo.
  which prioritizes (in order):
  1. A PNG with transparent background from the official bank page
  2. A PNG from the official bank page (even with background)
  3. A JPG from the official bank page
  4. Only then, a web-search result from an authoritative source
- The script logs which priority tier was used. If tier 3 or 4, the log
  notes it so Raquel knows to expect manual review.
- The image is saved to `/tmp/card-<slug>.<ext>`.

> **PITFALL - CIRCUIT BREAKER quando imagem do cartao falha (CRITICAL - anti-loop):**
>
> Quando search-card-image.sh retorna NEEDS_MANUAL ou imagem de baixa qualidade:
>
> **REGRA DE OURO: O script ja tenta tudo automaticamente. Se retornar NEEDS_MANUAL, PUBLICAR SEM IMAGEM e avisar Raquel. NAO tentar manualmente.**
>
> NUNCA usar delegate_task com sites comparadores (finder.com, moneysupermarket.com, comparethemarket.com, totallymoney.com, money.co.uk). Esses sites bloqueiam Browserbase com Cloudflare e geram loop infinito (caso real 01/05: 149 browser_navigate, $6.37 perdidos, nao publicou).
>
> **Como o script funciona internamente (2 tentativas automaticas):**
>
> **Tentativa 1 - Scraping do site oficial (curl + HTML parsing):**
>   - curl com User-Agent residencial na `card_official_url`
>   - Detecta geo-IP/bot block automaticamente: HTTP 4xx/5xx OU body contendo `Error 1007`, `cf-ray`, `we are sorry an error`, `access denied`
>   - Se bloqueio detectado em <1s: pula IMEDIATAMENTE para Tentativa 2 (sem gastar tempo)
>   - Se pagina carrega: extrai e valida candidatos por score + dimensoes (min 200×100px, aspect 1.2-2.2)
>
> **Tentativa 2 - Bing Images via Playwright LOCAL (`search-card-image-bing.py`):**
>   - Playwright roda headless LOCAL (NAO Browserbase) — sem bloqueio geo-IP, custo ~$0
>   - Busca `{card_name} credit card` no Bing Images, extrai URLs originais via `a.iusc[m]`
>   - Prioriza fontes UK confiáveis: headforpoints.com, backtodefault.com, moneysavingexpert.com
>   - Valida dimensoes e aspect ratio antes de aceitar
>   - Custo: ~15s de CPU local, zero tokens LLM extras
>
> **Se ambas falharem → NEEDS_MANUAL: PUBLICAR ARTIGO SEM CARD IMAGE.** NAO abortar.
>   - LazyBlock credit-card vai com `imagem` vazio (URL e ID null) - Raquel preenche manualmente
>   - Featured image AINDA gera normalmente via Step 4 (Gemini compoe usando placeholder)
>   - Step 13 (return summary) inclui aviso explicito ao Raquel - ver bloco "Card image manual" no template
>
> **LIMITES DUROS - anti-loop (forcar parada):**
>   - MAX 5 browser_navigate por sessao de REC inteira (nao 149!)
>   - MAX 3 minutos no Step 3 inteiro (timeout)
>   - Se exceder qualquer limite: encerrar Step 3 e ir pra fluxo "sem imagem"
>
> **NUNCA fazer (causou perda de $6.37 em 01/05/2026):**
>   - Wayback Machine para imagens (raramente funciona, sempre custa caro)
>   - Bing/Google image search via **browser_navigate** em loop (usar `search-card-image-bing.py` que roda Playwright LOCAL, não Browserbase — o script faz isso automaticamente)
>   - Tentar dezenas de sites comparadores manualmente
>   - Insistir apos script retornar NEEDS_MANUAL
>   - Variar URLs do mesmo site procurando imagem
>
> Custo de loop ate auto-prune Hermes: $5-10 USD por sessao perdida.
> Custo de abortar e publicar sem imagem: $0.50-1.00 USD.
>


>


> **REFERENCE - issuer-specific quirks:** Para detalhes especificos por banco
> (Capital One UK, Barclays vs Barclaycard, multi-card pages, vertical orientation,
> crop white borders, WP auto-rename, filename arg), ver
> `references/card-image-quirks.md` (carregada sob demanda via `view`).
>
> Carregue essa reference quando: search-card-image.sh retornar resultado suspeito,
> issuer for Capital One/Barclaycard/HSBC, ou ao processar imagem com problemas
> conhecidos (rotation, crop, MIME type).
>
- Upload via `content-publish-wordpress/scripts/upload-image.sh` →
  `{id, source_url, mime_type}` — this is the **card_media**.



### 4. Featured image (composition)
- Run `scripts/generate-featured-image.sh <slug> <card_image_path>` which
  calls Gemini 2.5 Flash Image with the uploaded card image (as inline
  base64 reference) and a random scene from the environments list
  (modern financial district, upscale café, luxury hotel lounge, premium
  office, elegant home interior, rooftop with skyline, airport lounge,
  contemporary coworking, urban street with cinematic blur, city at sunset,
  nighttime metropolis).
- Output: 16:9 JPEG at `/tmp/featured-<slug>.jpg` (auto-compressed via `compress-image.sh`: PNG 2 MB → JPEG ~150 KB, quality 88, max 1280px wide).
- VALIDATE LOCALLY BEFORE UPLOAD: use `vision_analyze` on `/tmp/featured-<slug>.jpg` and confirm the card in the composition is visually identical to the card_media (issuer design, layout, colours, sample text placement). If not, regenerate (retry up to 2x). If still broken, abort with a clear message.
- Only after the local vision check passes, upload via `upload-image.sh` → `{id, source_url, mime_type}` — this is the **featured_media**.

> **PITFALL — do not upload failed featured generations:** Gemini can produce a professional-looking image with a generic/altered Amex-style card. Uploading before visual validation leaves orphan media in WordPress and can confuse the final summary. Validate the local `/tmp/featured-<slug>.jpg` first; upload only the approved final image.

### 4b. Theme HTML quirks (per-site)

> **REFERENCE - eggbev theme quirks:** O tema `jbf-wp-theme-main` (eggbev.com)
> tem regras especificas pra wp:html sanitization, comparative tables, e REST
> API. Ver `references/site-quirks-eggbev.md` (carregada sob demanda via `view`).
>
> Carregue essa reference quando publicar em eggbev.com (sempre).
>
> Outros sites MGS (futuro) terao referencias proprias `references/site-quirks-{site}.md`.

### 5. Write the article (DEPRECATED - use Step 5b API)

Step 5 manual writing was DEPRECATED em 29/04/2026. **SEMPRE use Step 5b** (mgs-rec-api).

**Fallback de emergencia (apenas se API estiver down):**
- Verificar `/health` da API: `curl -s http://127.0.0.1:8001/health`
- Se API down: instruir LLM a escrever artigo seguindo o template carregado em Step 1
- Estrutura obrigatoria: intro + H2 Key Benefits + H2 How Does It Work + H2 Comparative Table + H2 Who Is This Card Best For
- Word count: 450-500 palavras (validar com Step 6)
- Reportar API down ao Rodolfo no Discord para investigacao

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

### 9. Title and Yoast SEO fields

Step 9 enxuto - constraints universais (todos sites MGS, todos templates).

Regras de **conteudo/tom/idioma** ficam no template (`templates/rec-{template_key}.md`,
secao "SEO FIELDS") - ver template carregado em Step 1.

**Constraints tecnicos universais (TODOS sites MGS):**

| Campo | Limite |
|---|---|
| `post_title` | max 60 chars, contem focus keyphrase, SEM suffix de site |
| `_yoast_wpseo_title` | DEIXAR VAZIO (Yoast inherita global template do site) |
| `_yoast_wpseo_metadesc` | 120-130 chars (sweet spot 128), focus keyphrase nos primeiros 100 chars |
| `_yoast_wpseo_focuskw` | max 4 palavras, aparece em title + metadesc + 1o paragrafo |

**Pitfalls criticos:**
- NUNCA preencher `_yoast_wpseo_title` (override quebra consistencia do site - ver post 62026 historico)
- Sempre validar EXACT char count antes de salvar (nao estimar)
- Se card_name >60 chars: abreviar mantendo focus keyphrase (ex: "Capital One Classic Credit Card" -> "Capital One Classic")

Demais regras (tom, exemplos, casos por idioma) -> template.

### 10. Resolve taxonomy IDs

Mandatory tags (in order), coming from config + card_slug:
1. `"rec"` — the article type
2. `"{vertical}"` — e.g. `"cc"`
3. `"{country}"` — e.g. `"gb"`
4. `"{card name words}"` — the card slug converted to spaces, e.g. `"aib visa gold"` (no hyphens)
5. `"lang_{language}"` — derived from the last segment of `template_key` (e.g. `gb-cc-en` → `"lang_en"`, `mx-cc-es` → `"lang_es"`, `br-loans-pt` → `"lang_pt"`). **Always include. Applies to all sites and verticals.**
6. `"atena_agent"` — always include on any article published or edited by Atena.

Plus **2–4 SEO tags chosen by the writer** based on the card's main benefits
(examples: `"travel credit card"`, `"airport lounge access"`, `"no annual fee"`,
`"cashback rewards"`). Multi-word tags must be resolved as the human-readable
name (WP auto-slugs to kebab-case — e.g. `"travel credit card"` →
slug `travel-credit-card`). If you need the slug explicitly, compute:
lowercase, spaces → `-`, strip non-alphanumeric.

Total: 8–10 tags.

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

> **REFERENCE - yoast scorer internals:** Para PITFALLs internos do scorer
> (yoastseo v3.6 API quirks, RunCloud ASCII art, wp yoast index limitations,
> node_modules path), ver `references/yoast-scorer-internals.md` (carregada
> sob demanda via `view`).
>
> Atena normalmente NAO precisa carregar isso - so executa o script e le o
> JSON. Carregue apenas se precisar debugar o script ou modificar o engine.





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
- Auditoria de artefatos: imagens criadas nesta execução, usadas, extras e cleanup aplicado
- Cost reporting (Step 14 — duração, API calls, custo USD)
- @Raquel mention (<@1496254952501280974>) for review notification

> **PITFALL — reportar TODAS as imagens criadas (CRITICAL):**
> Se a execução gerar/uploadar 6 imagens e usar apenas 2, Atena DEVE informar isso no resumo final. Nunca reportar só o erro principal ou só as imagens usadas. O usuário não deve precisar abrir WordPress → Media Library para descobrir órfãs.
>
> Regra operacional:
> - Audit mínimo antes do report final: post existe, featured_media setada, card image presente no conteúdo/LazyBlock, e contagem de media criadas no run.
> - Cleanup automático pós-publicação: deletar imagens extras somente quando forem uploads da própria execução e não estiverem em `featured_media`, no HTML do post, nem anexadas a outro post.
> - Se a segurança não for 100%, NÃO deletar; reportar Media IDs e pedir decisão.
> - Quando usar `mgs-rec-runner.py`, ler `images.artifact_audit` do JSON e refletir no resumo final.

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
• Card image ID: {card_id} — <{card_url}>
• Featured image ID: {featured_id} — <{featured_url}> (cena: {featured_scene})
• Audit: {created_count} criadas | {used_count} usadas | {extra_count} extras | {deleted_count} deletadas

💰 Custo: ${cost} USD ({duration}, {api_calls} API calls)

@Raquel artigo pronto para revisão! 👀

---

### LOGICA DE ESCOLHA (CRITICAL): qual template usar?

**Voce DEVE escolher UM template e usar SO ele. NUNCA combinar os dois.**

- Se publicacao foi 100% OK (incluindo card image): usar **TEMPLATE A — NORMAL** (acima)
- Se Circuit Breaker disparou (card image NAO publicada): usar **TEMPLATE B — SEM IMAGEM** (abaixo)

Como detectar qual template usar:
- `card_image_id` foi preenchido com numero valido + upload retornou 200? → **TEMPLATE A**
- `card_image_id` ficou null / Step 3 abortou apos 2 tentativas / blacklist? → **TEMPLATE B**

---

### TEMPLATE B — Circuit Breaker disparou (publicado SEM card image)

Use ESTE template (e SO este, nao combinar com Template A) quando o Step 3 nao conseguiu obter a imagem do cartao:

```
@Rodolfo ⚠️ {Card Name} publicado no {site} (SEM card image)

📄 Post ID: {id}
🔗 {public_url}
✏️ Edit: {edit_url}

📊 Yoast: SEO {seo}🟢 | Readability {read}🟢
📝 {words} palavras | Title {title_chars}c | Sub-Title {subtitle_chars}c | Meta {meta_chars}c
🔍 Focus: "{focus_kw}"
🏷️ Tags: {tags_csv}

🖼️ Imagens:
• ⚠️ Card image: NAO PUBLICADA (issuer bloqueia automacao ou imagem rejeitada)
• Featured image ID: {featured_id} — <{featured_url}> (cena: {featured_scene})

💰 Custo: ${cost} USD ({duration}, {api_calls} API calls)

⚠️ @Raquel ATENCAO: card image precisa upload manual!
   Issuer: {issuer_name}
   Motivo: {reason} (ex: Cloudflare bot block, blacklisted issuer, image quality)
   Google Images: <https://www.google.com/search?q={card_slug_url_encoded}&udm=2>
   Acao: editar post {id} no WP, abrir LazyBlock credit-card, fazer upload da imagem do cartao
```

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

## Post operations (find by slug / delete) - reference

> **REFERENCE - post operations:** Para operacoes auxiliares em posts
> ja publicados (achar post pelo slug quando REST API retorna vazio,
> deletar post + media juntos durante re-publish), ver
> `references/post-operations.md` (carregada sob demanda via `view`).
>
> Carregue essa reference quando: precisar deletar/recriar post, fazer
> cleanup, ou se `check-slug-conflict.sh` retornar WARN posts_query_zero_results.

## Failure modes

- Template missing → abort
- Card page unfetchable → abort (never invent data)
- Card image not found in any tier → **NAO ABORTAR**. Publicar sem imagem + avisar Raquel (ver Circuit Breaker em Step 3 e bloco condicional em Step 13)
- Word count out of 450–500 after 2 retries → abort
- Gemini composition fails after 2 retries → abort
- WP publish failure → log full response, abort
- Yoast verify mismatch → log and surface to user (post still exists, but meta needs manual fix)

## Step 14 - Cost reporting (mandatory after publish)

Apos completar Step 13 (Return summary com mensagem unica), SEMPRE incluir bloco de custo na MESMA mensagem. Zero latencia, sem segunda mensagem, sem esperar cron.

### Como calcular custo na hora (state.db delta)

Atena calcula custo real baseado nos tokens da propria sessao. IMPORTANTE: Atena pode dividir uma execucao em multiplas sessoes (parent + children quando auto-prune trigga). O calculo precisa SOMAR parent + children via parent_session_id.

#### Schema relevante

Tabela sessions em /root/.hermes/profiles/atena/state.db:
- id TEXT PRIMARY KEY (formato: 20260429_160151_27c93f7f)
- parent_session_id TEXT (aponta pra sessao pai quando ha split)
- input_tokens, output_tokens INTEGER
- cache_read_tokens, cache_write_tokens INTEGER
- tool_call_count INTEGER
- started_at, ended_at REAL (epoch float)

#### Passo 1 - identificar parent session

PARENT_ID=$(sqlite3 /root/.hermes/profiles/atena/state.db "SELECT COALESCE(parent_session_id, id) FROM sessions ORDER BY started_at DESC LIMIT 1;")

#### Passo 2 - somar tokens parent + children via Python

import sqlite3
conn = sqlite3.connect("/root/.hermes/profiles/atena/state.db")
cur = conn.execute("SELECT SUM(input_tokens), SUM(output_tokens), SUM(cache_read_tokens), SUM(cache_write_tokens), SUM(tool_call_count), MIN(started_at), MAX(COALESCE(ended_at, started_at)) FROM sessions WHERE id = ? OR parent_session_id = ?", (PARENT_ID, PARENT_ID))
i, o, cr, cw, tools, start, end = cur.fetchone()
conn.close()

# Pricing Sonnet 4.6 (USD per million tokens)
# ⚠️  SINGLE SOURCE OF TRUTH: references/pricing.md
# Se atualizar aqui, atualizar TAMBÉM em api/generate-rec-api.py + scripts/track-article-cost.sh
atena_cost = (i*3.00 + o*15.00 + cr*0.30 + cw*3.75) / 1_000_000
duration_min = round((end - start) / 60, 1) if start and end else 0

#### Passo 3 - somar custo da API (PATCH 15 - api_cost via query agregada)

A API mgs-rec-api pode ser chamada MAIS DE UMA VEZ por REC (refinement, retry).
NAO usar `response.get("cost_usd")` da resposta - so pega a ultima chamada e
sub-reporta custo.

**Em vez disso, somar TODAS chamadas desse REC via query SQL:**

```bash
# REC_START_TS foi capturado no Step 5b ANTES da primeira chamada
API_COST=$(sqlite3 /root/mgs-agent/api/usage.db "
SELECT printf('%.4f', COALESCE(SUM(cost_usd), 0))
FROM api_calls
WHERE card_slug = '$CARD_SLUG'
  AND timestamp >= '$REC_START_TS';
")
API_CALLS=$(sqlite3 /root/mgs-agent/api/usage.db "
SELECT COUNT(*)
FROM api_calls
WHERE card_slug = '$CARD_SLUG'
  AND timestamp >= '$REC_START_TS';
")
```

Em Python equivalente:

```python
import sqlite3
conn = sqlite3.connect("/root/mgs-agent/api/usage.db")
cur = conn.execute(
    "SELECT COALESCE(SUM(cost_usd), 0), COUNT(*) FROM api_calls WHERE card_slug=? AND timestamp>=?",
    (card_slug, rec_start_ts)
)
api_cost, api_calls = cur.fetchone()
conn.close()
```

total_cost = atena_cost + api_cost

#### Passo 4 - incluir bloco no template do Step 13

Custo: total_cost USD (duration_min, tools tools)
   Atena: atena_cost | API: api_cost (api_calls calls)

NOTA: api_calls vem da query agregada do Passo 3 (COUNT(*)).
Se api_calls > 1, foi refinement/retry - normal mas vale logar.

### Pricing Sonnet 4.6 (USD per million tokens)

- input: 3.00
- output: 15.00
- cache_read: 0.30
- cache_write: 3.75

Se mudarem, atualizar tambem em /root/mgs-agent/api/generate-rec-api.py e /root/mgs-agent/scripts/track-article-cost.sh.

### Por que parent_session_id

Hermes faz auto-prune/split quando sessao fica grande. Uma execucao do REC pode virar 2-3 sessoes. Sem agregar via parent_session_id, custo aparece subestimado em ate 70%.

Validacao empirica do REC Halifax 62039 (29/04/2026):
- Sessao parent: 20260429_160151_27c93f7f
- Sessao child:  20260429_160240_579083
- Total agregado: 2.01 Atena + 0.03 API = 2.04
- Sem agregar: subestima em 50%

### Por que NAO usar Admin API ou cron

- Admin API tem latencia 30-60min (Anthropic agrega depois)
- Cron track-article-cost.sh usa Admin API (mesma latencia)
- state.db eh LOCAL, instantaneo, fonte de verdade
- Discrepancia menor que 2 por cento (insignificante)

Cron 15min continua rodando pra reconciliacao historica no DB tracker (separado).

### Custo desta secao (overhead)

- 1 query SQL no state.db: 0 tokens LLM
- 1 calculo Python: 0 tokens LLM
- Bloco no Discord: 30 tokens output adicionais

Total: 30 tokens output extras por REC. Negligenciavel.

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

    # IMPORTANTE: capturar timestamp ANTES da primeira chamada API
    # (usado no Step 14 pra somar TODAS chamadas desse REC via query agregada)
    REC_START_TS=$(date -u +%Y-%m-%dT%H:%M:%S.000000Z)
    echo "REC_START_TS=$REC_START_TS"  # GUARDAR pra Step 14

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

    echo "Article generated via API: cost=\$$COST duration=${DURATION}s (PARCIAL - so esta chamada)"
    # NOTA: Step 14 vai SOMAR todas chamadas via query SQL (nao usar este COST diretamente)

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