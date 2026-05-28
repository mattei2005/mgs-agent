# Manual card image quality and LazyBlock context — 2026-05-28

## Trigger

During the HSBC Rewards REC+P1 repair, the supplied/manual image was a banner/article graphic with a vertical card inside it. The first repair extracted and rotated the card, but the source crop was visibly low quality/pixelated and later transparent/edge clipping created a notch-like artifact in the LazyBlock context.

Rodolfo clarified that the rule is not only extraction/rotation. Card image quality must be handled explicitly too.

## Durable rule

For LazyBlock card images, technical validity is insufficient. The final asset must be visually acceptable in the actual card UI.

Required behavior:

- Prefer the highest-quality available source that preserves the real card design.
- If the supplied image is low quality but an official/source-safe better asset exists, use the better validated source rather than preserving the supplied low-res file.
- If a manual/source image is below ~600px useful crop width, this can remain warning-only only when the final LazyBlock render looks clean.
- Forced upscaling, visible pixelation, blur, damaged text/logo, broken edges, transparent clipping, notch artifacts, canvas residue or fake-looking output must be reported and repaired before success.
- If the final render is visibly poor, block or repair; do not hide it behind `identity passed`, `normalized`, `upscaled`, or `featured passed`.
- Preview the final card asset against the real container/background. PNG transparency can expose clipping or notches; a neutral solid background/padded presentation asset may be better for LazyBlock.

## Implementation notes

The durable production rules belong in:

- `contracts/gb-cc-en.md` under `Manual image quality and size scope`;
- `SKILL.md` REC+P1 image guidance;
- runner image normalization/reporting as warning/blocker metadata such as `LOW_QUALITY_SOURCE` when applicable.

## Reporting pattern

When reporting final image status, include both identity/normalization and visual quality/context:

```text
Card image | official/better source used; final LazyBlock asset visually acceptable; no banner/canvas/notch; dimensions 900x528
Warning    | LOW_QUALITY_SOURCE only if low-res/upscaled source remains in use
```

If the repair replaced the low-quality source with a better official source, say that explicitly instead of calling the low-res source acceptable.