# REC/P1 rule consolidation and flow-review lesson — 2026-05-28

## Trigger

Use this reference when REC/P1/REC+P1 work accumulates multiple post-publish corrections, image repairs, runner patches, or new editorial rules in one session and Rodolfo asks for a reviewable flow for him/Raquel.

## Durable lesson

Do not let every incident become another active rule source. The production system should stay class-level and contract-driven:

```text
Active editorial rules      -> contracts/gb-cc-en.md
Operational routing         -> SKILL.md, kept short
Objective validation        -> runner/validator hard gates
Session-specific incidents  -> references/ or references/archive
Temporary manual repairs    -> not active production rules until approved/promoted
```

Historical references are evidence and migration detail, not production authority. If a lesson changes future behavior, promote it into the active contract and/or runtime validator; otherwise archive it as context.

## Review-ready REC+P1 flow

When explaining the initial flow for Rodolfo/Raquel, present it as a simple operational sequence:

```text
1. Request arrives with site, exact card name, official URL, status and optional card image.
2. Validate card identity and official source before publishing anything.
3. Prepare/validate the LazyBlock card image before article publication.
4. Generate and validate REC as the short commercial bridge to P1.
5. Publish/draft REC only after REC gates pass.
6. Generate P1 separately using only minimal REC handoff.
7. Publish/draft P1 only after P1 gates pass.
8. Generate distinct REC/P1 featured images from the final card asset.
9. Verify REC -> P1 -> issuer links, public pages, Yoast/readability and media IDs.
10. Report both URLs, image evidence, scores, warnings, repairs and cleanup.
```

## Key review framing

The four blocks Rodolfo/Raquel should review first:

```text
1. Official source and allowed facts
2. LazyBlock card image quality and pre-publication validation
3. REC vs P1 separation and allowed handoff
4. Final validation/reporting evidence
```

## Image-specific consolidation

The card image is a precondition, not a cosmetic final step. If it fails, it contaminates REC LazyBlock, P1 LazyBlock, REC featured, P1 featured, public verification and cleanup. Handle image validation before publication where possible.

For banner/manual images: extract the actual card, rotate if the card itself is vertical, add safe breathing room or neutral background if transparent edges cause LazyBlock notches, preview in context, and only then use it downstream.

## Anti-bola-de-neve rule

After a session with multiple new rules, do not keep adding disconnected references without a consolidation pass. Ask or propose to consolidate approved lessons into:

- `contracts/gb-cc-en.md` for active editorial/business rules;
- runner/validator code for objective hard gates;
- SKILL.md only for short operational routing;
- references/archive for one-off incident detail.

The final explanation should be executive and reviewable, not a dump of every historical patch.