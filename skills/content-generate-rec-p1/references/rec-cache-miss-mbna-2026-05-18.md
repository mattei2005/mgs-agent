# MBNA cache-miss benchmark incident — 2026-05-18

## What happened

Rodolfo asked for two REC benchmark threads after image-selection changes:
1. normal REC; and
2. REC with a manual card image URL (`--card-image-url`) to reuse the card art for LazyBlock and featured image.

The MBNA draft failed before image handling because the card was not in cache and the runner still attempted the deprecated Anthropic/Claude extraction path. The manual image override did not get exercised because the pipeline stopped during factual extraction.

## Durable lesson

When auditing image-flow benchmarks, first confirm the runner passes cache/facts extraction. If it stops before `content_validated_pre_upload`, card-image logic has not been tested.

Expected good `steps` on a safe dry-run after the patch:

```json
[
  "config_loaded",
  "reference_extracted_deterministic",
  "article_generated_local",
  "content_validated_pre_upload",
  "dry_run_skip_card_upload",
  "dry_run_skip_featured",
  "content_validated_final",
  "duplicate_fingerprint_checked",
  "dry_run_skip_publish"
]
```

## Patch pattern

The runner cache-miss path should:
- avoid Anthropic/Claude entirely;
- extract conservative snippets from the source text;
- filter bot-block boilerplate such as `Error 1007`, `access denied`, `Cloudflare`, `while you wait`;
- fall back to generic but honest review cautions when exact benefits are not fetchable;
- keep `extract_llm_est` at `0.0`; and
- label the step `reference_extracted_deterministic`.

## Validation pattern

Use dry-run first:

```bash
cd /root/mgs-agent
python3 -m py_compile scripts/mgs-rec-runner.py
python3 scripts/mgs-rec-runner.py \
  --site eggbev \
  --card "MBNA Credit Card" \
  --status draft \
  --source-url "https://www.mbna.co.uk/credit-cards.html" \
  --card-image-url "https://i.ytimg.com/vi/9ROGLmCEpJ0/maxresdefault.jpg" \
  --dry-run
```

Passing signal observed after fix:
- `success: true`
- `validation.status: PASS`
- `duration_sec` under 1s in dry-run
- `steps` include `reference_extracted_deterministic`

## Editorial caveat

If the official page returns only issuer/bot-block boilerplate, the draft can be operationally valid but editorially generic. For publish-quality output, ask for explicit facts or use an accessible official/comparator source. Do not invent APR, annual fee, or product benefits.
