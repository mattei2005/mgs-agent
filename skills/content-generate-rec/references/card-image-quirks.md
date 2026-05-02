# Card image - issuer-specific quirks

Reference loaded ON DEMAND quando Atena precisa de detalhes especificos por banco.
Carregada via `view references/card-image-quirks.md` quando o issuer eh Capital One,
Barclays/Barclaycard, ou quando search-card-image.sh retorna problema.

---

## Capital One UK - homepage is the only reliable data source

Capital One UK (`capitalone.co.uk`) returns "page not available" for almost all
subpage URLs including `/credit-cards/classic`, `/credit-cards/classic-credit-card`,
and `/credit-cards/credit-cards-for-bad-credit`. The **homepage** (`https://www.capitalone.co.uk/`)
is the only page that reliably loads and contains key card data (credit limits,
APR, benefits) for both the Classic Card and Balance Transfer Card.

Card image: use `https://www.capitalone.co.uk/cloud_assets/webp/contactless-card-image.webp`
(1154x724px RGBA webp) - clean isolated card shot, no hands. Download with a
`Referer: https://www.capitalone.co.uk/` header. The image has no white borders
so the crop step returns identical bounds (still run it for correctness).

RGBA handling: when the downloaded image is RGBA mode (webp with alpha), the
pixel loop must unpack 4 channels: `r, g, b, a = arr[x, y]`. Also gate on
`a > 20` to skip fully transparent pixels before checking brightness thresholds.
Otherwise the crop bounds will be wrong.

---

## Barclays vs Barclaycard - two separate domains

Barclays Bank (`barclays.co.uk`) and Barclaycard (`barclaycard.co.uk`) are
separate UK entities with separate card pages. Credit cards branded
"Barclaycard" (Avios Plus, Avios, Rewards, Platinum, etc.) live at
`https://www.barclaycard.co.uk/personal/credit-cards/<slug>`, NOT at
`barclays.co.uk/credit-cards/<slug>` - that path 404s for Barclaycard
products. Always confirm the correct domain before fetching card data.

---

## search-card-image.sh may select wrong card on multi-card pages

Some bank pages (especially Barclaycard) display multiple card images -
e.g. a generic "Rewards" card thumbnail alongside the specific Avios Plus
card. The scoring algorithm picks the highest-scoring PNG by keyword match,
which may not be the correct card if a generic card image scores higher or
equally due to naming conventions (e.g. `rewards-vertical-tombstone.png`
outscoring `AviosPlus-front.png` due to keyword overlap).

**Always verify the downloaded card image with `mcp_vision_analyze` before
proceeding**, asking: "Is this the [exact card name] card?" If the script
picked the wrong card, identify the correct image URL from
`browser_get_images` output and download it manually with curl.

Example for Barclaycard Avios Plus: the script may grab the generic
Barclaycard Rewards PNG; the correct image is the one explicitly named
`AviosPlus-front` in the page's image list.

---

## Card image must be HORIZONTAL (landscape) orientation

After downloading the candidate image, verify it is in landscape orientation
(width > height) before uploading. Modern bank cards (HSBC, Barclays, etc.)
increasingly use a vertical/portrait format on their websites, but the
LazyBlock card component expects a horizontal card for correct layout.

How to check: use `mcp_vision_analyze` on the downloaded image and ask
"Is this card horizontal (landscape) or vertical (portrait)?"

If the image is vertical -> rotate it 90 degrees using Python/PIL:

```python
from PIL import Image
img = Image.open('/tmp/card-<slug>.<ext>')
img_rotated = img.rotate(-90, expand=True)  # -90 = clockwise
img_rotated.save('/tmp/card-<slug>.<ext>')
```

**Do NOT search for alternative versions. Do NOT use images from other sources
(e.g. business cards, old versions). Always rotate the official image.**
**Do NOT upload a vertical card image.** It will render incorrectly in the
LazyBlock and require a manual fix pass.

---

## Card image must be cropped to card edges

After downloading and rotating (if needed), always crop the image to remove
any white borders or padding around the card. Use pixel-level detection:

```python
from PIL import Image
img = Image.open('/tmp/card-<slug>.<ext>')
arr = img.load()
w, h = img.size
left, right, top, bottom = w, 0, h, 0
for y in range(h):
    for x in range(w):
        r, g, b = arr[x, y]
        if r < 235 or g < 235 or b < 235:
            if x < left: left = x
            if x > right: right = x
            if y < top: top = y
            if y > bottom: bottom = y
pad = 3
cropped = img.crop((max(0,left-pad), max(0,top-pad), min(w,right+pad), min(h,bottom+pad)))
cropped.save('/tmp/card-<slug>.<ext>', quality=95)
```

Verify the result with vision_analyze: "Does the card have white borders?" If yes, crop again.
**Always crop before upload** - white borders render poorly in the LazyBlock card component.

---

## WordPress auto-renames duplicate filenames

When you upload a file with a name that already exists in the media library,
WordPress automatically appends a numeric suffix (e.g. `hsbc-premier-credit-card.jpg`
becomes `hsbc-premier-credit-card-1.jpg`). The `source_url` returned by the
upload response will contain the **renamed URL** (with the suffix), not the
original filename you passed.

**Always use the `source_url` AND `id` from the upload response** when building
the LazyBlock `imagem` JSON - never hardcode or reconstruct the URL from the
filename argument. The upload response is the single source of truth.

Example:
```bash
result=$(upload-image.sh eggbev /tmp/card.jpg "hsbc-premier-credit-card.jpg")
card_id=$(echo $result | jq -r '.id')          # e.g. 61970
card_url=$(echo $result | jq -r '.source_url') # e.g. .../hsbc-premier-credit-card-1.jpg
```

Use `card_id` and `card_url` from this result - NEVER derive the URL from the
filename string you passed.

---

## upload-image.sh filename argument - MIME type detection

`upload-image.sh` determines the MIME type from the **third argument**
(filename string), NOT from the file path. Always pass a filename **with
the correct extension** as the third arg:

```
upload-image.sh eggbev /tmp/card-foo.jpeg "hsbc-premier-credit-card.jpeg"
```

Passing a bare title with no extension causes HTTP 500
(`rest_upload_sideload_error`). The extension in the third arg must match
one of: `.jpg`, `.jpeg`, `.webp`, `.png`.
