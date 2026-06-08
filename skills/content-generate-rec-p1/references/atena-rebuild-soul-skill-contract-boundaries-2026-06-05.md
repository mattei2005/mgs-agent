# Atena rebuild — SOUL / SKILL / contract boundaries

Session context: Rodolfo is rebuilding Atena cleanly after the REC+P1 workflow accumulated rules in SOUL, SKILL, templates and references. The durable lesson is not the specific draft content; it is the classification rule for where future rules belong.

## Boundary rule

```text
Quem a Atena é / como se comporta       -> SOUL.md
Como executar REC+P1                    -> SKILL.md
Como o REC deve ser                     -> contracts/cc-rec.md
Como a P1 deve ser                      -> contracts/cc-p1.md
Configuração de sites                   -> data/sites.json
Histórico de bugs e incidentes          -> references/archive
Código de execução                      -> scripts/runners + validators
```

Do not put full operational templates in SOUL. SOUL may carry a short principle and a pointer to the operational source of truth.

## REC+P1 as the normal product

Rodolfo clarified that normal production should not be “ask for REC, then ask for P1”. The normal request is one business operation: REC+P1. Standalone REC or P1 should be treated as exception/repair/audit/continuation unless Rodolfo/Raquel explicitly request it.

A complete request usually includes:

```text
Site/vertical: Eggbev / gb-cc-en
Tipo: REC+P1
Produto/cartão: <exact card name>
Status: rascunho|publicado
URL oficial: <official issuer URL>
Imagem do card: <optional>
```

Complete request = authorization to execute end-to-end. Do not add ritual approval pauses. Pause only on a real blocker: official URL mismatch/inaccessible, unverified essential facts, bad/incompatible card image, security/production conflict, or risk of publishing wrong content.

## Final report placement

Rodolfo’s exact final summary template belongs in the SKILL/summary renderer, not SOUL. SOUL should only say that Atena must deliver an auditable final report with links, status, validations, images, official source, time and cost.

The SKILL/renderer must carry the exact field order:

```text
REC block: Post ID, public URL, edit URL, slug, status.
P1 block: Post ID, public URL, edit URL, slug, status.
REC detail block: type, Yoast SEO/readability, validation, title+chars, focus, meta+chars, tags, card image, featured image, official source.
P1 detail block: same fields.
Timing/cost block: runner times REC+P1 and estimated cost REC+P1=total.
```

## Image rule placement

SOUL should only hold the principle: images are part of editorial quality/conversion; preserve real card identity; do not declare success when final images are false, distorted, illegible, incompatible, wrongfully reused or poor quality.

SKILL should hold the operational image rules:

- If Rodolfo/Raquel sends a card image, treat it as the primary source; do not silently swap to fallback.
- If the image is vertical, bordered, canvas/banner, has drawings/headline/background, extract the actual card and normalize for LazyBlock.
- Rotate/prepare horizontal presentation when needed.
- Improve quality when possible; block/report if final rendering remains visibly poor.
- Use the cleaned validated card in REC LazyBlock and reuse the same cleaned card in P1 LazyBlock.
- REC featured and P1 featured must be different media/visual concepts.
- REC featured should include/compose the validated card when the visual spec requires it.
- P1 featured should be distinct from REC and may be reused as the internal P1 image after the first paragraph.

Validators/runners should enforce the rules where possible: same LazyBlock card for REC/P1, distinct REC/P1 featured media IDs/URLs, no fake/altered card identity, no silent fallback after user-supplied image, and no success report when image gates fail.

## Editing method

For this rebuild class of task, prefer creating a clean draft and using the old SOUL as source material. Line-by-line patching keeps the old remediated structure alive and tends to preserve contradictions.
