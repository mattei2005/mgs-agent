# P1 official-source and REC card-image hard gates (2026-05-24)

## Context

A P1 was created from an existing REC for Lloyds World Elite Mastercard. The run exposed two pipeline failures:

1. The official Lloyds URL returned a branded error/page-not-found shell rather than usable product content, but the P1 was still published using REC copy and explicit facts.
2. The REC LazyBlock card image was empty, but an external/manual card image was injected into the P1, bypassing the normal card-only crop/normalization gate.

Both behaviours are unsafe for published P1 content.

## Durable rule

For P1 publish runs, a URL being on an official issuer domain is not sufficient. The source must expose usable product content for the target card.

Reject the source before publication if it shows any of these signals:

- branded `Page not found` / 404 shell;
- issuer error page such as `Internet Banking - Error`;
- geo-block or access-denied shell;
- empty or near-empty body;
- search/help page with no product terms;
- page text that does not clearly mention the target product or its terms.

Explicit facts, cache rows, REC copy, or secondary references must not override a dead official URL for a publish run. Stop and ask Raquel/Rodolfo for the correct official link.

## P1 from REC card-image rule

When creating a P1 from an existing REC, the P1 card image must come from the REC LazyBlock unless the workflow explicitly repairs the REC/card image first.

If the REC LazyBlock image is empty:

1. Stop before publishing the P1.
2. Ask Raquel for the correct card image or repair the REC card image.
3. Any replacement image must pass the normal card-only gate before upload:
   - horizontal/landscape card;
   - card-only asset;
   - no large external background/canvas;
   - cropped/normalized to card bounds;
   - issuer/network identity visually verified.

Never silently inject a cache/manual/external image into the P1 just to unblock publication.

## Runner-level guardrails added

`/root/mgs-agent/scripts/mgs-p1-runner.py` now includes:

- an official-source preflight that rejects error shells even when HTTP status is 200;
- a hard stop when the source REC LazyBlock lacks a valid card image;
- JSON `images.card_image_source` reporting when publication succeeds.

## User-facing behaviour

When either gate fails, the correct response is a short operational update in the thread:

```text
Não publiquei a P1 ainda.

Motivo: a URL oficial não abriu conteúdo real do produto / o REC está sem imagem de card.

Raquel, pode enviar o link oficial correto e/ou a imagem correta do card para eu refazer com segurança?
```

Do not report the article as ready, validated, or published until both gates pass.
