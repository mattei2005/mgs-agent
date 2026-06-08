# REC pipeline lessons — Marbles / multi-site / artifact QA

Use this reference when auditing or improving the deterministic REC pipeline after a user reports quality, cost, or workflow drift.

## REC-only CTA status

If the generated CTA points to the future P1/apply URL and returns 404, do **not** classify it as a blocker during REC-only production. Report it as `P1 pending / expected 404` unless Rodolfo explicitly said the P1 already exists.

## Generic card mockups

A placeholder cardholder name such as `YOUR NAME`, `NO NAME`, or minor typo in the fake holder name is acceptable for generic mockups. Do not mark it as a meaningful quality failure unless the logo, issuer, network, product name, color, or card design is wrong.

## Featured image aspect ratio

Gemini may ignore a 16:9 prompt and return 16:10/8:5. The durable fix is post-processing, not prompt-only enforcement:

- `compress-image.sh` should force final 1280x720 for featured images.
- Prefer center crop over padding for REC hero art.
- Runner should validate final aspect ratio before upload.

## Card image fallback source

If official pages do not expose a clean card image, fallback image search is acceptable. Current automatic fallback favors Bing because the local Playwright scraper reliably extracts original image URLs. Google Images may have more options, but should not become automatic without a safe parser/API because it tends to trigger browser loops and unstable markup.

## Multi-site same-card publishing

For the same card across multiple MGS sites: reuse facts, not final copy. Keep APR/fees/benefits/card image cached where valid, but vary title, intro, benefit prose, comparison table wording, conclusion, meta description, and ideally featured scene. Use fingerprint/similarity reporting to catch duplicate-content risk.

## Cost reporting

Rodolfo chose a conservative Sonnet-equivalent operational estimate even when Atena runs via Codex/OAuth and billing is `included`. Do not invent small manual costs; calculate from `state.db` tokens using the helper:

```bash
/root/mgs-agent/scripts/estimate-atena-session-cost.py --session-id <SESSION_ID>
```

Repeat `--session-id` when a thread spans multiple root sessions. For the Marbles audit, aggregating two sessions produced approximately US$1.64 Sonnet-equivalent.

## Runner drift / API-off handling

When `mgs-rec-api` is masked or unavailable, Atena should not abandon the deterministic runner or do a manual multi-step rewrite. The runner should handle this internally with local deterministic generation from supplied official facts/cache and report `article_generated_local` in steps.
