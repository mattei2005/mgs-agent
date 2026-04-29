---
name: content-generate-rec-issuer-quirks
description: >
  Companion reference for content-generate-rec. Issuer-specific URL quirks,
  image CDN patterns, and HTML post-processing fixes discovered during REC
  pipeline runs. Load this alongside content-generate-rec when the issuer is
  American Express UK, Barclaycard, or Capital One UK.
---

# content-generate-rec — Issuer Quirks & Post-Processing Reference

Companion to `content-generate-rec`. Contains pitfalls and patterns discovered
in live REC sessions that are too issuer-specific for the main SKILL.md but
critical enough to encode.

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

## 4. API HTML Post-Processing

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

---

## 5. Focus Keyword Abbreviation for Long Card Names

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
