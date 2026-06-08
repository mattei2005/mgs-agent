# REC audit and image fallback validation

Use this reference when Zeus/Rodolfo asks to verify a completed Atena REC run, especially after changes to card-image fallback logic.

## Objective

Do not rely on Atena's final report alone. Triangulate the report against durable artifacts:

1. Discord thread transcript/import.
2. Runner JSON in `/tmp/rec-<slug>-runner.json`.
3. Public post HTTP response and rendered HTML.
4. WordPress REST post and media records.
5. Local cost/session JSON when available.
6. Visual inspection of the public page or local image files when image quality is part of the claim.

## Minimal audit checklist

For a published REC, verify:

- Post status is `publish` and public URL returns HTTP 200.
- Post ID, slug, title, public URL and edit URL match the report.
- CTA/apply URL behavior is classified correctly:
  - REC-only P1 404 = expected / not blocker.
  - P1 requested or should already exist = blocker.
- Runner `success`, `dry_run`, `site`, `post_id`, `post_slug`, `steps`, `warnings`, `duration_sec`.
- Runner steps show whether deterministic runner/local generation/API generation was used.
- Card image exists in WP media and appears in public HTML/LazyBlock.
- Current `featured_media` on the WP post matches the final intended featured image.
- Any bad/extra media created in the run are either safely deleted or explicitly reported.
- Yoast scores and focus keyword are backed by runner/REST/scorer output.
- Cost/duration claims are backed by the cost JSON/state helper, not hand-estimated.

## Determining whether Brave Images was actually exercised

The existence of the Brave fallback in `search-card-image.sh` does not prove a specific REC used Brave.

Read runner steps/logs and image provenance:

- `card_image_manual_url_used` means the card image entered as an already resolved/manual/official URL. Do **not** claim Brave was used.
- `brave_images` or equivalent provider/log entry means Brave was actually exercised.
- Official-page image discovery takes precedence over Brave. If official page exposed a usable card image, the REC validates that the new fallback did not break the pipeline, but it does **not** validate Brave in production.

User-facing phrasing:

> O fallback Brave está implementado e validado em teste separado, mas este REC específico não prova uso do Brave; a imagem veio da fonte oficial/manual já resolvida. Isso é operacionalmente bom, porque oficial > Brave > Bing.

## Featured image repair audit

If Atena detects a bad generated featured image after publication:

1. Confirm the bad media ID exists or was deleted.
2. Confirm the corrected/final media IDs exist.
3. Confirm `featured_media` on the post points to the final intended ID.
4. Check public HTML and `yoast_head_json` for stale image references.
5. Treat mixed `corrected` vs `final` references as a metadata/cache attention item, not automatically as a broken post, if the page renders correctly and the final featured is set.
6. Recommend Yoast/cache cleanup only when social/OG consistency matters or stale references persist.

## Reporting style for Rodolfo

Use an executive verdict first, then evidence:

```text
Status geral
────────────────────────────────────────────────────────────
Post publicado           OK
URL pública              HTTP 200
CTA / Apply              HTTP 404 esperado — P1 futura
Card image               OK
Featured image final     OK
Yoast                    SEO xx / Readability yy
Post ID                  nnnnn
```

Then list only material warnings:

- Brave not exercised in this REC, if applicable.
- Local generator used because `mgs-rec-api` was unavailable/masked; not a blocker when runner continued successfully.
- CTA 404 expected for REC-only.
- Yoast/OG cache inconsistency if observed.
- Two-message final report from Atena if it violated the one-message rule.

End with a concrete next step, e.g.:

> Próximo passo pendente: para testar Brave em REC real, escolher um cartão cuja página oficial não exponha imagem fácil; para produção normal, seguir com pedido curto.
