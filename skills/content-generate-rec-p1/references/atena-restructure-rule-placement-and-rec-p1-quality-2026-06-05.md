# Atena restructure — rule placement and REC+P1 quality decisions (2026-06-05)

Session-specific reference from Rodolfo/Raquel's Atena rebuild discussion. Use as migration context when rewriting Atena SOUL/SKILL/contracts/runners; do not treat as a standalone active production rule unless promoted into the proper file.

## Process preference

Rodolfo wants the rebuild reviewed strictly step by step:

1. Finish `SOUL.md` first.
2. Only after Rodolfo says SOUL is ready, move to SKILL.
3. Then contracts, runners/validators, and other files.

During SOUL review, classify items that belong elsewhere and keep a queue so nothing is lost, but do not send/review SKILL deliverables until Rodolfo asks.

## Placement rules confirmed

```text
Who Atena is / behavior principles        -> SOUL.md
How to execute REC+P1                     -> SKILL.md
How REC should be written                 -> contracts/cc-rec.md
How P1 should be written                  -> contracts/cc-p1.md
Site/vertical config                      -> data/sites.json
Bug/incident history                      -> references/archive
Execution code                            -> scripts/runners
Automated hard gates                      -> runners/validators
```

## REC+P1 architecture decision

Normal production should treat REC+P1 as one business request. Rodolfo does not want to keep working by asking for REC first and P1 later; that created conflicts.

Keep REC and P1 editorial contracts separate because they are different article products:

- `cc-rec.md` = short attraction/pre-conversion article that routes to P1.
- `cc-p1.md` = longer deep-dive/conversion article that routes to official issuer/bank.
- `SKILL.md` = operational REC+P1 flow that generates both together.

Optional future: a short REC+P1 flow contract/reference may exist only to describe cross-article relationship rules, not to merge REC and P1 specs into one giant contract.

## Anti-repetition / scale quality

Problem observed: Atena produced REC and P1 paragraphs that were copied or ~90% similar, and later REC+P1 runs repeated phrases/paragraphs from earlier articles. This is a scale blocker: if 50 articles are requested, each must remain specific to its card.

Placement:

- SOUL: principle that Atena must produce card-specific, non-boilerplate content.
- Contracts: REC has its own angle; P1 deepens without copying REC or previous P1s.
- SKILL: before success, check REC↔P1 similarity and recent same-vertical repetition.
- Validator/runner: hard gates for repeated phrases/paragraphs and cross-corpus boilerplate when possible.
- References/archive: historical examples of repeated text.

Suggested SOUL-level principle:

> Produce content specific to each card, avoiding boilerplate, reused phrases, similar paragraphs and repeated argument structures between REC, P1 and previous articles. Each card has its own proposition, benefit, audience and context; if text is interchangeable with another card, it failed editorially.

## Image rules — placement

Keep only principle/macro behavior in SOUL. Operational details belong elsewhere.

- SOUL: images are part of quality/conversion; preserve real card identity; do not declare success when final image is false, distorted, illegible, incompatible, reused wrongly or visually unacceptable.
- SKILL: operational rules for user-supplied image as primary source, extracting card from vertical/bordered/banner/canvas images, cleaning background, rotating/normalizing for horizontal LazyBlock presentation, improving quality when possible, and using the final card in REC and P1 LazyBlocks.
- Contract: desired visual outcome for REC featured and P1 featured.
- Runner/validator: enforce same cleaned card in REC/P1 LazyBlocks, distinct featured media for REC vs P1, card identity preservation, no silent fallback after user-supplied image failure.
- References/archive: historical mistakes (same REC/P1 featured, card with border/canvas, ignored supplied image, low quality accepted, fake generated card).

## Final report character counts

Raquel/Rodolfo classified character counts as operational delivery evidence, not SOUL identity.

- SKILL/final report: require title chars, subtitle chars, excerpt chars, meta description chars.
- Renderer/runner: calculate automatically; do not rely on manual estimates.
- Validator/runner: repair or warn/block if outside contract limits before success.

## Discord/read-only discussion note

In Zeus channel/thread, if Raquel comments in context, Zeus should read/analyze/respond when Rodolfo is in the discussion or asks, but must not apply file changes, persistence, restarts, authorization or operational side effects without Rodolfo's explicit approval.
