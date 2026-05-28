# REC/P1 featured image separation — 2026-05-28

## Trigger

Rodolfo corrected the HSBC Rewards REC+P1 repair: the LazyBlock card image was fixed, but REC and P1 must not share the same featured image.

## Durable rule

For every REC+P1 operation, REC and P1 are separate articles and need separate featured-image assets.

Required:

- REC and P1 must use different WordPress `featured_media` IDs.
- REC and P1 must use different featured image URLs.
- The images must be different visual concepts, not the same composition renamed or lightly cropped.
- REC featured image should act as a short commercial/recommendation hook.
- P1 featured image should act as a deeper application/decision-support image.
- P1 may use its own featured image inside the P1 article body, but it must not reuse the REC featured image.

## Verification

Before reporting success for REC+P1:

1. Fetch both posts via REST.
2. Compare `featured_media` IDs.
3. Resolve media URLs and compare them.
4. If IDs or URLs match, repair before final report.
5. Visually inspect when the generated scenes look too similar despite distinct URLs.

## Runtime promotion

This rule has been promoted into:

- `contracts/gb-cc-en.md` image rules.
- `SKILL.md` REC+P1 operation rules and final report requirements.
- `mgs-rec-p1-orchestrator.py` hard validation for distinct featured media IDs/URLs.
- `generate-featured-image.sh` P1 prompt distinction from REC.
