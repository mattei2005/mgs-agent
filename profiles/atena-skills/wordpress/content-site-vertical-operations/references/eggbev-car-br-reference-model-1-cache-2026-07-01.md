# Eggbev CAR BR — reference model 1 and cache lessons (2026-07-01)

## Context
Rodolfo corrected the first Eggbev CAR BR REC after publication. The issue was not only facts; it was model fidelity. For this class of content, “use this reference/model” means reproduce the article structure closely while rewriting the context professionally and without plagiarism.

## Reference-model workflow lesson

When Rodolfo provides a model URL and asks for the same model/structure:

1. Analyze the reference article structurally before writing:
   - title style;
   - subtitle/excerpt placement;
   - intro paragraph count;
   - H2 order and wording pattern;
   - lists/ordered lists;
   - tables;
   - FAQ format;
   - CTA labels, placement and destination behavior;
   - image/hyperlink presence.
2. Recreate the structure for the target context.
3. Use GPT/LLM rewriting for the new context by default; do not copy the surface text.
4. Keep the content professional and natural, not a mechanical synonym swap.
5. Validate final rendered HTML against the requested model elements, not only against word count/Yoast.

## CAR BR REC model 1 ending requested

For the CAR BR financing REC in this session, Rodolfo requested the final block from screenshot/reference:

- blue CTA button: `VEJA OPÇÕES DISPONÍVEIS`;
- helper text: `Ao clicar, você permanecerá no mesmo site.`;
- centered FAQ heading: `FAQ — Dúvidas Frequentes Sobre Financiamento de Veículos Sem Entrada e Parcelado`;
- FAQ/accordion box with 5 questions;
- centered warning paragraph beginning with `⚠️ Atenção:` and emphasizing `financiamento de veículos sem entrada e parcelado`;
- second blue CTA button: `SAIBA MAIS`;
- helper text repeated;
- REC buttons stay on the same site and point to the P1.

## Cloudflare APO cache lesson

Eggbev can keep serving stale public HTML from Cloudflare APO (`cf-cache-status: HIT`) after a REST/WP content update. In the session, REST and cache-busted public HTML showed the update, while the canonical old slug still served old content.

Durable validation/repair pattern:

1. Validate REST content after update.
2. Validate public URL with `Cache-Control: no-cache` or a cache-busting query.
3. Use browser/DOM checks for the visible content: title, CTA labels, FAQ/details count, table, and P1 link.
4. If immediate human review is required and the canonical slug remains stale, use a clean new slug or purge APO/cache; then validate the new public URL.
5. Report cache handling transparently in the final summary.

## Final validation checklist for this pattern

- HTTP 200 on final public URL.
- Browser/DOM title matches the rewritten title.
- Rendered body contains required structural elements from the reference/model.
- CTAs point to the intended P1 or final destination.
- Yoast SEO/readability recalculated.
- Final report says if this was manual/adapted rather than the standard runner path.
