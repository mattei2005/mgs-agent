# Eggbev CAR BR — CTA block isolation and branded reference-image repair (2026-07-01)

## Session trigger

Rodolfo reviewed the CAR BR REC-only article and corrected two issues:

1. The 3-button CTA block needed to move **one editorial block above**.
2. The reference image before the table still carried another site's branding (`wallet wisdoms`); it needed Eggbev branding instead.

## Durable workflow lessons

### 1. Move blocks by editorial boundary, not visual guess

When Rodolfo says “sobe os botões um bloco acima”, move the block to the previous content boundary in raw post HTML. In this case the correct order became:

```text
excerpt/subtitle paragraph
body paragraph 1 (“Conquistar um carro próprio...”)
3-button CTA block
body paragraph 2 (“O ponto importante...”)
```

Do not leave it after paragraph 2 just because it appears near the desired visual area.

### 2. Isolate multi-button CTA blocks from Google Auto Ads

Avoid three separate WordPress button blocks because Google Auto Ads/theme injections may enter between them.

Use one `wp:html` block with all buttons inside the same container:

```html
<!-- wp:html -->
<div class="mgs-car-options mgs-no-ad no-ad" data-no-ad="true"
     style="max-width:620px;margin:24px auto 28px auto;padding:0 6px;text-align:center;box-sizing:border-box;break-inside:avoid;page-break-inside:avoid;contain:layout paint">
  <div style="width:86px;height:7px;background:#0b4ea2;border-radius:999px;margin:0 auto 18px auto"></div>
  <a href="#carro-parcelado-sem-entrada" style="display:flex;align-items:center;justify-content:space-between;gap:16px;width:100%;box-sizing:border-box;background:#0561ea;color:#ffffff;text-decoration:none;border-radius:6px;padding:16px 18px;margin:0 auto 12px auto;font-size:15px;font-weight:800;line-height:1.2;letter-spacing:.2px;box-shadow:0 3px 10px rgba(5,97,234,.18)"><span style="text-align:left">CARRO PARCELADO SEM ENTRADA</span><span style="font-size:22px;line-height:1">→</span></a>
  <a href="#bancos-liberados" style="display:flex;align-items:center;justify-content:space-between;gap:16px;width:100%;box-sizing:border-box;background:#0561ea;color:#ffffff;text-decoration:none;border-radius:6px;padding:16px 18px;margin:0 auto 12px auto;font-size:15px;font-weight:800;line-height:1.2;letter-spacing:.2px;box-shadow:0 3px 10px rgba(5,97,234,.18)"><span style="text-align:left">BANCOS LIBERADOS</span><span style="font-size:22px;line-height:1">→</span></a>
  <a href="#veiculos-disponiveis" style="display:flex;align-items:center;justify-content:space-between;gap:16px;width:100%;box-sizing:border-box;background:#0561ea;color:#ffffff;text-decoration:none;border-radius:6px;padding:16px 18px;margin:0 auto 10px auto;font-size:15px;font-weight:800;line-height:1.2;letter-spacing:.2px;box-shadow:0 3px 10px rgba(5,97,234,.18)"><span style="text-align:left">VEÍCULOS DISPONÍVEIS</span><span style="font-size:22px;line-height:1">→</span></a>
  <div style="font-size:11px;color:#666666;line-height:1.4;margin-top:8px">Ao clicar, você permanecerá no mesmo site.</div>
</div>
<!-- /wp:html -->
```

Then verify public HTML order:

```text
index("Conquistar um carro") < index("mgs-car-options") < index("O ponto importante")
```

### 3. Reference image branding must match Eggbev

If a reference body image is used (for example the car image before the comparison table), inspect it for third-party logo/watermark/overlay. It is not enough that the photo is relevant.

Required before publishing:

- remove/crop/cover foreign branding (`wallet wisdoms`, etc.);
- add Eggbev branding if a branded corner is desired;
- upload as a new media asset with a distinct filename;
- replace the old media URL and `wp-image-<id>` in raw content;
- delete old third-party-branded media if it is no longer used and identity is scoped;
- visually validate no foreign logo remains.

### 4. Cache validation remains mandatory

After content/media edits on Eggbev, validate the default public URL, not only cache-busted/no-cache. If canonical slug remains stale due Cloudflare APO HIT, change to a fresh slug and verify default public HTML contains latest markers before reporting.

## Verification markers

- `mgs-no-ad` and `data-no-ad="true"` present in public HTML.
- `car-financing-before-comparison-eggbev.png` present.
- Old `car-financing-before-comparison.png` absent.
- CTA order is after paragraph 1 and before paragraph 2.
- Yoast scorer rerun after final slug/content/media edits.
