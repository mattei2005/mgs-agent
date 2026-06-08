# Manual low-res card image scope — 2026-05-27

## Trigger

During the Nationwide Balance Transfer REC+P1 benchmark, the supplied Finder card image had useful crop width below the previous 600px threshold. The runner blocked publish even though Rodolfo clarified this class of image works correctly after normalization inside the card UI.

## Durable rule

For user-supplied/manual card images:

- Useful crop width below 600px is **warning only**, not a publish blocker.
- It is acceptable to publish a smaller manual card image if normalization renders it correctly inside the LazyBlock/card UI.
- Still report the low-quality/source-size warning in the final response.

Hard blockers remain:

- wrong product/card identity;
- phone mockup, hand, props, lifestyle scene, external frame or page UI in the LazyBlock card image;
- hallucinated or visually changed card design;
- failed normalization or invalid card-like aspect;
- automatic fallback uncertainty in publish mode.

## Implementation shape

The rule belongs in:

- `contracts/gb-cc-en.md` under image rules;
- `mgs-rec-runner.py` image gate as `LOW_QUALITY_SOURCE_ALLOWED_MANUAL` warning;
- final report as a non-blocking warning.

Do not reintroduce the previous hard block `manual_card_image_low_quality_source` solely for small manual images.

## Operational example

A manual image with useful crop width `316px` can proceed if identity and normalization pass. Final report should say the manual image was accepted after normalization with a warning, not hide the condition.