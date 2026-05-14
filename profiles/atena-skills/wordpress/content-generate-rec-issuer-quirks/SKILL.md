---
name: content-generate-rec-issuer-quirks
description: >
  Companion reference for content-generate-rec. Issuer-specific URL quirks,
  image CDN patterns, HTML post-processing fixes, and geo-block workarounds
  (Bing Images + Playwright local fallback for blocked domains like lloydsbank.com).
  Load this alongside content-generate-rec when the issuer is American Express UK,
  Barclaycard, Capital One UK, NatWest, or Lloyds Bank.
---

# content-generate-rec — Issuer Quirks & Post-Processing Reference

Companion to `content-generate-rec`. Contains pitfalls and patterns discovered
in live REC sessions that are too issuer-specific for the main SKILL.md but
critical enough to encode.

**Support files:**
- `references/subtitle-rewrite-patterns.md` — confirmed ≤100-char subtitle examples + cascade fix pattern
- `references/playwright-local-install.md` — Playwright local: install steps on MGS server, usage pattern for Bing Images scraping, geo-block vs bot-block distinction

---

## 1. American Express UK

### URL Discovery (CRITICAL)
Card-specific URLs on `americanexpress.com/en-gb` do NOT follow a guessable
pattern. All attempts to construct slug from card name return 404:
- `/credit-cards/british-airways/` → 404
- `/cards/ba-plus/` → 404
- `/credit-cards/british-airways-american-express-premium-plus-card/` → 404

**Correct approach:** Delegate a sub-task to navigate to the personal sitemap:
```
https://www.americanexpress.com/en-gb/sitemap/personal.html
```
This lists all active personal cards with real URLs.

**Known real URLs (as of Apr 2026):**
| Card | URL path |
|------|----------|
| BA Premium Plus | `/en-gb/credit-cards/ba-premium-plus-credit-card/` |
| Platinum Card | `/en-gb/credit-cards/the-platinum-card/` |
| Gold Card | `/en-gb/credit-cards/american-express-gold-card/` |
| Preferred Rewards Gold | `/en-gb/credit-cards/preferred-rewards-gold-credit-card/` |

### Card Image CDN
Amex hosts card images at a predictable CDN path:
```
https://icm.aexp-static.com/Internet/internationalcardshop/en_gb/images/cards/UK_AXP_<Name_With_Underscores>.png
```
Example:
```
https://icm.aexp-static.com/Internet/internationalcardshop/en_gb/images/cards/UK_AXP_British_Airways_American_Express_Premium_Plus_Card.png
```
- Images are 480×304px RGBA PNG — landscape orientation, no white borders.
- Download with `Referer: https://www.americanexpress.com/`
- `search-card-image.sh` will return `NEEDS_MANUAL` for Amex (page has no direct `<img>` tags parseable by the script). Skip the script and download CDN image directly via curl.

### When `search-card-image.sh` returns `NEEDS_MANUAL` for Amex
1. Try the CDN URL pattern above (construct from card name)
2. If uncertain about the exact filename: delegate a sub-task with browser tools
   to load `https://www.americanexpress.com/en-gb/credit-cards/all-cards/` and
   run `browser_get_images` — all card CDN URLs appear there
3. Download with curl + Referer header
4. Verify with vision_analyze before proceeding

---

## 2. Barclaycard

### Separate Domain from Barclays
- Barclays Bank → `barclays.co.uk`
- Barclaycard credit cards → `barclaycard.co.uk`

URL pattern for Barclaycard: `https://www.barclaycard.co.uk/personal/credit-cards/<slug>`

### Annual Fee Format
Barclaycard Avios Plus fee: **£20/month** (not annual).
Display in comparative tables as `£20/mo` — do NOT convert to `£240/yr` as the
official page uses monthly pricing. Consistency with source is important.

### Multi-Card Pages
Barclaycard pages may show multiple card images. `search-card-image.sh` can pick
the wrong one (e.g. generic Rewards card instead of Avios Plus).
Always verify downloaded image with `vision_analyze` before proceeding.

---

## 3. Capital One UK

Card-specific subpages unavailable — use homepage only:
```
https://www.capitalone.co.uk/
```
Card image URL (Classic Card):
```
https://www.capitalone.co.uk/cloud_assets/webp/contactless-card-image.webp
```
RGBA webp — handle 4-channel pixels in crop loop (see main SKILL.md pitfall).

---

## 4. NatWest

### Card Image
- Official page: `https://www.natwest.com/credit-cards/reward-credit-card.html`
- Card image URL (Reward Credit Card, as of 2026-05):
  ```
  https://www.natwest.com/credit-cards/reward-credit-card/_jcr_content/root/responsivegrid/container_1115300139/productcardshelf_cop/productcard_0/card_right_image.coreimg.png/1767607794625/nw-credit-card-reward-470x2642x.png
  ```
