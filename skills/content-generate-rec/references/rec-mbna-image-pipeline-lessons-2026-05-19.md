# MBNA image pipeline lessons — 2026-05-19

Use this reference when creating or repairing REC posts where the user supplies a card image URL, or when validating featured/card images.

## Core lesson

A manual card image URL and automatic card search are different execution paths.

- **Manual image supplied:** treat the URL as the initial source of truth for the LazyBlock card image. Do not silently replace it with automatic search. If it fails quality gates, stop and report the issue or ask for explicit fallback approval.
- **No manual image supplied:** use automatic image search/ranking and report the selected source in the final summary.

## MBNA failure modes to prevent

1. **Low effective resolution hidden inside a large canvas**
   - A 1280x720 YouTube thumbnail can contain only a ~400px-wide useful card crop.
   - Upscaling that crop to 900px makes text/logos look soft or pixelated.
   - If useful pre-upscale crop width is below ~600px, mark `LOW_QUALITY_SOURCE` and do not call it production-ready.

2. **Aggressive background removal creates transparent holes**
   - Do not globally remove a flat background colour if that colour also appears inside the card design.
   - If background/canvas colour overlaps the card artwork, use a conservative RGB-preserving crop.
   - Reject internal checkerboard/transparency inside the card.

3. **Featured image must not become card-only**
   - Featured image should be contextual/lifestyle hero art.
   - It must use the same validated card design, integrated into a realistic scene.
   - Reject a huge isolated card, card-only mockup, redesigned card, wrong issuer/colours, duplicate cards, UI overlays or decorative frames.

4. **AI card-only enhancement is unsafe for LazyBlock**
   - Do not use Gemini/AI to recreate or enhance the raw card-only LazyBlock image unless the user explicitly approves a special exception.
   - AI-generated card-only assets can alter text, edges, shadows, colours and brand design.

## Final summary requirements from this incident

- Keep metrics/status in a monospaced table.
- Keep edit/public/image URLs outside the table as clickable Markdown links.
- List `Tags:` as a single complete list of all tag names applied.
- Include card image ID+URL, featured image ID+URL, image origin (manual vs automatic), media cleanup, total operational estimated cost, and duration in minutes/seconds when over 60s.
