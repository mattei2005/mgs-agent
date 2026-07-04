# Eggbev CAR BR — REC-only funnel, structure repair and featured image (2026-07-01)

## User correction

Rodolfo clarified that this Eggbev CAR BR strategy is **not REC+P1**. The funnel is:

```text
Facebook campaign -> site chat/AI -> chat displays three offers -> offer click -> long REC article
```

Therefore, the destination article is a **long REC-only page**. Do not create a P1 for this pattern unless Rodolfo/Raquel explicitly asks for one.

## If a P1 was created by mistake

With explicit authorization from Rodolfo/Raquel:

1. Verify the P1 by direct post ID and identity (title/slug) before deleting.
2. Delete the P1 permanently only after identity matches.
3. Delete only scoped P1-only media whose title/slug/source clearly belongs to the mistaken P1.
4. Verify post/media return REST 404.
5. Remove REC links that pointed to the deleted P1.
6. Replace REC CTA links with same-page anchors or the intended campaign/chat/offer destination.

## Reference fidelity pattern

When Rodolfo says to make it “igual”, “mesma estrutura” or “copiar estrutura inteira”, reproduce the structural model from the reference while rewriting the context professionally/no plagiarism:

- title/subtitle style;
- intro paragraph count and order;
- section order and H2s;
- lists, tables, FAQ and images;
- CTA block positions;
- screenshot-specific final or mid-article blocks.

For `walletwisdoms.com/br-financiamento-do-carro-agil/`, the reference model included a comparison heading followed by an image, source line and table. The body image was:

```text
https://walletwisdoms.com/wp-content/uploads/2026/02/WALLET-CAR-3-1.png
```

The featured/OG image was different:

```text
https://walletwisdoms.com/wp-content/uploads/2026/02/WALLET-CAR-P1-4.png
```

## Mid-article button block from screenshot

When Rodolfo sends the three-button screenshot and says to place it after the second paragraph, insert it after the second body paragraph, not after the excerpt/subtitle:

- blue top bar;
- full-width blue buttons:
  - `CARRO PARCELADO SEM ENTRADA`
  - `BANCOS LIBERADOS`
  - `VEÍCULOS DISPONÍVEIS`
- note below: `Ao clicar, você permanecerá no mesmo site.`

Prefer same-page anchors when the article is REC-only.

## Image/featured repair lessons

When the user says the featured image is ugly, inspect the reference for `og:image` and visible article images. The better featured candidate may be in metadata, not in the visible body.

Before using a reference image as Eggbev featured:

1. Download and inspect it.
2. Remove/crop third-party branding, watermarks and colored overlays such as `wallet wisdoms`.
3. Resize/crop to clean 16:9 featured dimensions such as `1200x675`.
4. Blur readable license plates.
5. Validate visually before upload.
6. Upload and set as `featured_media`.
7. Refresh Yoast/OpenGraph after changing featured media; otherwise `og:image` may keep the old URL.
8. Verify public HTML contains the new featured image and no old featured image URL.
9. Delete only scoped old media after confirming it belongs to the replaced featured image.

Do not report success from `featured_media` alone; verify public HTML/OG metadata.