- Image: 940×528px PNG, sRGB, horizontal/landscape — no rotation needed.
- Download with:
  - `User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36`
  - `Referer: https://www.natwest.com/credit-cards/reward-credit-card.html`
- NatWest is **NOT blacklisted** — direct curl works reliably (confirmed 2026-05-02).
- The image has a white/light background area around the card — **always crop** with the pixel-detection method before upload.

### Page Data (Reward Credit Card)
| Field | Value |
|-------|-------|
| Annual fee | £24 (£0 with NatWest Reward current account) |
| Purchase APR | 25.9% p.a. (variable) |
| Representative APR | 31.0% (variable) |
| Supermarket rewards | 1% back in Rewards |
| Other spending | 0.25% back |
| Partner retailers | 1–15% via MyRewards |
| Eligibility min income | £10,000/year |

---

## 5. API HTML Post-Processing

### Malformed Closing Tags from mgs-rec-api
The API sometimes returns `<!-- /w:heading -->` (missing `p`) instead of
`<!-- /wp:heading -->`. This can also cause duplicate H2 blocks when the API
regenerates the block after the malformed tag.

**Always scan API-returned HTML for these before assembling:**
```python
content = content.replace('<!-- /w:heading -->', '<!-- /wp:heading -->')
```

### Duplicate H2 Blocks
If the API returns two consecutive identical H2 blocks (usually "How Does It Work"),
remove the first one — keep the second (it's the regenerated correct version).

```python
# Pattern: two identical H2s back to back — collapse to one
import re
content = re.sub(
    r'(<!-- wp:heading \{"level":2\} -->\n<h2>[^<]+<\/h2>\n<!-- \/wp:heading -->)\n\n\1',
    r'\1',
    content
)
```

### Table Style Injection
The API does not add `style="font-size:85%"` to `<table>` elements.
Always inject before upload:
```python
content = content.replace('<table><thead>', '<table class="has-fixed-layout" style="font-size:85%"><thead>')
```

### Subtitle Length — API Consistently Over-Generates
The API tends to generate subtitles in the **140–160 char range**, failing the
100-char hard limit. This is a systematic issue, not a one-off.

**Always check subtitle length immediately after receiving the API response.**
Do NOT proceed to LazyBlock assembly or file writing until subtitle is ≤100 chars.

Rewrite pattern: `{Card Name} {ONE benefit}. {ONE secondary fact if fits.}`
- Drop "with annual fee waived for X" type clauses — they push past 100 chars.
- Confirmed working (89 chars):
  `"NatWest Reward Credit Card earns 1% back on groceries and up to 15% at partner retailers."`

**Cascade warning:** Rewriting the subtitle to ≤100 chars removes ~10–15 words.
If the body was at 451 words, it will drop to ~438–441. Expand 1–2 paragraphs
by one clause each (~10 words total) before re-validating. Re-validation is
mandatory — do not assume a prior PASS still holds.

---

## 6. Lloyds Bank (lloydsbank.com) — BLACKLISTED (site oficial)

**Status:** Site oficial totalmente bloqueado por geolocalização de IP — confirmado 01/05/2026 e reconfirmado 14/05/2026.

Tanto `mcp_browser_navigate` (Browserbase) quanto `curl` e **Playwright local** são bloqueados quando o IP não é UK:
- Qualquer URL em `lloydsbank.com` retorna **Error 1007** (página de erro do banco, não Cloudflare wall) — sem conteúdo de cartão.
- Aplica-se a **todas as páginas** do domínio, incluindo a homepage.

**MBNA vs Lloyds Bank:**
- MBNA UK (`mbna.co.uk`) — Lloyds Banking Group, também bloqueado
- Lloyds Bank (`lloydsbank.com`) — bloqueado por geolocalização de IP (não-UK)
- Ambos → não tentar site oficial, ir direto para fallback abaixo

---

### Fallback de card image: Bing Images + Playwright local (PREFERIDO)

> **Descoberto em 14/05/2026** — Bing Images funciona e produz imagens reais de alta qualidade do cartão. Usar ANTES de qualquer Template B.

**Por que Bing e não Google Images?**
- Google Images bloqueia o IP do servidor com CAPTCHA ("sorry" redirect)
- Bing Images funciona sem bloqueio e retorna URLs de imagem originais (alta res)

**Por que Playwright local e não `mcp_browser_navigate`?**
- `mcp_browser_navigate` usa Browserbase (cloud remoto) — IP não-UK, bloqueado
- Playwright local (`python3 - <<'EOF'...`) roda diretamente na máquina — também bloqueado no lloydsbank.com, mas **funciona para Bing Images**

**Procedimento completo:**

1. Verificar que playwright está instalado:
```bash
python3 -c "from playwright.sync_api import sync_playwright; print('ok')"
# Se ModuleNotFoundError: instalar com
python3 /tmp/pip_extracted/pip install playwright --break-system-packages -q
python3 -m playwright install chromium
# (pip está em /usr/share/python-wheels/pip-24.0-py3-none-any.whl — extrair se necessário)
```

2. Buscar no Bing e extrair URLs originais via atributo `m` (JSON com campo `murl`):
```python
from playwright.sync_api import sync_playwright
import json, time

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        viewport={"width": 1280, "height": 900}
    )
    page = context.new_page()
    page.goto("https://www.bing.com/images/search?q=lloyds+bank+world+elite+mastercard+credit+card&qft=+filterui:imagesize-large", timeout=30000)
    time.sleep(3)

    items = page.query_selector_all('a.iusc')
    for item in items[:20]:
        m_attr = item.get_attribute('m')
        if m_attr:
            data = json.loads(m_attr)
            print(data.get('murl', ''), '|', data.get('t', '')[:80])
    browser.close()
```

3. Baixar as melhores candidatas (priorizar: headforpoints.com > comparadores UK > blogs):
```python
import urllib.request
headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)..."}
req = urllib.request.Request(url, headers=headers)
data = urllib.request.urlopen(req, timeout=15).read()
with open('/tmp/lloyds_card.jpg', 'wb') as f:
    f.write(data)
```

4. Verificar com `vision_analyze` se é o cartão correto, horizontal (landscape), sem logo errado.

5. Aplicar crop pixel-level (remover bordas brancas) conforme padrão do SKILL principal.

**Fontes confiáveis encontradas para Lloyds World Elite Mastercard (2026):**
| URL | Dimensões | Observação |
|-----|-----------|------------|
| `https://www.headforpoints.com/wp-content/uploads/2025/05/HFP-Lloyds-Mastecard-World-Elite-2.webp` | 1300×860 | ✅ Melhor opção — landscape, 2025, cartão real |
| `https://backtodefault.com/wp-content/uploads/2025/07/Lloyds-Bank-World-Elite-Mastercard-750x450.jpg` | 750×450 | ✅ Landscape, 2025 |
| `https://www.headforpoints.com/wp-content/uploads/2023/11/Lloyds-World-Elite-Mastercard.jpg` | — | ⚠️ Portrait/inclinado |

---

### Fallback final: Template B (apenas se Bing também falhar)

Somente ir para Template B se o Bing retornar zero resultados úteis ou todas as imagens forem de outros bancos/cartões genéricos.

**Featured image workaround quando não há card image:**
```python
from PIL import Image, ImageDraw
W, H = 856, 540
img = Image.new('RGB', (W, H), '#16213e')
draw = ImageDraw.Draw(img)
img.save('/tmp/card-placeholder-generic.png', 'PNG')
```
Passar como `card_image_path` para o Gemini. Raquel substitui durante revisão.

---

### Card data (Step 2) para lloydsbank.com

Para buscar dados do cartão (features, APR, fees) sem acessar o site oficial:
- Use web search direta (não browser) — os dados do cartão aparecem em snippets e comparadores UK
- Fontes confiáveis: headforpoints.com, moneysavingexpert.com, finder.com/uk
- NÃO usar `delegate_task` com browser toolset — vai bloquear no mesmo Error 1007

---

## 7. Upload-Image MIME Detection Pitfall (CRITICAL)

`upload-image.sh` detects MIME type from the **filename argument** (3rd arg), not from file magic bytes. The detection regex is:
```bash
case "${FILENAME,,}" in
  *.jpg|*.jpeg) mime="image/jpeg" ;;
  *.webp)       mime="image/webp" ;;
  ...
esac
```
Default fallback is `image/png`.

**If you pass a filename WITHOUT extension, WP rejects with HTTP 500 `rest_upload_sideload_error`.**

✅ CORRECT: `upload-image.sh eggbev /tmp/featured-foo.jpg featured-foo.jpg`
❌ WRONG:   `upload-image.sh eggbev /tmp/featured-foo.jpg featured-foo` → HTTP 500

**Rule:** always include the file extension in the 3rd argument (`filename` param). Even if the 4th arg (alt text/title) is what changed, 3rd arg must have `.jpg`/`.png`/`.webp`.

---

## 8. Focus Keyword Abbreviation for Long Card Names

When the official card name has >4 words (Yoast max), abbreviate for focuskw:
| Card name (full) | Focus KW (≤4 words) |
|-----------------|---------------------|
| British Airways American Express Premium Plus Card | `BA Amex Premium Plus` |
| Barclaycard Avios Plus Credit Card | `Barclaycard Avios Plus` |
| Capital One Classic Credit Card | `Capital One Classic` |

Also adjust `post_title` to ≤60 chars using the same abbreviation, so title
and focuskw are consistent:
- BAD: `British Airways Amex Premium Plus: Earn Avios & Companion Voucher` (65 chars)
- GOOD: `BA Amex Premium Plus: Earn Avios & Companion Voucher` (52 chars)
